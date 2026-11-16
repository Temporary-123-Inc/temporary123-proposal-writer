"""Placeholder formatting checks preserve exact text and Word XML structures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET


SCRIPTS = Path(__file__).resolve().parents[1] / "temporary123-proposal-writer/scripts"
SPEC = importlib.util.spec_from_file_location("proposal_draft_fields", SCRIPTS / "draft_fields.py")
fields = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fields)
W = fields.W
NS = {"w": W[1:-1]}


def root_xml(content, tag="document"):
    return ET.fromstring(f'<w:{tag} xmlns:w="{W[1:-1]}">{content}</w:{tag}>')


def text(root):
    return "".join(element.text or "" for element in root.iter(W + "t"))


def highlighted_text(root):
    return "".join(text(run) for run in root.iter(W + "r") if fields._red(run))


class DraftFieldTests(unittest.TestCase):
    def test_exact_spans_multiple_fields_and_numeric_citations(self):
        root = root_xml('<w:p><w:r><w:t>Lead [CONFIRM: unit] middle TBD and {{price}}. See [1, 2].</w:t></w:r></w:p>')
        original = text(root)
        self.assertEqual(fields.highlight_fields(root), 3)
        self.assertEqual(text(root), original)
        self.assertEqual(highlighted_text(root), "[CONFIRM: unit]TBD{{price}}")
        self.assertTrue(all(item["red_highlighted"] for item in fields.inspect_fields(root)))
        self.assertEqual(len(fields.inspect_fields(root)), 3)

    def test_split_runs_keep_individual_style_and_surrounding_text(self):
        root = root_xml('<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Before [CON</w:t></w:r>'
                        '<w:r><w:rPr><w:i/></w:rPr><w:t>FIRM: assigned lead] after</w:t></w:r></w:p>')
        original = text(root)
        fields.highlight_fields(root)
        runs = list(root.iter(W + "r"))
        self.assertEqual([text(run) for run in runs], ["Before ", "[CON", "FIRM: assigned lead]", " after"])
        self.assertEqual([fields._red(run) for run in runs], [False, True, True, False])
        self.assertTrue(all(run.find("w:rPr/w:b", NS) is not None for run in runs[:2]))
        self.assertTrue(all(run.find("w:rPr/w:i", NS) is not None for run in runs[2:]))
        self.assertEqual(text(root), original)
        self.assertTrue(fields.inspect_fields(root)[0]["red_highlighted"])

    def test_hyperlinks_bookmarks_drawings_and_page_field_are_preserved(self):
        root = root_xml('<w:p><w:bookmarkStart w:id="1" w:name="scope"/>'
                        '<w:hyperlink w:anchor="scope"><w:r><w:t>See [INSERT: page]</w:t></w:r></w:hyperlink>'
                        '<w:r><w:drawing><w:object/></w:drawing></w:r>'
                        '<w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple>'
                        '<w:bookmarkEnd w:id="1"/></w:p>')
        drawing = ET.tostring(root.find(".//w:drawing", NS))
        field = ET.tostring(root.find(".//w:fldSimple", NS))
        fields.highlight_fields(root)
        link = root.find(".//w:hyperlink", NS)
        self.assertEqual(link.get(W + "anchor"), "scope")
        self.assertEqual(text(link), "See [INSERT: page]")
        self.assertEqual(highlighted_text(link), "[INSERT: page]")
        self.assertEqual(ET.tostring(root.find(".//w:drawing", NS)), drawing)
        self.assertEqual(ET.tostring(root.find(".//w:fldSimple", NS)), field)
        self.assertIsNotNone(root.find(".//w:bookmarkStart", NS))
        self.assertIsNotNone(root.find(".//w:bookmarkEnd", NS))

    def test_tables_headers_footers_and_content_controls(self):
        for tag, content in (
            ("document", '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cost [INSERT: price]</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'),
            ("hdr", '<w:p><w:r><w:t>For [CONFIRM: buyer]</w:t></w:r></w:p>'),
            ("ftr", '<w:p><w:r><w:t>Status TODO</w:t></w:r></w:p>'),
            ("document", '<w:p><w:sdt><w:sdtContent><w:r><w:t>{{assigned manager}}</w:t></w:r></w:sdtContent></w:sdt></w:p>'),
        ):
            with self.subTest(tag=tag, content=content):
                root = root_xml(content, tag)
                before = text(root)
                self.assertEqual(fields.highlight_fields(root), 1)
                self.assertEqual(text(root), before)
                self.assertEqual(len(fields.inspect_fields(root)), 1)
                self.assertTrue(fields.inspect_fields(root)[0]["red_highlighted"])

    def test_nested_textbox_placeholder_is_counted_once(self):
        root = root_xml('<w:p><w:r><w:t>Outer [CONFIRM: buyer]</w:t><w:drawing><w:txbxContent>'
                        '<w:p><w:r><w:t>Inner [INSERT: unit]</w:t></w:r></w:p>'
                        '</w:txbxContent></w:drawing></w:r></w:p>')
        self.assertEqual(fields.highlight_fields(root), 2)
        occurrences = fields.inspect_fields(root)
        self.assertEqual(len(occurrences), 2)
        self.assertTrue(all(item["red_highlighted"] for item in occurrences))

    def test_idempotent_and_preserves_literal_whitespace(self):
        root = root_xml('<w:p><w:r><w:t xml:space="preserve"> Before [CONFIRM: value] after </w:t></w:r></w:p>')
        fields.highlight_fields(root)
        first = ET.tostring(root)
        fields.highlight_fields(root)
        self.assertEqual(ET.tostring(root), first)
        self.assertEqual(text(root), " Before [CONFIRM: value] after ")
        for node in root.iter(W + "t"):
            if node.text[0].isspace() or node.text[-1].isspace():
                self.assertEqual(node.get(fields.XML_SPACE), "preserve")

    def test_marker_does_not_cross_a_line_break(self):
        root = root_xml('<w:p><w:r><w:t>[CONFIRM:</w:t><w:br/><w:t> broken]</w:t></w:r></w:p>')
        self.assertEqual(fields.highlight_fields(root), 0)

    def test_partial_highlight_is_a_gap_and_font_color_is_black(self):
        root = root_xml('<w:p><w:r><w:rPr><w:highlight w:val="red"/></w:rPr><w:t>[CON</w:t></w:r>'
                        '<w:r><w:rPr><w:color w:val="FFFFFF" w:themeColor="accent1"/></w:rPr><w:t>FIRM: lead]</w:t></w:r></w:p>')
        self.assertFalse(fields.inspect_fields(root)[0]["red_highlighted"])
        fields.highlight_fields(root)
        self.assertTrue(fields.inspect_fields(root)[0]["red_highlighted"])
        for run in root.iter(W + "r"):
            color = run.find("w:rPr/w:color", NS)
            self.assertEqual(dict(color.attrib), {W + "val": "000000"})


@unittest.skipUnless(importlib.util.find_spec("docx"), "Optional python-docx is unavailable")
class WordHelperSmokeTests(unittest.TestCase):
    def test_builder_and_inspector_allow_draft_but_reject_submission_ready(self):
        data = {
            "title": "Equipment Support Proposal", "header": "Project [CONFIRM: number]",
            "footer": "Draft [CONFIRM: revision]",
            "cover_letter": {"salutation": "Dear Facilities Team,",
                             "paragraphs": ["We propose facility support at [CONFIRM: site]."]},
            "sections": [{"heading": "Equipment", "blocks": [
                {"type": "paragraph", "text": "We will coordinate delivery with the designated site representative."},
                {"type": "table", "headers": ["Item", "Price"], "rows": [["Supported equipment", "[INSERT: approved price]"]]},
            ]}],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, target = base / "content.json", base / "draft.docx"
            source.write_text(json.dumps(data), encoding="utf-8")
            build = subprocess.run([sys.executable, str(SCRIPTS / "create_proposal.py"), str(source), "--output", str(target)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertEqual(json.loads(build.stdout)["red_highlighted_draft_fields"], 5)
            check = subprocess.run([sys.executable, str(SCRIPTS / "inspect_proposal.py"), str(target), "--require-cover-letter"], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            result = json.loads(check.stdout)
            self.assertEqual(result["draft_fields_without_red_highlight"], [])
            self.assertEqual(len(result["draft_field_occurrences"]), 5)
            self.assertEqual({item["part"] for item in result["draft_field_occurrences"]}, {"word/document.xml", "word/header1.xml", "word/footer1.xml"})
            strict = subprocess.run([sys.executable, str(SCRIPTS / "inspect_proposal.py"), str(target), "--submission-ready"], capture_output=True, text=True)
            self.assertEqual(strict.returncode, 1, strict.stderr)
            self.assertIn("Unresolved draft fields remain", json.loads(strict.stdout)["errors"])

    def test_inspector_finds_unhighlighted_split_field_in_header(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "draft.docx"
            document = Document()
            document.add_paragraph("Supported substantive narrative.")
            paragraph = document.sections[0].header.paragraphs[0]
            paragraph.add_run("[CON")
            paragraph.add_run("FIRM: buyer]")
            document.save(target)
            check = subprocess.run([sys.executable, str(SCRIPTS / "inspect_proposal.py"), str(target)], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            result = json.loads(check.stdout)
            self.assertEqual(result["draft_fields"], ["[CONFIRM: buyer]"])
            self.assertEqual(result["draft_fields_without_red_highlight"][0]["part"], "word/header1.xml")
            self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
