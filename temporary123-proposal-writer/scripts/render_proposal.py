#!/usr/bin/env python3
"""Render DOCX pages without controlling desktop applications.

Conversion uses LibreOffice --headless. Rasterization needs PyMuPDF, pypdfium2,
or Poppler pdftoppm. --pdf-source accepts a PDF exported from the same document
by an authorized browser/connector workflow when headless conversion is absent.
Every output page still needs visual inspection by Claude.
"""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def render(args):
    source = args.docx.resolve()
    if not source.is_file() or source.suffix.lower() != ".docx":
        raise ValueError("Input must be an existing .docx")
    if not 72 <= args.dpi <= 300:
        raise ValueError("DPI must be between 72 and 300")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if list(out.glob("page-*.png")) and not args.overwrite:
        raise ValueError("Page images already exist; use a fresh QA directory or --overwrite")
    pdf = out / (source.stem + ".pdf")
    if pdf.exists() and not args.overwrite:
        raise ValueError("PDF already exists; use a fresh QA directory or --overwrite")
    mode = "provided-pdf"
    if args.pdf_source:
        supplied = args.pdf_source.resolve()
        if not supplied.is_file() or supplied.read_bytes()[:5] != b"%PDF-":
            raise ValueError("--pdf-source must be the matching exported PDF")
        if supplied != pdf:
            shutil.copy2(supplied, pdf)
    else:
        office = args.soffice or shutil.which("soffice") or shutil.which("libreoffice") or shutil.which("soffice.exe")
        if not office:
            raise ValueError("LibreOffice headless is unavailable. Use an authorized Google Docs/browser export of this same document and rerun with --pdf-source exported.pdf. Do not open or automate desktop Word. Layout has not been verified.")
        if Path(office).name.lower() not in {"soffice", "soffice.exe", "libreoffice", "libreoffice.exe"}:
            raise ValueError("--soffice must identify the LibreOffice command; desktop Word automation is unsupported")
        mode = "libreoffice-headless"
        with tempfile.TemporaryDirectory(prefix="proposal-render-") as temp:
            temp_path = Path(temp)
            profile = temp_path / "profile"
            command = [str(office), "--headless", "-env:UserInstallation=" + profile.as_uri(), "--convert-to", "pdf", "--outdir", str(temp_path), str(source)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout, check=False)
            generated = temp_path / (source.stem + ".pdf")
            if not generated.is_file() or generated.stat().st_size == 0:
                raise ValueError("Headless conversion produced no PDF. " + (completed.stderr or completed.stdout)[-1500:])
            shutil.copy2(generated, pdf)
    if args.overwrite:
        for old in out.glob("page-*.png"):
            if old.parent.resolve() == out and not old.is_symlink():
                old.unlink()
    pages = []
    if importlib.util.find_spec("fitz"):
        import fitz
        with fitz.open(pdf) as document:
            for index, page in enumerate(document):
                target = out / ("page-%03d.png" % (index + 1))
                page.get_pixmap(matrix=fitz.Matrix(args.dpi / 72, args.dpi / 72), alpha=False).save(target)
                pages.append(str(target))
    elif importlib.util.find_spec("pypdfium2"):
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(str(pdf))
        try:
            for index in range(len(document)):
                target = out / ("page-%03d.png" % (index + 1))
                page = document[index]
                try:
                    bitmap = page.render(scale=args.dpi / 72)
                    try:
                        bitmap.to_pil().save(target)
                    finally:
                        bitmap.close()
                finally:
                    page.close()
                pages.append(str(target))
        finally:
            document.close()
    else:
        poppler = args.pdftoppm or shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")
        if not poppler:
            raise ValueError("PDF saved, but no rasterizer is available. Provide PyMuPDF, pypdfium2, or Poppler pdftoppm; layout has not been visually verified. PDF: " + str(pdf))
        completed = subprocess.run([str(poppler), "-png", "-r", str(args.dpi), str(pdf), str(out / "page")], capture_output=True, text=True, timeout=args.timeout, check=False)
        if completed.returncode:
            raise ValueError("PDF rasterization failed: " + completed.stderr[-1500:])
        pages = [str(p) for p in sorted(out.glob("page-*.png"))]
    if not pages:
        raise ValueError("No page images were generated")
    result = {"source_docx": str(source), "pdf": str(pdf), "conversion": mode, "page_count": len(pages), "pages": pages, "visual_review_required": True, "layout_verified": False}
    (out / "render-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("docx", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--pdf-source", type=Path, help="Matching PDF exported through an authorized browser or connector")
    parser.add_argument("--soffice", help="LibreOffice command path, used only with --headless")
    parser.add_argument("--pdftoppm", help="Optional Poppler executable path")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--overwrite", action="store_true", help="Replace this QA directory's generated PDF and page images")
    args = parser.parse_args()
    try:
        result = render(args)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print("Render unavailable or failed: " + str(error), file=sys.stderr); return 2
    print(json.dumps(result, indent=2)); return 0


if __name__ == "__main__":
    sys.exit(main())
