# Trailer image selection

## Approved source and verified layout

- Spreadsheet: [Websites Project - List of Trailers](https://docs.google.com/spreadsheets/d/1tu6szuEWANuI0gtqrsl9g_gQa0Vm256YD7UmsEtouOc/edit?gid=943101906#gid=943101906).
- Spreadsheet ID: `1tu6szuEWANuI0gtqrsl9g_gQa0Vm256YD7UmsEtouOc`.
- Target sheet ID/gid: `943101906`; inspected tab title: `List of Trailers`.
- Header row: row 1. Column A: `Equipment`; B: `Photos`; C: `Ehanced` (the source's spelling); D: `Drive`.
- Column D links to equipment-specific Google Drive folders. The sheet is a photo index rather than a grid of directly embedded photos. Some rows are category labels with no folder.

The inspected catalog includes kitchens, dishwashing units, refrigerated trailers/containers, multifunctional units, laundry units, shower/restroom combinations, shower containers/trailers, sleeping/accommodation units, and supporting equipment. Do not assume each listed category has an available folder or exact configuration. Refresh the relevant live rows rather than freezing the current file list into every proposal.

The user's additional supporting-document repository also provides a verified [PHOTOS and VIDEOS folder](https://drive.google.com/drive/folders/183wcGD5Zo-fu5qtz-BaTMhrqxxI-EbWC). Use its matching product folders as an additional approved source when the spreadsheet lacks a suitable view. Apply the same configuration, visual-inspection, provenance and caption checks; do not substitute unrelated images simply to fill a page.

For offline discovery, `assets/catalog/trailer-image-catalog.json` retains only the designated List of Trailers tab's columns A–D, with values, formulas, hyperlinks and rich-text links. No other workbook tabs are bundled. It is a dated snapshot; refresh the relevant live rows when access permits. Two unchanged images from row 37's Restroom Only folder are bundled at `assets/images/restroom-sink-interior.png` and `assets/images/restroom-urinal-interior.png`. Use them only as relevant, clearly captioned representative restroom views; they do not establish a model, stall count, electrical rating, tank capacity, accessibility or availability. Source IDs and hashes appear in `assets/source-provenance.json`.

## Locate candidate assets

1. Load the Google Sheets skill and its live-read safety reference. Read workbook metadata and resolve the current tab title by sheet ID `943101906`. Use this target tab; unrelated tabs are not part of the image catalog.
2. Read a bounded range with the verified tab name, initially `A1:D80` or a smaller relevant range within current grid bounds. Include displayed values, formulas, `hyperlink`, and `textFormatRuns` so linked text is not lost. If the catalog has grown, read further bounded blocks only as needed.
3. Match the proposed unit to the equipment label in A: product type, length, trailer versus container, stall/bed/machine count, and relevant configuration. Broad category similarity is insufficient for a caption that claims an exact model. For an unconfirmed offered model, use only a clearly labeled representative image of the appropriate type, or omit it when it could mislead.
4. Extract D's actual link from `hyperlink`, rich-text runs, a HYPERLINK formula, or the displayed/raw URL as applicable. Trim surrounding whitespace. `Photos = Yes` and `Ehanced = Yes` are inventory indicators, not links or proof of quality/provenance. A blank flag does not negate a valid folder link.
5. Load the Google Drive skill. List the linked folder and relevant image subfolders through the connector. Inspect filenames, MIME types, dimensions/size when available, then preview the actual candidates. Download selected original files through the authenticated connector/file-reference workflow when needed for document insertion. Keep the catalog and source files read-only; do not change sharing to make an image embeddable.

A verified example is row 2, `24ft Mobile Kitchen`, whose folder is `https://drive.google.com/drive/folders/1OunVHARHYsXf8RxLP02Kb0xsWSUMt2fm`. At inspection it held four PNG interior/feature views, including `mobile-commercial-kitchen-entry-view.png`. Another inspected folder for the `30ft Luxury Shower-Restroom Combination Trailer (8 Individual Stalls)` is `https://drive.google.com/drive/folders/1OEk_GG66gYVgBH6ZS-u30-Kb4V0Gy4RG`. These examples demonstrate the retrieval path; recheck the live matching row instead of reusing those folders for unrelated equipment.

## Choose good images

Prioritize truthful fit, then useful detail and visual quality. Review the image pixels before selection; filenames and enhancement flags alone do not establish what the image shows.

- Choose sharp, well-lit, adequately sized images with an unobstructed view. Prefer clear equipment presentation and relevant features over decorative scenery.
- Use complementary views when available: an exterior/access view plus an interior showing the layout or function relevant to the requirement. One useful image may be enough; normally keep to one or two per equipment type and avoid repeating near-identical angles.
- Reject blurry thumbnails, awkward/clipped views, misleading composites, wrong equipment types/configurations, and images that conflict with the written offer. Do not crop out features in a way that changes the apparent layout or capability.
- Prefer actual equipment photographs where available. A supplied enhanced image may be used when it remains a faithful depiction. Label a supplied rendering/illustration as such; do not describe it as a field photograph. If provenance or configuration is uncertain, use a qualified representative caption or omit the asset.
- Do not use ImageGen or external stock as the automatic fallback for missing inventory photos. Do not alter stall counts, ramps, doors, fixtures, equipment, logos, or apparent condition to support an unsupported claim.

## Place and describe the selection

Place images near the corresponding Equipment Specifications text, with a concise descriptive caption. For example: `Representative mobile kitchen interior; final configuration subject to confirmation.` Use an exact unit/model caption only when verified. A photo is not proof of availability, occupancy, dimensions, accessibility, certification, or service performance.

For chat, prefer the connector's supported native preview or a permitted image embed. Materialize an authenticated source file through the normal file workflow only when needed for legitimate inspection or output; do not download remote media to evade a presentation restriction. If inline display is unsupported, give a descriptive source-file link with the caption and intended section. Do not claim the file was inserted when only a link was returned. Do not use a Drive HTML viewer URL as if it were a direct image URL.

For requested Google Docs, Word, or PDF output, insert the chosen source files through the appropriate document workflow. Preserve aspect ratios, avoid upscaling small images, use consistent sizing and captions, and visually check the final rendered pages for legibility and page fit. Use the full source asset rather than a screenshot of the Drive viewer.

Keep the equipment label, sheet row, Drive folder, selected file ID/name and any representative/rendering qualification in working notes or a short source note outside the client-facing proposal. If there is no suitable optional match, continue without an image and note that gap separately. If an image or drawing is required by the buyer, ask for the missing input after source checks and follow the required-input rule in `SKILL.md` before delivery.
