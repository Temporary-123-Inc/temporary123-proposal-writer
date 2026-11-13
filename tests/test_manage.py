"""Stdlib tests for repository management; all writes stay in temporary fixtures."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "manage.py"
SPEC = importlib.util.spec_from_file_location("proposal_skill_manage", MODULE_PATH)
manage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage)


class ManagementTests(unittest.TestCase):
    def setUp(self):
        # Keep even transient files under the repository's tests directory.
        self.temporary = tempfile.TemporaryDirectory(prefix=".manage-test-", dir=Path(__file__).parent)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "repository"
        self.runtime = self.repo / manage.SKILL_NAME
        self.runtime.mkdir(parents=True)
        self.write("SKILL.md", f'---\nname: {manage.SKILL_NAME}\ndescription: "Create complete proposal documents."\n---\n\n# Example Skill\n\n[Guide](references/guide.md#required-facts)\n')
        self.write("references/guide.md", "# Guide\n\n## Required facts\n\n[Skill](../SKILL.md#example-skill)\n")
        self.write("agents/openai.yaml", 'interface:\n  display_name: "Example"\n')
        self.write("assets/example.txt", "retained original evidence\n")
        self.write("assets/inventory/source.txt", "fixture inventory source\n")
        self.write("assets/inventory/index.json", '{"verified_source": "fixture inventory source\\n"}\n')
        # The fixture helper verifies real fixture inputs and returns a failure
        # when their content diverges, rather than accepting every invocation.
        self.write("scripts/inventory.py", '''import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
assert sys.argv[1:] == ["verify"], "expected verify command"
index = json.loads((root / "assets/inventory/index.json").read_text())
source = (root / "assets/inventory/source.txt").read_text()
if index["verified_source"] != source:
    sys.exit("index differs from source")
print(json.dumps({"verified": True}))
''')
        self.archive = self.repo / "source-archives" / "temporary123-rental-price-book.pdf"
        self.archive.parent.mkdir(parents=True)
        self.archive.write_bytes(b"%PDF-original-pricebook-outside-runtime\n")
        self.provenance = {"bundled_asset_sha256": {}, "repository_original_pricebook": {"path": self.archive.relative_to(self.repo).as_posix(), "sha256": manage.sha256(self.archive)}}
        self.refresh_hashes()
        (self.repo / "README.md").write_text(f"# Repository\n\n[Skill]({manage.SKILL_NAME}/SKILL.md#example-skill)\n", encoding="utf-8")

    def write(self, relative, content):
        path = self.runtime / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def refresh_hashes(self):
        self.provenance["bundled_asset_sha256"] = {path.relative_to(self.runtime / "assets").as_posix(): manage.sha256(path) for path in self.runtime.rglob("*") if path.is_file() and "assets" in path.relative_to(self.runtime).parts and path.name != "source-provenance.json"}
        self.write("assets/source-provenance.json", json.dumps(self.provenance))

    def test_validate_checks_real_fixture_and_all_markdown(self):
        result = manage.validate(self.repo)
        self.assertTrue(result["valid"])
        self.assertTrue(result["inventory_verified"])
        self.assertEqual(result["relative_links_checked"], 3)
        self.assertEqual(result["hashed_assets"], 3)

    def test_missing_relative_link_and_anchor_fail(self):
        guide = self.runtime / "references/guide.md"
        for text, message in (("[Missing](missing.md)", "missing relative link target"), ("[Missing](../SKILL.md#absent)", "missing Markdown anchor")):
            with self.subTest(text=text):
                guide.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(manage.ManagementError, message):
                    manage.validate(self.repo)

    def test_repository_metadata_links_and_json_are_checked(self):
        metadata = self.repo / ".github"
        metadata.mkdir()
        (metadata / "CONTRIBUTING.md").write_text("[Missing](../missing.md)", encoding="utf-8")
        with self.assertRaisesRegex(manage.ManagementError, "missing relative link target"):
            manage.validate(self.repo)
        (metadata / "CONTRIBUTING.md").write_text("[Home](../README.md#repository)", encoding="utf-8")
        (metadata / "metadata.json").write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(manage.ManagementError, "Invalid JSON"):
            manage.validate(self.repo)

    def test_markdown_examples_external_links_and_duplicate_headings(self):
        guide = self.runtime / "references/guide.md"
        guide.write_text("## Required facts\n\n## Required facts\n\n[Duplicate](#required-facts-1)\n[External](https://example.invalid/no-file)\n```md\n[Example](not-present.md)\n```\n`[Example](not-present.md)`\n", encoding="utf-8")
        self.assertTrue(manage.validate(self.repo)["valid"])

    def test_reference_link_html_and_escaped_filename_checked(self):
        self.write("references/extra (facts).md", "# Facts\n")
        self.write("references/guide.md", "## Required facts\n\n[Ref][facts]\n\n[facts]: <extra%20(facts).md#facts>\n<a href='../SKILL.md#example-skill'>Home</a>\n[Inline](extra%20\\(facts\\).md#facts)\n")
        self.assertTrue(manage.validate(self.repo)["valid"])
        self.write("references/guide.md", "## Required facts\n\n[facts]: <lost.md>\n")
        with self.assertRaisesRegex(manage.ManagementError, "missing relative link target"):
            manage.validate(self.repo)

    def test_missing_frontmatter_and_description_fail(self):
        for content in ("# No metadata\n", f"---\nname: {manage.SKILL_NAME}\n---\n"):
            with self.subTest(content=content):
                self.write("SKILL.md", content)
                with self.assertRaisesRegex(manage.ManagementError, "frontmatter"):
                    manage.validate(self.repo)

    def test_json_parse_and_asset_tampering_fail(self):
        index = self.runtime / "assets/inventory/index.json"
        original = index.read_text(encoding="utf-8")
        index.write_text("{not valid JSON", encoding="utf-8")
        with self.assertRaisesRegex(manage.ManagementError, "Invalid JSON"):
            manage.validate(self.repo)
        index.write_text(original, encoding="utf-8")
        self.write("assets/example.txt", "tampered")
        with self.assertRaisesRegex(manage.ManagementError, "SHA-256 mismatch"):
            manage.validate(self.repo)

    def test_original_archive_hash_and_manifest_completeness_fail(self):
        self.archive.write_bytes(b"changed original")
        with self.assertRaisesRegex(manage.ManagementError, "Original price-book archive: SHA-256 mismatch"):
            manage.validate(self.repo)
        self.provenance["repository_original_pricebook"]["sha256"] = manage.sha256(self.archive)
        self.refresh_hashes()
        self.write("assets/untracked.txt", "unrecorded asset")
        with self.assertRaisesRegex(manage.ManagementError, "missing hashes.*untracked.txt"):
            manage.validate(self.repo)

    def test_provenance_cannot_read_outside_its_source_root(self):
        outside = self.base / "outside.pdf"
        outside.write_bytes(b"outside")
        self.provenance["repository_original_pricebook"] = {"path": "../outside.pdf", "sha256": manage.sha256(outside)}
        self.write("assets/source-provenance.json", json.dumps(self.provenance))
        with self.assertRaisesRegex(manage.ManagementError, "escapes its source directory"):
            manage.validate(self.repo)

    def test_inventory_divergence_is_verified_even_with_updated_hashes(self):
        self.write("assets/inventory/source.txt", "divergent inventory")
        self.refresh_hashes()
        with self.assertRaisesRegex(manage.ManagementError, "Inventory verification failed.*index differs"):
            manage.validate(self.repo)

    def test_package_has_one_root_only_runtime_and_is_reproducible(self):
        self.write(".secret", "not bundled")
        self.write(".git/config", "not bundled")
        self.write("scripts/__pycache__/inventory.pyc", "not bundled")
        self.write("scripts/inventory.pyc", "not bundled")
        first = self.base / "one.zip"
        second = self.base / "two.zip"
        result = manage.package(self.repo, first)
        # Source mtimes must not influence ZIP bytes.
        for path in manage.runtime_files(self.runtime):
            os.utime(path, (1_700_000_000, 1_700_000_000))
        manage.package(self.repo, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertTrue(result["crc_verified"])
        with zipfile.ZipFile(first) as bundle:
            names = bundle.namelist()
            self.assertTrue(all(name.startswith(manage.SKILL_NAME + "/") for name in names))
            self.assertIn(manage.SKILL_NAME + "/SKILL.md", names)
            self.assertFalse(any("source-archives" in name or "__pycache__" in name or name.endswith(".pyc") or "/.git/" in name or name.endswith(".secret") for name in names))
            self.assertIsNone(bundle.testzip())
            self.assertEqual(names, sorted(names))

    def test_package_output_guard_and_limits_create_no_output(self):
        with self.assertRaisesRegex(manage.ManagementError, "outside the runtime"):
            manage.package(self.repo, self.runtime / "bad.zip")
        target = self.base / "too-large.zip"
        with patch.object(manage, "MAX_BUNDLE_BYTES", 1):
            with self.assertRaisesRegex(manage.ManagementError, "Claude Skills API"):
                manage.package(self.repo, target)
        self.assertFalse(target.exists())
        with patch.object(manage, "MAX_FILE_BYTES", 1):
            with self.assertRaisesRegex(manage.ManagementError, "OpenAI Skills API"):
                manage.package(self.repo, target)
        self.assertFalse(target.exists())

    def test_invalid_source_is_not_packaged_or_installed(self):
        self.write("assets/example.txt", "tampered")
        output = self.base / "invalid.zip"
        skills = self.base / "invalid-install"
        with self.assertRaises(manage.ManagementError):
            manage.package(self.repo, output)
        with self.assertRaises(manage.ManagementError):
            manage.install(self.repo, agent="codex", skills_dir=skills)
        self.assertFalse(output.exists())
        self.assertFalse(skills.exists())

    def test_install_overwrite_guard_is_preflight_and_preserves_unmanaged(self):
        skills = self.base / "installed-skills"
        first = manage.install(self.repo, agent="codex", skills_dir=skills)
        installed = skills / manage.SKILL_NAME
        self.assertEqual(Path(first["destination"]), installed)
        self.assertEqual(first["new_files"], len(manage.runtime_files(self.runtime)))
        unmanaged = installed / "my-notes.txt"
        unmanaged.write_text("keep my notes", encoding="utf-8")
        changed = installed / "scripts/inventory.py"
        changed.write_text("local user edit", encoding="utf-8")
        # A later conflict cannot cause an earlier new source file to be copied.
        self.write("references/new.md", "new source file")
        with self.assertRaisesRegex(manage.ManagementError, "Existing managed file differs"):
            manage.install(self.repo, agent="codex", skills_dir=skills)
        self.assertEqual(changed.read_text(encoding="utf-8"), "local user edit")
        self.assertFalse((installed / "references/new.md").exists())
        result = manage.install(self.repo, agent="codex", skills_dir=skills, overwrite=True)
        self.assertEqual(result["replaced"], 1)
        self.assertEqual(result["new_files"], 1)
        self.assertEqual(unmanaged.read_text(encoding="utf-8"), "keep my notes")
        self.assertEqual(changed.read_bytes(), (self.runtime / "scripts/inventory.py").read_bytes())
        self.assertFalse((installed / "source-archives").exists())
        repeated = manage.install(self.repo, agent="claude", skills_dir=skills)
        self.assertEqual(repeated["copied"], 0)

    def test_install_source_overlap_rejected_without_modifying_source(self):
        before = (self.runtime / "SKILL.md").read_bytes()
        for root in (self.repo, self.runtime / "nested"):
            with self.subTest(root=root):
                with self.assertRaisesRegex(manage.ManagementError, "overlaps"):
                    manage.install(self.repo, agent="codex", skills_dir=root, overwrite=True)
        self.assertEqual((self.runtime / "SKILL.md").read_bytes(), before)
        self.assertFalse((self.runtime / "nested").exists())

    def test_install_rejects_destination_symlink_without_writing_outside(self):
        outside = self.base / "outside-destination"
        outside.mkdir()
        skills = self.base / "symlink-skills"
        skills.mkdir()
        link = skills / manage.SKILL_NAME
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Creating directory symlinks is unavailable on this platform")
        with self.assertRaisesRegex(manage.ManagementError, "symlink"):
            manage.install(self.repo, agent="codex", skills_dir=skills, overwrite=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_default_roots_and_project_install(self):
        fake_home = self.base / "home"
        with patch.object(Path, "home", return_value=fake_home):
            self.assertEqual(manage.installation_root("codex", "user", None), fake_home / ".agents/skills")
            self.assertEqual(manage.installation_root("claude", "user", None), fake_home / ".claude/skills")
        project = self.base / "project"
        result = manage.install(self.repo, agent="claude", scope="project", project=project)
        self.assertEqual(Path(result["destination"]), project / ".claude/skills" / manage.SKILL_NAME)
        self.assertFalse((project / ".claude/settings.json").exists())

    def test_doctor_never_launches_applications_or_installs_packages(self):
        with patch.object(manage.subprocess, "run", side_effect=AssertionError("must not execute")):
            report = manage.doctor()
        self.assertIn("python-docx", report["optional_packages"])
        self.assertIn("Pillow", report["optional_packages"])
        self.assertIn("pypdf", report["optional_packages"])
        self.assertIn("local_docx_rendering_available", report["headless_renderer"])

    def test_main_returns_clean_error_for_validation_failure(self):
        self.write("assets/example.txt", "tampered")
        errors = io.StringIO()
        with patch.object(manage, "validate", side_effect=manage.ManagementError("bad source hash")), contextlib.redirect_stderr(errors):
            self.assertEqual(manage.main(["validate"]), 1)
        self.assertIn("Management error: bad source hash", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
