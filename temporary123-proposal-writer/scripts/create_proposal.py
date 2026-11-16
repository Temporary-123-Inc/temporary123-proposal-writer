#!/usr/bin/env python3
"""Create an editable proposal DOCX from researched, task-specific JSON prose.

Dependency: python-docx. No network, desktop automation, or embedded proposal text.
Use --schema to print the input contract. Relative image paths use the JSON folder.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from draft_fields import TEXT_PART, highlight_fields


SCHEMA = {
    "required": ["title", "cover_letter", "sections"],
    "format": {
        "font": "Arial", "font_size": 12, "heading_size": 12,
        "page_size": "Letter", "margins": {"top": 0.7, "bottom": 0.7, "left": 0.7, "right": 0.7},
        "line_spacing": 1.05, "paragraph_after": 6,
    },
    "title": "Actual project title",
    "subtitle": "Optional solicitation and buyer information",
    "metadata": ["Optional date or contact line"],
    "author": "Company legal name", "header": "Optional running header",
    "footer": "DRAFT FOR REVIEW",
    "cover_letter": {
        "date": "Actual date or explicit draft field", "recipient": ["Name", "Agency", "Address"],
        "salutation": "Personalized salutation", "paragraphs": ["Actual proposal-specific letter prose"],
        "closing": "Respectfully,", "signer": ["Unsigned name", "Title", "Company"],
    },
    "toc": {"title": "Contents", "entries": [{"label": "Actual section heading", "bookmark": "scope", "page": 3}]},
    "sections": [{
        "heading": "Actual section heading", "level": 1, "bookmark": "scope", "page_break_before": True,
        "blocks": [
            {"type": "paragraph", "text": "Actual researched narrative", "bold": False},
            {"type": "heading", "text": "Actual subsection", "level": 2, "bookmark": "subsection"},
            {"type": "bullet", "text": "Actual provision"},
            {"type": "number", "text": "Actual ordered provision"},
            {"type": "table", "headers": ["Description", "Price"], "widths": [5.6, 1.5],
             "rows": [["Actual item", "Approved price"]], "center_columns": [1]},
            {"type": "image", "path": "image.png", "width": 4.5, "max_height": 4.0,
             "caption": "Accurate equipment caption"},
            {"type": "images", "items": [{"path": "image.png", "width": 3.0}], "caption": "Accurate group caption"},
            {"type": "page_break"},
        ],
    }],
    "notes": "Write full supported content first. Use descriptive [CONFIRM: missing fact] or [INSERT: required value] fields for unresolved inputs; the builder gives only those spans native red highlighting. TBD, TODO and {{fields}} are also recognized. TOC pages must come from actual rendered pagination, not inference. Measurements are inches except font sizes and paragraph spacing in points.",
}


def build(data, output, base):
    try:
        from docx import Document
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Inches, Pt, RGBColor
    except ImportError as error:
        raise ValueError("Missing dependency python-docx. Install it in an environment permitting packages, or use an available document authoring tool.") from error

    if not isinstance(data, dict) or not str(data.get("title", "")).strip():
        raise ValueError("title is required")
    letter = data.get("cover_letter")
    if not isinstance(letter, dict) or not letter.get("salutation"):
        raise ValueError("cover_letter with a personalized salutation is required")
    if not isinstance(letter.get("paragraphs"), list) or not letter["paragraphs"] or not all(isinstance(x, str) and x.strip() for x in letter["paragraphs"]):
        raise ValueError("cover_letter.paragraphs must contain actual letter prose")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("sections must contain a substantive proposal body")
    content = [b for s in sections if isinstance(s, dict) for b in s.get("blocks", []) if isinstance(b, dict)]
    if not any(
        (b.get("type", "paragraph") in ("paragraph", "bullet", "number") and str(b.get("text", "")).strip())
        or (b.get("type") == "table" and any(str(cell).strip() for row in b.get("rows", []) for cell in row))
        for b in content
    ):
        raise ValueError("sections cannot be only empty headings")

    fmt = data.get("format", {})
    font = str(fmt.get("font", "Arial"))
    size = float(fmt.get("font_size", 12))
    heading_size = float(fmt.get("heading_size", size))
    if not 8 <= size <= 24 or not 8 <= heading_size <= 36:
        raise ValueError("font sizes are outside a practical range")
    doc = Document()
    section = doc.sections[0]
    page_size = fmt.get("page_size", "Letter")
    dimensions = {"Letter": (8.5, 11), "A4": (8.2677, 11.6929)}
    if page_size not in dimensions:
        raise ValueError("format.page_size must be Letter or A4")
    page_width, page_height = dimensions[page_size]
    section.page_width, section.page_height = Inches(page_width), Inches(page_height)
    margins = fmt.get("margins", {})
    for side in ("top", "bottom", "left", "right"):
        val = float(margins.get(side, 0.7))
        if not 0.25 <= val <= 2:
            raise ValueError("margins must be between 0.25 and 2 inches")
        setattr(section, side + "_margin", Inches(val))
    section.header_distance = section.footer_distance = Inches(0.25)
    available = page_width - section.left_margin.inches - section.right_margin.inches
    used_bookmarks, toc_targets = set(), []

    for name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3", "List Bullet", "List Number", "Caption", "Header", "Footer"):
        style = doc.styles[name]
        style.font.name = font
        style.font.size = Pt(heading_size if name.startswith("Heading") or name == "Title" else size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.underline = False
        style.paragraph_format.space_after = Pt(float(fmt.get("paragraph_after", 6)))
        style.paragraph_format.line_spacing = float(fmt.get("line_spacing", 1.05))
        rpr = style.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is not None:
            for key in list(rf.attrib):
                if "Theme" in key:
                    del rf.attrib[key]
        ppr = style.element.find(qn("w:pPr"))
        if ppr is not None:
            for border in list(ppr.findall(qn("w:pBdr"))):
                ppr.remove(border)
        if name.startswith("Heading") or name == "Title":
            style.font.bold = True
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(9)

    doc.core_properties.title = str(data["title"])
    doc.core_properties.author = str(data.get("author", ""))
    doc.core_properties.subject = str(data.get("subject", ""))

    def bookmark(paragraph, name):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,39}", name):
            raise ValueError("bookmark names must start with a letter/underscore and contain at most 40 letters, numbers or underscores")
        if name in used_bookmarks:
            raise ValueError("duplicate bookmark: " + name)
        number = len(used_bookmarks) + 1
        used_bookmarks.add(name)
        a, b = OxmlElement("w:bookmarkStart"), OxmlElement("w:bookmarkEnd")
        a.set(qn("w:id"), str(number)); a.set(qn("w:name"), name)
        b.set(qn("w:id"), str(number))
        paragraph._p.insert(0, a); paragraph._p.append(b)

    def paragraph(text, style=None, bold=False, keep=False):
        para = doc.add_paragraph(style=style)
        para.add_run(str(text)).bold = bold
        para.paragraph_format.keep_with_next = keep
        return para

    def lines(value):
        return "\n".join(str(x) for x in value) if isinstance(value, list) else str(value or "")

    def heading(text, level, anchor=None):
        if level not in (1, 2, 3):
            raise ValueError("heading level must be 1, 2 or 3")
        para = doc.add_heading(str(text), level)
        if anchor:
            bookmark(para, anchor)
        return para

    def add_images(items, caption):
        if not items:
            raise ValueError("image block needs at least one image")
        widths = [float(item.get("width", 4.5)) for item in items]
        if any(w <= 0 for w in widths) or sum(widths) + max(0, len(items) - 1) * 0.1 > available + 0.01:
            raise ValueError("image widths exceed the usable page width")
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next = bool(caption)
        for index, (item, width) in enumerate(zip(items, widths)):
            file = Path(str(item.get("path", ""))).expanduser()
            file = file if file.is_absolute() else base / file
            if not file.is_file():
                raise ValueError("image file not found: " + str(file))
            if index:
                para.add_run(" ")
            shape = para.add_run().add_picture(str(file), width=Inches(width))
            maximum = float(item.get("max_height", 5.5))
            if shape.height > Inches(maximum):
                factor = Inches(maximum) / shape.height
                shape.width = int(shape.width * factor)
                shape.height = Inches(maximum)
        if caption:
            paragraph(caption, "Caption").alignment = WD_ALIGN_PARAGRAPH.CENTER

    def add_table(block):
        headers, rows = block.get("headers"), block.get("rows")
        if not isinstance(headers, list) or not headers or not isinstance(rows, list) or not rows:
            raise ValueError("table requires nonempty headers and rows")
        count = len(headers)
        if any(not isinstance(row, list) or len(row) != count for row in rows):
            raise ValueError("every table row must match its header count")
        widths = block.get("widths", [available / count] * count)
        if len(widths) != count or any(float(w) <= 0 for w in widths) or sum(float(w) for w in widths) > available + 0.01:
            raise ValueError("table widths must match columns and fit the usable page width")
        table = doc.add_table(rows=1, cols=count)
        table.autofit = False
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for column, width in zip(table.columns, widths):
            column.width = Inches(float(width))
        for cell, text in zip(table.rows[0].cells, headers):
            cell.text = str(text)
        for row in rows:
            for cell, text in zip(table.add_row().cells, row):
                cell.text = str(text)
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        for number, row in enumerate(table.rows):
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for index, cell in enumerate(row.cells):
                cell.width = Inches(float(widths[index]))
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                pr = cell._tc.get_or_add_tcPr()
                padding = OxmlElement("w:tcMar")
                for side, value in (("top", 70), ("bottom", 70), ("left", 90), ("right", 90)):
                    element = OxmlElement("w:" + side)
                    element.set(qn("w:w"), str(value)); element.set(qn("w:type"), "dxa")
                    padding.append(element)
                pr.append(padding)
                borders = OxmlElement("w:tcBorders")
                for side in ("top", "left", "bottom", "right"):
                    element = OxmlElement("w:" + side)
                    for key, value in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
                        element.set(qn("w:" + key), value)
                    borders.append(element)
                pr.append(borders)
                shade = OxmlElement("w:shd")
                shade.set(qn("w:fill"), "E2E8ED" if number == 0 else ("F6F7F8" if number % 2 == 0 else "FFFFFF"))
                pr.append(shade)
                for para in cell.paragraphs:
                    para.paragraph_format.space_after = Pt(0)
                    para.paragraph_format.line_spacing = 1.0
                    if index in block.get("center_columns", []):
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in para.runs:
                        run.font.name = font; run.font.size = Pt(size); run.bold = number == 0
        paragraph("").paragraph_format.space_after = Pt(0)

    if data.get("header"):
        section.header.paragraphs[0].text = str(data["header"])
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run(str(data.get("footer", "DRAFT FOR REVIEW")) + "  |  ")
    field = OxmlElement("w:fldSimple"); field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    title = paragraph(data["title"], "Title")
    bookmark(title, "CoverLetter")
    if data.get("subtitle"):
        paragraph(data["subtitle"], "Subtitle")
    for text in data.get("metadata", []):
        paragraph(text)
    for key in ("date", "recipient", "salutation"):
        if letter.get(key):
            paragraph(lines(letter[key]))
    for text in letter["paragraphs"]:
        if not str(text).strip():
            raise ValueError("cover letter contains an empty paragraph")
        paragraph(text)
    paragraph(str(letter.get("closing", "Respectfully,")))
    paragraph(lines(letter.get("signer", "[INSERT: authorized signatory details]")))

    toc = data.get("toc")
    if toc:
        if not isinstance(toc, dict) or not isinstance(toc.get("entries"), list) or not toc["entries"]:
            raise ValueError("toc must include explicit entries with verified page numbers")
        doc.add_page_break()
        heading(toc.get("title", "Contents"), 1, "Contents")
        for entry in toc["entries"]:
            if not isinstance(entry.get("page"), int) or entry["page"] < 1:
                raise ValueError("every TOC entry needs an actual positive page number")
            target = entry.get("bookmark")
            if not target:
                raise ValueError("TOC entry needs a bookmark target")
            toc_targets.append(target)
            para = doc.add_paragraph()
            para.paragraph_format.tab_stops.add_tab_stop(Inches(available), WD_TAB_ALIGNMENT.RIGHT)
            link = OxmlElement("w:hyperlink"); link.set(qn("w:anchor"), target)
            run, text = OxmlElement("w:r"), OxmlElement("w:t")
            text.text = str(entry.get("label", target)); run.append(text); link.append(run); para._p.append(link)
            para.add_run("\t" + str(entry["page"]))

    for index, item in enumerate(sections):
        if not isinstance(item, dict) or not item.get("heading"):
            raise ValueError("each section needs a heading")
        if item.get("page_break_before", index == 0):
            doc.add_page_break()
        anchor = item.get("bookmark", "Section_" + str(index + 1))
        heading(item["heading"], int(item.get("level", 1)), anchor)
        for block in item.get("blocks", []):
            kind = block.get("type", "paragraph")
            if kind in ("paragraph", "bullet", "number"):
                paragraph(block.get("text", ""), {"bullet": "List Bullet", "number": "List Number"}.get(kind), block.get("bold", False), block.get("keep_with_next", False))
            elif kind == "heading":
                heading(block["text"], int(block.get("level", 2)), block.get("bookmark"))
            elif kind == "table":
                add_table(block)
            elif kind == "image":
                add_images([block], block.get("caption", ""))
            elif kind == "images":
                add_images(block.get("items", []), block.get("caption", ""))
            elif kind == "page_break":
                doc.add_page_break()
            else:
                raise ValueError("unknown block type: " + str(kind))
    missing = set(toc_targets) - used_bookmarks
    if missing:
        raise ValueError("TOC targets do not exist: " + ", ".join(sorted(missing)))
    highlighted = 0
    for part in doc.part.package.parts:
        if TEXT_PART.fullmatch(str(part.partname).lstrip("/")) and hasattr(part, "element"):
            highlighted += highlight_fields(part.element)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    return {"output": str(output), "tables": len(doc.tables), "images": len(doc.inline_shapes), "bookmarks": len(used_bookmarks), "red_highlighted_draft_fields": highlighted, "layout_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", type=Path, help="UTF-8 JSON containing full researched proposal content")
    parser.add_argument("--output", type=Path, help="New .docx destination")
    parser.add_argument("--schema", action="store_true", help="Print JSON input schema and exit")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing generated output file")
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(SCHEMA, indent=2)); return 0
    if not args.input or not args.output:
        parser.error("input and --output are required unless --schema is used")
    if args.output.suffix.lower() != ".docx":
        parser.error("--output must end in .docx")
    if args.output.exists() and not args.overwrite:
        parser.error("output exists; use another path or --overwrite for the generated file")
    try:
        result = build(json.loads(args.input.read_text(encoding="utf-8-sig")), args.output.resolve(), args.input.resolve().parent)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print("Proposal creation failed: " + str(error), file=sys.stderr); return 2
    print(json.dumps(result, indent=2)); return 0


if __name__ == "__main__":
    sys.exit(main())
