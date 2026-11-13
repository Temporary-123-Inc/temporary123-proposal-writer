# Codex Word authoring and portable fallback

## Use the host's document capability first

When the Documents skill is available, read and follow its current instructions, including any artifact-operation marker, runtime selection, source editing and render checks. Locate the host's bundled runtimes through its dependency loader when available. Do not copy managed plugin code into this package or hardcode another user's runtime installation path.

This skill repository includes three independent Python helpers for environments without the Documents capability. They require Python 3 and `python-docx`; image work needs `Pillow`. Reading the bundled PDFs uses `pypdf`. Rendering additionally requires headless LibreOffice and either `PyMuPDF`, `pypdfium2` or Poppler. Use permitted installed/bundled dependencies; do not claim that a skill installs software or grants access by itself.

Keep output, researched content JSON, calculations, source notes and QA files in the task workspace, outside the installed skill. Helpers do not retrieve links, write a proposal from an unknown scope, choose prices, sign forms or submit bids.

## Compose the actual proposal content

Inspect the builder's exact JSON input contract:

```bash
python scripts/create_proposal.py --schema
```

Required fields: `title`, a `cover_letter` with personalized `salutation` and substantive `paragraphs`, and a nonempty `sections` array. Each section has a heading, level, optional unique bookmark, optional page-break instruction and actual content blocks. Preserve the buyer's required volumes and order.

Supported blocks are paragraphs, headings, native bullet/number lists, native tables, individual images, image groups and page breaks. Tables accept headers, rows, deliberate column widths in inches and centered-column indices. Images accept an actual file path, width, optional maximum height and truthful caption. Image paths relative to the content JSON resolve from that JSON's directory; resolve bundled assets explicitly when composing input.

`format` controls font, body/heading sizes, Letter/A4 page dimensions, margins, line spacing and paragraph spacing. Follow buyer requirements, including mandatory font sizes in tables and captions. Defaults are Letter and Arial 12. Optional metadata, header/footer, subtitle, author and subject remain editable.

The helper writes complete supplied content rather than a generic proposal template. Calculate approved prices with decimal arithmetic before passing them to it; it does not audit source support, capabilities, responsiveness or price calculations.

```bash
python scripts/create_proposal.py task/proposal-content.json --output task/Proposal_Draft.docx
python scripts/inspect_proposal.py task/Proposal_Draft.docx --require-cover-letter --expected-images 2
```

Use the real intended image count. Existing outputs are not overwritten without `--overwrite`; use that only for the task's generated document. The inspector checks ZIP integrity, editable structures, navigation links, page-number fields and unresolved draft fields. A cover-letter bookmark is not proof of correct prose. `--submission-ready` additionally rejects draft fields and missing structural elements; it does not authorize submission or guarantee compliance.

## Rendering without desktop takeover

Try the available Documents renderer first and diagnose any failure. The portable renderer invokes LibreOffice only with `--headless`:

```bash
python scripts/render_proposal.py task/Proposal_Draft.docx --output-dir task/qa-pass-1
```

If headless conversion is unavailable, use authorized Google Docs/browser services to import/open the actual document and export its current version to PDF, following the host's document and connector instructions. Then:

```bash
python scripts/render_proposal.py task/Proposal_Draft.docx --pdf-source task/same-document-export.pdf --output-dir task/qa-pass-1
```

Confirm the PDF is from the exact current content and layout; the helper cannot prove that a supplied PDF matches the DOCX. Use fresh QA directories for successive passes. Never switch to Word COM, native-app GUI control or desktop takeover. Do not change source sharing to obtain an export. If no permitted rendering route works, preserve the editable draft and report the concrete verification limitation; never claim a visual pass that did not occur.

## Contents and final review

Use Word heading styles and real bookmark targets. For explicit helper contents entries, provide labels, exact target bookmark names and verified positive page numbers. When pages are unknown, build/render without `toc`, obtain real section starts, add entries, then rebuild/render and adjust until pagination matches. Adding contents can itself move pages. Do not invent page numbers to satisfy an input field.

Inspect every rendered page. Check cover-letter fit, table header/row wrapping, page breaks, captions paired with images, accidental blank pages, fonts, footers and contents alignment. Repair layout and re-render changed content. Structural inspection alone never establishes visual correctness.

Before delivery, apply `SKILL.md`'s required-input rule: use the existing sources, ask for required missing answers and obtain those answers or explicit instruction to deliver an incomplete draft. Rendering limitations do not waive this rule. Return the actual `.docx` through the host's supported artifact/file-link mechanism; keep any explicitly authorized unresolved items in a separate concise note. Normal unsigned execution lines may remain blank. QA PDFs, PNGs, scratch inputs and source logs are not deliverables unless requested. If a Google Docs copy is created with the user's authorization, verify its native ID/URL before sharing it. Use the current host's required file-citation format when available; otherwise provide an ordinary verified file link.
