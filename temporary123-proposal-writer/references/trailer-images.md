# Trailer image retrieval and selection

## Approved sources

- Catalog: https://docs.google.com/spreadsheets/d/1tu6szuEWANuI0gtqrsl9g_gQa0Vm256YD7UmsEtouOc/edit?gid=943101906#gid=943101906
- Spreadsheet ID `1tu6szuEWANuI0gtqrsl9g_gQa0Vm256YD7UmsEtouOc`; target gid `943101906`; last inspected tab title `List of Trailers`.
- Header row 1; A `Equipment`, B `Photos`, C `Ehanced` (source spelling), D `Drive`.
- Additional approved source: https://drive.google.com/drive/folders/183wcGD5Zo-fu5qtz-BaTMhrqxxI-EbWC

The spreadsheet is an index of equipment folders, not a grid of embedded images. Use available Google Sheets/Drive connectors or an authorized browser. The skill cannot create access to private files. Keep sources read-only and never change their sharing to embed images.

For company product identity and specifications, first consult the [inventory specification guide](inventory-specifications.md) and selected ItemID in the [technical index](../assets/inventory/product-specifications.json), checking [source workbook cells](../assets/inventory/temporary123-inventory-and-specifications.xlsx) where needed. The image catalog remains the primary source for discovering visuals; its row/category or a photograph does not override inventory specifications, resolve identity conflicts or establish live availability. Match the actual variant before describing a photo as the offered unit.

## Selection workflow

1. Resolve the current tab by its gid. Read bounded relevant rows (initially A1:D80 if appropriate), including hyperlinks, rich-text links, formulas and raw/display values. Expand only as needed.
2. Match equipment family, trailer/container type, length and fixture/stall/bed/machine configuration. A category match alone is insufficient for an exact-model caption.
3. Extract the actual Drive URL in D from the hyperlink/rich text/HYPERLINK formula/value; trim whitespace. Yes/enhanced flags are inventory signals, not proof of source, quality or compliance.
4. List the corresponding folder and useful subfolders. Inspect filenames, MIME types and dimensions where available; then open actual candidates. Select readable, useful views over decorative scenery.
5. Materialize selected files through available authenticated export/download tools for legitimate insertion. Never treat a Drive HTML viewer URL as image bytes. Do not claim insertion when only a link was returned.
6. Insert one or two complementary views near Equipment Specifications with preserved aspect ratios and accurate captions. Keep images/captions together in the final page layout.

Prefer actual equipment photographs when provenance supports that description. Identify known renderings as illustrations. For unconfirmed provenance/configuration, use “representative image,” not “our offered unit” or “field photograph.” Do not alter stall counts, doors, ramps, tanks, fixtures or equipment appearance. Do not substitute stock/generated imagery by default.

Useful caption: “Representative restroom interior; final model, layout, electrical compatibility and tank capacities remain to be confirmed.” Library membership does not establish availability, accessibility certification or specification compliance.

## Bundled restroom fallbacks

The user-designated catalog's row 37, `Restroom Trailer`, linked to `Restroom Only` folder `1urVsllbGMhX-IyybufdG0bbcDqah--kz` when inspected November 13, 2026. Two unchanged source images are bundled:

| Asset | Drive source | Intended use |
|---|---|---|
| `../assets/images/restroom-sink-interior.png` | `1r5-6USyN0FBE0vOtHLJoMCIh4BklsQYQ` | Representative sink/toilet/dispensers; 1435 × 1096. |
| `../assets/images/restroom-urinal-interior.png` | `1wEwo4WrwxIMkUwS9--yN9ad12T-XIue6` | Representative wall-mounted urinal/interior; 1087 × 1446. |

Use them only for relevant restroom proposals, with qualified captions. They do not establish two/three-stall layout, ADA status, tank sizes, electrical load or offered model. Refresh the live catalog when accessible; these are not universal images for kitchen, laundry, berthing or shower-only projects.

Record catalog row, equipment label, source folder/file ID, selected asset and caption qualification in working notes outside the buyer-facing proposal. If no suitable optional image exists, finish without it and note that gap separately. If the buyer requires an image or drawing, ask after source checks and obtain the required input or explicit instruction to deliver an incomplete draft before delivery.
