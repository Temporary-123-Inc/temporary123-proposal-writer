#!/usr/bin/env python3
"""Build, query and verify the technical inventory index using Python's standard library."""

import argparse
import hashlib
import json
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "assets/inventory/product-specifications.json"
DEFAULT_SOURCE = ROOT / "assets/inventory/temporary123-inventory-and-specifications.xlsx"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
TECHNICAL_LABELS = {"sku", "type", "product description", "list of equipment"}
ACCESS_CONTENT = re.compile(r"gate\s*code|gps\s*tracker|fleet\.global-view\.net", re.I)


def normalized(value):
    return " ".join(str(value or "").split()).casefold()


def read_sheets(path):
    """Read stored values without recalculating or modifying the workbook."""
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", NS):
                strings.append("".join(t.text or "" for t in item.findall(".//s:t", NS)))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in relationships}
        result = {}
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        for sheet in workbook.findall("s:sheets/s:sheet", NS):
            target = targets[sheet.attrib[f"{{{REL_NS}}}id"]]
            part = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            rows = {}
            for row in ET.fromstring(archive.read(part)).findall("s:sheetData/s:row", NS):
                values = {}
                for cell in row.findall("s:c", NS):
                    if cell.find("s:f", NS) is not None:
                        raise ValueError("Formula encountered; review its meaning before indexing: " + cell.attrib["r"])
                    kind = cell.attrib.get("t")
                    element = cell.find("s:v", NS)
                    value = element.text if element is not None else None
                    if kind == "s" and value is not None:
                        value = strings[int(value)]
                    elif kind == "inlineStr":
                        value = "".join(t.text or "" for t in cell.findall(".//s:t", NS))
                    column = re.match(r"[A-Z]+", cell.attrib["r"]).group()
                    values[column] = value
                rows[int(row.attrib["r"])] = values
            result[sheet.attrib["name"]] = rows
        return result


def build_index(source):
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    sheets = read_sheets(source)
    for name in ("Inventory", "Field details", "Links and images", "Source text"):
        if name not in sheets:
            raise ValueError("Required source sheet missing: " + name)
    if sheets["Inventory"].get(6, {}).get("A") != "Item ID":
        raise ValueError("Inventory schema changed; review the header mapping")
    if sheets["Field details"].get(6, {}).get("F") != "Original value":
        raise ValueError("Field-details schema changed; review the header mapping")

    groups = defaultdict(lambda: defaultdict(list))
    for row, values in sheets["Field details"].items():
        if row < 7 or not values.get("A") or normalized(values.get("E")) not in TECHNICAL_LABELS:
            continue
        label = values.get("E")
        key = (values.get("C"), values.get("D"), label)
        groups[values["A"]][key].append((row, values))

    media = defaultdict(list)
    for row, values in sheets["Links and images"].items():
        if row < 7 or not values.get("A"):
            continue
        if values.get("C") != "Image" and values.get("D") not in ("Photo/video reference", "textarea"):
            continue
        url = values.get("F") or ""
        if not url or ACCESS_CONTENT.search(url):
            continue
        media[values["A"]].append({
            "reference": values.get("C"), "type": values.get("D"),
            "label": values.get("E"), "url": url,
            "source_cell": f"'Links and images'!F{row}", "source_url": values.get("G"),
        })

    records = []
    seen = set()
    for row, values in sorted(sheets["Inventory"].items()):
        if row < 7 or not values.get("A"):
            continue
        item_id = values["A"]
        if item_id in seen:
            raise ValueError("Duplicate Item ID: " + item_id)
        seen.add(item_id)
        flags = []
        if not values.get("B"):
            flags.append("unnamed_record_excluded_from_recommendations")
        specifications = []
        for (field_source, section, label), parts in groups[item_id].items():
            parts.sort(key=lambda x: (int(x[1].get("H") or 0), x[0]))
            value = "".join(p.get("F") or "" for _, p in parts) or None
            cells = [{"sheet": "Field details", "cell": f"F{r}", "row": r,
                      "field_source": field_source, "section": section} for r, _ in parts]
            marker = bool(value and re.search(r"\bNO\s+OFFICIAL\b", value, re.I))
            if value and ACCESS_CONTENT.search(value):
                flags.append("technical_field_contains_internal_access_data_review_original")
                continue
            if marker:
                flags.append("source_placeholder_is_not_a_specification")
            # Coalesce exact duplicate values, retaining every source locator.
            match = next((s for s in specifications if normalized(s["label"]) == normalized(label)
                          and s["value"] == value), None)
            if match:
                match["source_cells"].extend(cells)
            else:
                specifications.append({"label": label, "value": value,
                                       "source_cells": cells, "missing_value_marker": marker})
        for column, label in (("D", "SKU"), ("E", "Type"), ("F", "Product Description"), ("G", "List of Equipment")):
            value = values.get(column)
            locator = {"sheet": "Inventory", "cell": f"{column}{row}", "row": row,
                       "field_source": "Inventory", "section": "Summary"}
            match = next((s for s in specifications if normalized(s["label"]) == normalized(label)
                          and s["value"] == value), None)
            if match:
                match["source_cells"].append(locator)
            elif value and not ACCESS_CONTENT.search(value):
                specifications.append({"label": label, "value": value, "source_cells": [locator],
                                       "missing_value_marker": bool(re.search(r"\bNO\s+OFFICIAL\b", value, re.I))})
        for label in ("Product Description", "List of Equipment"):
            if not any(normalized(s["label"]) == normalized(label) and s["value"]
                       and not s["missing_value_marker"] for s in specifications):
                flags.append("missing_" + normalized(label).replace(" ", "_"))
        for label in TECHNICAL_LABELS:
            variants = {normalized(s["value"]) for s in specifications
                        if normalized(s["label"]) == label and s["value"]}
            if len(variants) > 1:
                flags.append("review_source_variants_" + label.replace(" ", "_"))
        # These are verified source-specific naming conflicts, not corrected values.
        if source_hash == "62006b7f894c3ae9f2d5cb436819efb86851dc64f7519860535fe10d2179ec37" and row in (92, 98):
            flags.append(f"review_name_sku_configuration_conflict_Inventory_B{row}_D{row}")
        records.append({
            "item_id": item_id, "display_name": values.get("B"), "sku": values.get("D"),
            "category": values.get("C"), "type": values.get("E"), "inventory_row": row,
            "source_url": values.get("W"), "specifications": specifications,
            "media": media[item_id], "review_flags": sorted(set(flags)),
        })
    title_note = sheets["Inventory"].get(3, {}).get("A") or ""
    date = re.search(r"Extracted (\d{4}-\d{2}-\d{2})", title_note)
    return {
        "schema_version": 1,
        "source": {"workbook": source.name, "sha256": source_hash,
                   "source_snapshot_date": date.group(1) if date else None,
                   "source_url": "https://temporary123.glide.page/dl/08a746"},
        "scope": "Internal technical lookup. Operational/access/client/driver/tracker data remains in the original workbook.",
        "record_count": len(records), "named_record_count": sum(bool(r["display_name"]) for r in records),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    build.add_argument("--output", type=Path, default=DEFAULT_INDEX)
    for name in ("find", "show", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--index", type=Path, default=DEFAULT_INDEX)
        if name == "find":
            command.add_argument("--query", default="")
            command.add_argument("--category")
            command.add_argument("--limit", type=int, default=5)
        elif name == "show":
            command.add_argument("--item-id", required=True)
        else:
            command.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    if args.command == "build":
        data = build_index(args.source)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"records": data["record_count"], "named": data["named_record_count"],
                          "output": str(args.output), "source_sha256": data["source"]["sha256"]}))
        return
    data = json.loads(args.index.read_text(encoding="utf-8"))
    if args.command == "verify":
        rebuilt = build_index(args.source)
        if data != rebuilt:
            raise ValueError("Inventory index differs from source. Rebuild and review it before use.")
        print(json.dumps({"verified": True, "records": data["record_count"],
                          "named": data["named_record_count"], "source_sha256": data["source"]["sha256"]}))
    elif args.command == "show":
        record = next((r for r in data["records"] if r["item_id"] == args.item_id), None)
        if record is None:
            raise ValueError("Item ID not found: " + args.item_id)
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        if not 1 <= args.limit <= 50:
            raise ValueError("--limit must be between 1 and 50")
        terms = normalized(args.query).split()
        matches = []
        for record in data["records"]:
            if not record["display_name"]:
                continue
            if args.category and normalized(record["category"]) != normalized(args.category):
                continue
            text = normalized(" ".join(str(record.get(k) or "") for k in
                                       ("item_id", "display_name", "sku", "category", "type")) + " " +
                              " ".join(s["value"] or "" for s in record["specifications"]))
            if all(term in text for term in terms):
                matches.append({k: record[k] for k in
                                ("item_id", "display_name", "sku", "category", "inventory_row", "review_flags")})
        print(json.dumps({"matched": len(matches), "returned": min(len(matches), args.limit),
                          "records": matches[:args.limit]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        print("Inventory error: " + str(error), file=sys.stderr)
        sys.exit(1)
