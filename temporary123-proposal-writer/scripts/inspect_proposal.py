#!/usr/bin/env python3
"""Check DOCX integrity, editable structures, links and remaining draft fields.

Dependency: python-docx. This structural check never certifies visual layout.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def inspect(path):
    from docx import Document
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError("ZIP CRC failed: " + bad)
        root = ET.fromstring(archive.read("word/document.xml"))
        footer_codes = " ".join(archive.read(name).decode("utf-8") for name in archive.namelist() if re.fullmatch(r"word/footer\d+\.xml", name))
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs]
    cell_text = [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
    body_text = "\n".join(paragraphs + cell_text)
    bookmarks = [element.get("{" + NS["w"] + "}name") for element in root.findall(".//w:bookmarkStart", NS)]
    links = [element.get("{" + NS["w"] + "}anchor") for element in root.findall(".//w:hyperlink", NS) if element.get("{" + NS["w"] + "}anchor")]
    fields = sorted(set(re.findall(r"\[[^\[\]\r\n]{1,300}\]|\bTBD\b|\{\{[^{}\r\n]{1,100}\}\}", body_text, re.I)))
    errors = []
    unresolved_links = sorted(set(links) - set(bookmarks))
    if unresolved_links:
        errors.append("Internal links have no bookmark target: " + ", ".join(unresolved_links))
    if not any(text.strip() for text in paragraphs):
        errors.append("Document contains no editable narrative paragraphs")
    if len(bookmarks) != len(set(bookmarks)):
        errors.append("Document has duplicate bookmark names")
    sizes = [{"width_inches": round(s.page_width.inches, 3), "height_inches": round(s.page_height.inches, 3)} for s in doc.sections]
    return {
        "file": str(path.resolve()), "zip_integrity": "passed", "paragraphs": len(doc.paragraphs),
        "tables": [{"rows": len(t.rows), "columns": len(t.columns)} for t in doc.tables],
        "images": len(doc.inline_shapes), "bookmarks": bookmarks, "internal_links": len(links),
        "cover_letter_bookmark": "CoverLetter" in bookmarks,
        "page_number_field": bool(re.search(r"\bPAGE\b", footer_codes)),
        "page_sizes": sizes, "draft_fields": fields,
        "headings": [p.text for p in doc.paragraphs if p.style and p.style.name.startswith("Heading")],
        "errors": errors, "visual_layout_verified": False,
        "next_step": "Render and inspect every page; verify contents pagination and source support separately.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path)
    parser.add_argument("--require-cover-letter", action="store_true")
    parser.add_argument("--expected-images", type=int)
    parser.add_argument("--submission-ready", action="store_true", help="Fail on unresolved fields, absent cover letter or absent page numbering")
    args = parser.parse_args()
    try:
        result = inspect(args.docx)
    except ImportError:
        print("Missing dependency: python-docx", file=sys.stderr); return 2
    except (OSError, BadZipFile, KeyError, ET.ParseError, ValueError) as error:
        print("DOCX inspection failed: " + str(error), file=sys.stderr); return 2
    if (args.require_cover_letter or args.submission_ready) and not result["cover_letter_bookmark"]:
        result["errors"].append("CoverLetter bookmark missing; verify the personalized cover letter is present")
    if args.expected_images is not None and result["images"] != args.expected_images:
        result["errors"].append("Image count differs from expected value")
    if args.submission_ready:
        if result["draft_fields"]:
            result["errors"].append("Unresolved draft fields remain")
        if not result["page_number_field"]:
            result["errors"].append("PAGE field missing from footers")
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
