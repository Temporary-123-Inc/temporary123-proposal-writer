# Word authoring and portable fallback

## Use the host's document capability first

Use the current host's native document-authoring capability first when available. In Codex, follow the Documents skill's current requirements, including artifact-operation markers, runtime selection and render checks, and locate bundled dependencies through its loader. In Claude, use available native file/document capabilities without assuming Codex-only skills or tools exist. See the matching [Codex adapter](platform-codex.md) or [Claude adapter](platform-claude.md). Do not copy managed plugin code or hardcode another user's runtime path.

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

The helper writes supplied substantive content rather than a generic proposal template. Populate supported facts and prices, and use a precise descriptive placeholder such as `[CONFIRM: assigned field-service lead and time allocation]` only where a required answer remains unresolved. Keep generic preparation commands and the completion checklist outside the buyer-facing document. Calculate supported prices with decimal arithmetic before passing them to the helper; it does not audit source support, capabilities, responsiveness or price calculations.

Apply **native Word red highlighting** to the exact placeholder text, including its delimiters, with black/readable text. This applies to descriptive `[CONFIRM: ...]` / `[INSERT: ...]` fields and any remaining `TBD` wherever they occur, including tables, the cover letter, headers/footers and captions. Highlight only the replaceable span, not the surrounding sentence, paragraph or table cell; red font alone is not the requested highlighting. Represent required unsigned signature/date inputs with descriptive highlighted placeholders when manual input is needed, and list them as execution actions; never manufacture a signature or execution date. The portable builder applies this formatting to recognized placeholders; check the actual output rather than assuming an authoring tool preserved it.

```bash
python scripts/create_proposal.py task/proposal-content.json --output task/Proposal_Draft.docx
python scripts/inspect_proposal.py task/Proposal_Draft.docx --require-cover-letter --expected-images 2
```

Use the real intended image count. Existing outputs are not overwritten without `--overwrite`; use that only for the task's generated document. The inspector checks ZIP integrity, editable structures, navigation links, page-number fields and unresolved draft fields. A cover-letter bookmark is not proof of correct prose. For ordinary draft review, run the inspector without `--submission-ready`: unresolved draft fields are findings to include in the delivery report, not a reason to withhold the Word draft. Reserve `--submission-ready` for an explicitly requested pre-submission check; it rejects draft fields and missing structural elements but does not authorize submission or guarantee compliance.

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

Inspect every rendered page. Check cover-letter fit, table header/row wrapping, page breaks, captions paired with images, accidental blank pages, fonts, footers and contents alignment. Confirm that every remaining placeholder has visible red highlighting over only its exact replaceable text and remains legible; repair missing highlighting or highlighting that spills into supported prose. Repair layout and re-render changed content. Structural inspection alone never establishes visual correctness.

Before delivery, use existing sources and ask about unresolved inputs with supported recommendations, then deliver the substantive editable Word draft even when answers are pending. Clearly mark unresolved required fields and provisional product selections, with red highlighting on their exact replaceable placeholder spans; do not turn a recommendation into an approved choice or invent facts, rates or compliance. Audit every remaining placeholder and unfinished required action against the final rendered pages for the [final delivery report](delivery-report.md), including what is needed and who must supply it. The structural inspector alone cannot assign page numbers or establish completeness. Report rendering limitations honestly and reflect them in readiness. Normal unsigned execution lines may remain in drafts, but required signature/date input needs a descriptive highlighted placeholder and remains an unfinished submission action. Missing answers or incomplete readiness do not require separate permission to deliver a draft.

Follow the [final delivery report](delivery-report.md). Save/upload the actual stored `.docx` without silently converting it into a native Doc, set and verify Anyone-with-link Viewer access for that generated output, and use the service's actual file URL. Preserve source/folder permissions; company/domain-only access is not public link access. Use permitted storage/permission tools or an authorized browser, never desktop takeover or invented tool arguments. If public sharing is blocked, provide the actual available artifact and state the unfinished sharing action honestly.

Return **Link**, **What to update**, **Readiness**, **Winning chances and improvements** in that order, with the source-status table within Readiness. Keep the page/location/action audit and competitiveness analysis outside the client Word document. QA PDFs, PNGs and scratch inputs remain internal unless requested. Use the current host's required file-citation format when available alongside the actual cloud Word link.
