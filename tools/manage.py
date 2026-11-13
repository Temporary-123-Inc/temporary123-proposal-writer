#!/usr/bin/env python3
"""Validate, package, install, and diagnose the portable proposal-writer skill.

Management uses Python's standard library only. Proposal creation/rendering has
separate optional dependencies, reported by ``doctor`` without installing them.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit
import zipfile

SKILL_NAME = "temporary123-proposal-writer"
REPOSITORY = Path(__file__).resolve().parents[1]
# Conservative, tool-specific portability checks, in decimal bytes. These are
# Claude Skills API / OpenAI Skills API portability checks, not universal
# chat-upload limits or a substitute for checking a target tool's current limits.
MAX_BUNDLE_BYTES = 30_000_000
MAX_FILE_BYTES = 25_000_000
IGNORED_DIRECTORIES = {"__pycache__", "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
REPOSITORY_IGNORED_DIRECTORIES = IGNORED_DIRECTORIES | {".git", ".venv", "venv", "dist", "build"}


class ManagementError(ValueError):
    """An actionable repository or destination problem."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def is_link(path: Path) -> bool:
    # Windows junctions can redirect traversal just like directory symlinks.
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def repository_path(repository: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ManagementError(f"{label}: expected a nonempty repository-relative POSIX path")
    candidate = Path(relative)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:", relative):
        raise ManagementError(f"{label}: absolute paths are not allowed: {relative}")
    resolved = (repository / candidate).resolve()
    if not is_within(resolved, repository.resolve()):
        raise ManagementError(f"{label}: path escapes its source directory: {relative}")
    if not resolved.is_file():
        raise ManagementError(f"{label}: missing file: {relative}")
    return resolved


def runtime_files(runtime: Path) -> list[Path]:
    """Return the portable runtime payload; never traverse symlinks or caches."""
    if not runtime.is_dir() or is_link(runtime):
        raise ManagementError(f"Runtime must be an ordinary directory: {runtime}")
    found = []
    for base, directories, names in os.walk(runtime, followlinks=False):
        directories[:] = sorted(d for d in directories if not d.startswith(".") and d not in IGNORED_DIRECTORIES)
        for directory in directories:
            if is_link(Path(base) / directory):
                raise ManagementError(f"Runtime symlinks are not portable: {Path(base) / directory}")
        for name in sorted(names):
            if name.startswith(".") or name.endswith((".pyc", ".pyo")):
                continue
            path = Path(base) / name
            if is_link(path):
                raise ManagementError(f"Runtime symlinks are not portable: {path}")
            if not path.is_file():
                raise ManagementError(f"Runtime entry is not a regular file: {path}")
            found.append(path)
    return sorted(found, key=lambda path: path.relative_to(runtime).as_posix())


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise ManagementError(f"Cannot read UTF-8 file {path}: {error}") from error


def frontmatter(skill_file: Path) -> dict[str, str]:
    text = read_text(skill_file)
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    if not match:
        raise ManagementError(f"{skill_file}: missing YAML frontmatter delimiters")
    lines = match.group(1).splitlines()
    result = {}
    for index, line in enumerate(lines):
        field = re.match(r"^(name|description):\s*(.*?)\s*$", line)
        if not field:
            continue
        key, value = field.groups()
        if key in result:
            raise ManagementError(f"{skill_file}: duplicate frontmatter field {key}")
        if value in {">", ">-", ">+", "|", "|-", "|+"}:
            parts = []
            for continuation in lines[index + 1:]:
                if continuation and not continuation[0].isspace():
                    break
                parts.append(continuation.strip())
            value = ("\n" if value.startswith("|") else " ").join(parts).strip()
        elif value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as error:
                raise ManagementError(f"{skill_file}: {key} must use plain, single-quoted, or JSON-compatible double-quoted text") from error
        elif value.startswith("'"):
            if not value.endswith("'") or len(value) < 2:
                raise ManagementError(f"{skill_file}: unterminated {key} string")
            value = value[1:-1].replace("''", "'")
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        if not isinstance(value, str) or not value.strip():
            raise ManagementError(f"{skill_file}: {key} must be nonempty text")
        result[key] = value.strip()
    if not all(key in result for key in ("name", "description")):
        raise ManagementError(f"{skill_file}: frontmatter requires name and description")
    if result["name"] != SKILL_NAME or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", result["name"]):
        raise ManagementError(f"{skill_file}: name must match runtime directory {SKILL_NAME!r}")
    if len(result["name"]) > 64 or len(result["description"]) > 1024:
        raise ManagementError(f"{skill_file}: name must be <=64 and description <=1024 characters")
    return result


def without_code_fences(text: str) -> str:
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            char = marker.group(1)[0]
            length = len(marker.group(1))
            if fence is None:
                fence = (char, length)
            elif char == fence[0] and length >= fence[1]:
                fence = None
            lines.append("")
        else:
            lines.append(line if fence is None else "")
    return "\n".join(lines)


def markdown_targets(text: str) -> list[str]:
    """Extract inline/reference Markdown links and HTML href/src attributes.

    Fenced examples and inline code are intentionally not treated as links.
    Balanced parentheses in inline destinations cover common filenames/URLs.
    """
    text = without_code_fences(text)
    text = re.sub(r"(`+).*?\1", "", text, flags=re.S)
    targets = []
    for match in re.finditer(r"\]\(\s*", text):
        start = match.end()
        if start < len(text) and text[start] == "<":
            end = text.find(">", start + 1)
            if end >= 0:
                targets.append(text[start + 1:end])
            continue
        cursor = start
        depth = 0
        while cursor < len(text):
            char = text[cursor]
            if char == "\\":
                cursor += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char.isspace() and depth == 0:
                break
            cursor += 1
        if cursor > start:
            targets.append(re.sub(r"\\([() ])", r"\1", text[start:cursor]))
    for match in re.finditer(r"^\s{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))", text, re.M):
        targets.append(match.group(1) or match.group(2))
    for match in re.finditer(r"\b(?:href|src)\s*=\s*(['\"])(.*?)\1", text, re.I):
        targets.append(html.unescape(match.group(2)))
    return targets


def markdown_anchors(text: str) -> set[str]:
    anchors = set(re.findall(r"\b(?:id|name)\s*=\s*['\"]([^'\"]+)['\"]", text, re.I))
    seen = {}
    lines = without_code_fences(text).splitlines()
    for index, line in enumerate(lines):
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        title = heading.group(1) if heading else None
        if title is None and index + 1 < len(lines) and line.strip() and re.fullmatch(r"\s{0,3}(?:=+|-+)\s*", lines[index + 1]):
            title = line.strip()
        if title is None:
            continue
        title = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", title)
        title = html.unescape(re.sub(r"<[^>]+>", "", title)).lower().strip()
        title = "".join(char for char in title if char in "-_ " or unicodedata.category(char)[0] in "LN")
        slug = title.replace(" ", "-")
        number = seen.get(slug, 0)
        seen[slug] = number + 1
        anchors.add(slug if not number else f"{slug}-{number}")
    return anchors


def repository_files(repository: Path, suffix: str) -> list[Path]:
    files = []
    for base, directories, names in os.walk(repository, followlinks=False):
        directories[:] = [d for d in directories if d not in REPOSITORY_IGNORED_DIRECTORIES and not d.startswith(".manage-test-")]
        directories[:] = [d for d in directories if not is_link(Path(base) / d)]
        files.extend(Path(base) / name for name in names if name.lower().endswith(suffix) and not is_link(Path(base) / name))
    return sorted(files)


def markdown_files(repository: Path) -> list[Path]:
    return repository_files(repository, ".md")


def validate_markdown(repository: Path) -> tuple[int, int]:
    files = markdown_files(repository)
    checked = 0
    root = repository.resolve()
    for source in files:
        for target in markdown_targets(read_text(source)):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or target.startswith("/"):
                continue
            relative = unquote(parsed.path)
            destination = (source.parent / relative).resolve() if relative else source.resolve()
            if not is_within(destination, root):
                raise ManagementError(f"{source.relative_to(repository)}: relative link escapes repository: {target}")
            if not destination.exists():
                raise ManagementError(f"{source.relative_to(repository)}: missing relative link target: {target}")
            if parsed.fragment and destination.suffix.lower() == ".md":
                anchor = unquote(parsed.fragment)
                if anchor not in markdown_anchors(read_text(destination)):
                    raise ManagementError(f"{source.relative_to(repository)}: missing Markdown anchor #{anchor} in {destination.relative_to(repository)}")
            checked += 1
    return len(files), checked


def load_json(path: Path):
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as error:
        raise ManagementError(f"Invalid JSON in {path}: line {error.lineno}, column {error.colno}: {error.msg}") from error


def check_hash(path: Path, expected: str, label: str) -> None:
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise ManagementError(f"{label}: expected a SHA-256 value with 64 hexadecimal characters")
    actual = sha256(path)
    if actual.lower() != expected.lower():
        raise ManagementError(f"{label}: SHA-256 mismatch for {path.name}; expected {expected.lower()}, got {actual}")


def validate(repository: Path = REPOSITORY) -> dict:
    repository = repository.resolve()
    runtime = repository / SKILL_NAME
    files = runtime_files(runtime)
    metadata = frontmatter(runtime / "SKILL.md")
    for required in ("agents/openai.yaml", "scripts/inventory.py", "assets/source-provenance.json"):
        repository_path(runtime, required, "Required runtime file")
    json_files = [path for path in files if path.suffix.lower() == ".json"]
    for path in json_files:
        load_json(path)
    # Repository metadata and checked-in fixtures also deserve parse checks.
    for path in repository_files(repository, ".json"):
        if is_within(path, runtime):
            continue
        load_json(path)
    provenance = load_json(runtime / "assets/source-provenance.json")
    if not isinstance(provenance, dict):
        raise ManagementError("assets/source-provenance.json must contain a JSON object")
    manifest = provenance.get("bundled_asset_sha256")
    if not isinstance(manifest, dict) or not manifest:
        raise ManagementError("assets/source-provenance.json: bundled_asset_sha256 must be a nonempty object")
    assets = runtime / "assets"
    actual_assets = {path.relative_to(assets).as_posix() for path in files if is_within(path, assets) and path.name != "source-provenance.json"}
    if set(manifest) != actual_assets:
        missing = sorted(actual_assets - set(manifest))
        stale = sorted(set(manifest) - actual_assets)
        raise ManagementError(f"Asset hash manifest does not match runtime assets; missing hashes: {missing}; missing assets: {stale}")
    for relative, expected in manifest.items():
        check_hash(repository_path(assets, relative, "Bundled asset"), expected, "Bundled asset")
    original = provenance.get("repository_original_pricebook")
    if not isinstance(original, dict):
        raise ManagementError("assets/source-provenance.json: repository_original_pricebook object is required")
    archive = repository_path(repository, original.get("path"), "Original price-book archive")
    if is_within(archive, runtime):
        raise ManagementError("Original price-book archive must be outside the installable runtime directory")
    check_hash(archive, original.get("sha256"), "Original price-book archive")
    markdown_count, link_count = validate_markdown(repository)
    inventory = subprocess.run([sys.executable, str(runtime / "scripts/inventory.py"), "verify"], cwd=repository, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False)
    if inventory.returncode:
        detail = (inventory.stderr or inventory.stdout).strip()[-2000:]
        raise ManagementError(f"Inventory verification failed (exit {inventory.returncode}): {detail}")
    return {"valid": True, "skill": metadata["name"], "runtime": str(runtime), "runtime_files": len(files), "runtime_bytes": sum(path.stat().st_size for path in files), "markdown_files": markdown_count, "relative_links_checked": link_count, "json_files": len(json_files), "hashed_assets": len(manifest), "original_archive_verified": True, "inventory_verified": True}


def portable_limits(files: list[Path], runtime: Path) -> int:
    total = 0
    for path in files:
        size = path.stat().st_size
        if size >= MAX_FILE_BYTES:
            raise ManagementError(f"OpenAI Skills API portable file limit: {path.relative_to(runtime)} is {size} bytes; each file must be below {MAX_FILE_BYTES} bytes")
        total += size
    if total >= MAX_BUNDLE_BYTES:
        raise ManagementError(f"Claude Skills API portable bundle limit: uncompressed runtime is {total} bytes; must be below {MAX_BUNDLE_BYTES} bytes")
    return total


def package(repository: Path = REPOSITORY, output: Path | None = None) -> dict:
    repository = repository.resolve()
    runtime = repository / SKILL_NAME
    output = (output if output is not None else repository / "dist" / f"{SKILL_NAME}.zip").resolve()
    if is_within(output, runtime):
        raise ManagementError("Package output must be outside the runtime directory")
    if output.suffix.lower() != ".zip":
        raise ManagementError("Package output must have a .zip extension")
    validation = validate(repository)
    files = runtime_files(runtime)
    total = portable_limits(files, runtime)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".skill-package-", suffix=".zip", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
        expected = []
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for path in files:
                name = f"{SKILL_NAME}/{path.relative_to(runtime).as_posix()}"
                expected.append(name)
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(temporary) as bundle:
            if bundle.namelist() != expected or bundle.testzip() is not None:
                raise ManagementError("Package verification failed: archive entries or CRC do not match")
            if sum(info.file_size for info in bundle.infolist()) != total:
                raise ManagementError("Runtime changed during packaging; rerun validation/package")
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"packaged": True, "skill": SKILL_NAME, "output": str(output), "files": validation["runtime_files"], "uncompressed_bytes": total, "archive_bytes": output.stat().st_size, "sha256": sha256(output), "crc_verified": True}


def installation_root(agent: str, scope: str, skills_dir: Path | None, project: Path | None = None) -> Path:
    if agent not in {"codex", "claude"} or scope not in {"user", "project"}:
        raise ManagementError("Install requires agent codex|claude and scope user|project")
    if skills_dir is not None:
        return skills_dir.expanduser().absolute()
    base = Path.home() if scope == "user" else (project or Path.cwd())
    return base / (".agents" if agent == "codex" else ".claude") / "skills"


def reject_symlink_path(path: Path) -> None:
    for component in (path, *path.parents):
        if is_link(component):
            raise ManagementError(f"Install destination cannot pass through a symlink or junction: {component}")


def install(repository: Path = REPOSITORY, *, agent: str, scope: str = "user", skills_dir: Path | None = None, overwrite: bool = False, project: Path | None = None) -> dict:
    repository = repository.resolve()
    runtime = repository / SKILL_NAME
    root = installation_root(agent, scope, skills_dir, project)
    raw_destination = root / SKILL_NAME
    reject_symlink_path(raw_destination)
    destination = raw_destination.resolve()
    if is_within(destination, runtime) or is_within(runtime, destination):
        raise ManagementError("Install destination overlaps the runtime source directory")
    validate(repository)
    files = runtime_files(runtime)
    copy = []
    unchanged = 0
    replaced = 0
    # Complete the conflict/symlink preflight before creating any directories.
    for source in files:
        target = destination / source.relative_to(runtime)
        reject_symlink_path(target)
        for parent in (target.parent, *target.parent.parents):
            if parent.exists() and not parent.is_dir():
                raise ManagementError(f"Install destination parent is not a directory: {parent}")
        if target.exists():
            if not target.is_file():
                raise ManagementError(f"Managed file conflicts with a directory: {target}")
            if sha256(source) == sha256(target):
                unchanged += 1
                continue
            if not overwrite:
                raise ManagementError(f"Existing managed file differs: {target}. Rerun with --overwrite to replace managed files; unrelated files are preserved")
            replaced += 1
        copy.append((source, target))
    for source, target in copy:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".skill-install-", dir=target.parent, delete=False) as stream:
                temporary = Path(stream.name)
            shutil.copyfile(source, temporary)
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {"installed": True, "agent": agent, "scope": scope, "skills_root": str(root.resolve()), "destination": str(destination), "managed_files": len(files), "copied": len(copy), "new_files": len(copy) - replaced, "replaced": replaced, "unchanged": unchanged, "unmanaged_files_preserved": True}


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def doctor() -> dict:
    modules = {display: module_available(module) for display, module in (("python-docx", "docx"), ("Pillow", "PIL"), ("pypdf", "pypdf"), ("PyMuPDF", "fitz"), ("pypdfium2", "pypdfium2"))}
    office = shutil.which("soffice") or shutil.which("libreoffice") or shutil.which("soffice.exe")
    if not office and os.name == "nt":
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(variable)
            candidate = Path(base) / "LibreOffice/program/soffice.exe" if base else None
            if candidate and candidate.is_file():
                office = str(candidate)
                break
    poppler = shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")
    rasterizer = modules["PyMuPDF"] or modules["pypdfium2"] or bool(poppler)
    return {"python": {"version": sys.version.split()[0], "executable": sys.executable, "supported": sys.version_info >= (3, 10)}, "optional_packages": modules, "headless_renderer": {"libreoffice": office, "pdftoppm": poppler, "pdf_rasterization_available": rasterizer, "local_docx_rendering_available": bool(office) and rasterizer}, "document_creation_dependencies_available": modules["python-docx"] and modules["Pillow"], "notes": ["Management commands require only Python 3.10+ standard library.", "No applications were launched and no packages were installed.", "Headless commands are detected, not executed; actual rendering and visual review remain required.", "Live browser/Drive/Sheets access depends on the target environment and was not checked."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Check metadata, relative Markdown links, JSON, source hashes and inventory")
    bundle = commands.add_parser("package", help="Validate and create a deterministic runtime-only ZIP")
    bundle.add_argument("--output", type=Path, help="ZIP output; default: repository dist/temporary123-proposal-writer.zip")
    installer = commands.add_parser("install", help="Copy runtime files into a Codex or Claude skills directory")
    installer.add_argument("--agent", required=True, choices=("codex", "claude"))
    installer.add_argument("--scope", choices=("user", "project"), default="user")
    installer.add_argument("--skills-dir", type=Path, help="Override skills ROOT; the skill name is appended")
    installer.add_argument("--overwrite", action="store_true", help="Replace differing managed files; preserve unrelated files")
    commands.add_parser("doctor", help="Report optional authoring/rendering dependencies without launching or installing")
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 10):
            raise ManagementError("Python 3.10 or newer is required")
        if args.command == "validate":
            result = validate()
        elif args.command == "package":
            result = package(output=args.output)
        elif args.command == "install":
            result = install(agent=args.agent, scope=args.scope, skills_dir=args.skills_dir, overwrite=args.overwrite)
        else:
            result = doctor()
    except (ManagementError, OSError, subprocess.TimeoutExpired, zipfile.BadZipFile) as error:
        print(f"Management error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
