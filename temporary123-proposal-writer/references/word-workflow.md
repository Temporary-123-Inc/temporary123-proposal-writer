# Portable Word authoring and verification

Use Claude's available document-authoring tools when suitable. Do not assume Claude Code has a preinstalled document skill. The scripts here are a self-contained fallback; they consume researched prose and data composed for the actual opportunity. They do not retrieve links, select prices, write generic proposal content, authenticate to Drive or approve submissions.

## Environment and output locations

- Python 3 and `python-docx` are required for creation/inspection; image handling also needs `Pillow`.
- `pypdf` is useful for reading the bundled price book and source PDFs.
- Rendering needs headless LibreOffice and a PDF rasterizer: `PyMuPDF`, `pypdfium2` or Poppler `pdftoppm`.
- In an environment permitting package installs, install missing dependencies from the standard package registry. In the API container the host must preinstall them; do not run futile network installation loops.
- Resolve paths relative to the installed skill and the task workspace. Do not assume another machine's Windows paths, an installed connector or a particular system Python executable.
- In Claude chat, use the environment's output directory and file-sharing tools (commonly `/mnt/data/output/` when available). In Claude Code, honor the user's output directory. Keep scratch JSON, price/source notes and QA images outside the installed skill folder.

Never use Word COM, UI automation or desktop application takeover. `render_proposal.py` invokes LibreOffice only with `--headless`, or consumes a PDF exported from the same current document through an authorized browser/connector workflow.

## Prepare the content JSON

Obtain the exact current input contract:

```bash
python scripts/create_proposal.py --schema
```

Required keys are `title`, `cover_letter` and a nonempty `sections` array. The cover letter requires a personalized `salutation` and actual `paragraphs`; optional fields include date, recipient lines, closing and unsigned signer lines. `sections` can follow any required volumes/order; each has a `heading`, heading `level`, optional `bookmark`, optional `page_break_before`, and substantive `blocks`.

Block types:

- `paragraph`: `text`, optional `bold` and `keep_with_next`.
- `heading`: `text`, `level` 1–3 and optional `bookmark`.
- `bullet` / `number`: actual provision text, with native Word list styling.
- `table`: `headers`, `rows`, optional deliberate column `widths` in inches and `center_columns` indices. Widths must fit the usable page. All row lengths must match the header.
- `image`: actual file `path`, width in inches, optional `max_height`, truthful `caption`.
- `images`: `items` with image paths/widths and a shared `caption`; useful for complementary views. Relative paths resolve from the JSON file's directory, not automatically from the skill folder.
- `page_break`: an intentional break when needed.

`format` controls font, body/heading size, Letter/A4 page size, margins, line spacing and paragraph spacing. Follow buyer requirements rather than a generic preset. For a bid requiring all 12-point Arial, set `font: "Arial"`, `font_size: 12`, `heading_size: 12`. `header`, `footer`, `subtitle`, `metadata`, `author` and `subject` are optional document fields.

Use unique bookmark names beginning with a letter/underscore and containing at most 40 letters, numbers or underscores. `CoverLetter` is created automatically. For each contents entry, specify the target's exact bookmark, label and actual positive page number; invalid/missing targets are rejected.

The script does not calculate prices, validate source support or prove technical compliance. Calculate approved rates/extensions with decimal arithmetic before writing the JSON. Missing company evidence can be represented by explicit draft fields, but do not leave the narrative as empty headings.

## Create and inspect

```bash
python scripts/create_proposal.py task/proposal-content.json --output task/Proposal_Draft.docx
python scripts/inspect_proposal.py task/Proposal_Draft.docx --require-cover-letter --expected-images 2
```

Use `--expected-images` only with the actual intended count. Creating or inspecting a document reports layout as unverified. A CoverLetter bookmark is a structural aid, not proof that the prose is correct. Review letter, scope, company claims, pricing, forms and completeness semantically.

The builder refuses to overwrite an existing file unless `--overwrite` is used. Overwrite only the task's generated output when iterating, never an original source. The inspector reports unresolved fields. `--submission-ready` additionally fails on draft fields, absent cover-letter bookmark or absent page numbering; it does not authorize signing or submission and cannot guarantee responsiveness.

## Render and update contents

```bash
python scripts/render_proposal.py task/Proposal_Draft.docx --output-dir task/qa-pass-1
```

If LibreOffice is unavailable but authorized Google Docs/browser authoring/export is available, export the exact current document to PDF and run:

```bash
python scripts/render_proposal.py task/Proposal_Draft.docx --pdf-source task/same-document-export.pdf --output-dir task/qa-pass-1
```

The helper cannot prove that a supplied PDF matches the DOCX; confirm that the export comes from the same current content and formatting. Use a fresh QA directory for each pass. `--overwrite` replaces generated QA files in that directory and should be used only for disposable task outputs.

For contents pagination, first build/render without `toc` when pages are unknown. Read the actual section starts, add `toc.entries` with real page references, rebuild and render again; adding contents can shift pagination. Repeat until displayed references and final pages agree. Do not enter guessed page numbers merely to satisfy the JSON contract. When a native document tool can update contents fields, it is also acceptable to use and verify those fields.

Inspect every rendered page, not only the first page or extracted text. Check cover-letter fit, table/header wrapping, row visibility, page breaks, image/caption placement, blank/overflow pages, fonts, footer fields and contents/bookmark navigation. Repair widths/spacing or restructure content rather than shrinking below a mandatory font size. Re-render after meaningful layout changes.

If no permitted renderer/export route works, preserve and deliver the real editable Word draft, state that page layout could not be visually verified, and identify the concrete unavailable capability. Do not invent verification, abandon substantive drafting or open desktop apps as a workaround.

## Delivery

Return only requested deliverables, normally the `.docx`; QA PDFs/PNGs and scratch JSON stay internal. Use Claude's supported file attachment/output-link mechanism. Verify that the saved file exists, opens as a valid DOCX ZIP and contains the full draft, cover letter, tables and intended images. Provide a concise list of actual remaining confirmations outside the buyer-facing document.
