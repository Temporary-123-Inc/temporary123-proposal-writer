#!/usr/bin/env python3
"""Read the price catalog and calculate explicit, source-traceable quote lines.

This helper uses explicit catalog rates and approved billing metadata without
prorating or inventing rental periods. Its totals are calculations for requested
lines, not compliance or availability confirmations. Dependencies are standard
library only.
"""

import argparse
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "assets/pricing/rate-catalog.json"
CENT = Decimal("0.01")


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream, parse_float=Decimal)


def number(value, label, *, allow_zero=False, whole=False):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} must be a finite number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a finite number") from None
    if not result.is_finite() or result < 0 or (result == 0 and not allow_zero):
        raise ValueError(f"{label} must be {'nonnegative' if allow_zero else 'positive'} and finite")
    if whole and result != result.to_integral_value():
        raise ValueError(f"{label} must be a whole number")
    return result


def decimal_text(value):
    return format(value, "f")


def money(value):
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), ".2f")


def load_catalog(path=DEFAULT_CATALOG):
    catalog = read_json(path)
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        raise ValueError("Expected pricing catalog schema_version 1")
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("Catalog items must be a list")
    ids = [item.get("id") for item in items if isinstance(item, dict)]
    if len(ids) != len(items) or any(not isinstance(value, str) or not value for value in ids):
        raise ValueError("Every catalog item needs a nonempty string id")
    if len(ids) != len(set(ids)):
        raise ValueError("Catalog item ids must be unique")
    return catalog


def find_items(catalog, query, limit=10):
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    terms = query.casefold().split()
    matches = []
    for item in catalog["items"]:
        haystack = " ".join(
            str(item.get(key) or "") for key in ("id", "name", "family", "kind")
        ) + " " + " ".join(str(alias) for alias in item.get("aliases", []))
        if all(term in haystack.casefold() for term in terms):
            matches.append(item)
    return {
        "matched": len(matches),
        "returned": min(limit, len(matches)),
        "items": [
            {key: item[key] for key in (
                "id", "name", "family", "kind", "rates", "published_amount",
                "source_pages", "source_status", "status", "rate_basis_authority", "rental_billing", "unresolved_fields"
            ) if key in item}
            for item in matches[:limit]
        ],
    }


def service_periods(line, catalog):
    """Use explicit visits first; never multiply visits by trailer count."""
    if "visits" in line:
        return number(line["visits"], "visits", allow_zero=True, whole=True), "explicit_visits"
    if "periods" in line:
        return number(line["periods"], "periods", allow_zero=True, whole=True), "explicit_periods"
    if "months" in line:
        months = number(line["months"], "months", whole=True)
        policy = catalog.get("policies", {}).get("service_default", {})
        frequency = number(policy.get("recommended_visits_per_month"), "recommended visits per month", whole=True)
        visits = number(months * frequency, "planned visits", whole=True)
        return visits, "recommended_visits_per_month"
    return Decimal(1), "single_visit"


def calculate_quote(catalog, request):
    if not isinstance(request, dict) or not isinstance(request.get("lines"), list) or not request["lines"]:
        raise ValueError("Quote input must contain a nonempty lines list")
    items = {item["id"]: item for item in catalog["items"]}
    results = []
    for index, line in enumerate(request["lines"], 1):
        if not isinstance(line, dict):
            raise ValueError(f"Quote line {index} must be an object")
        item = items.get(line.get("item_id"))
        result = {
            "line": index,
            "item_id": line.get("item_id"),
            "rate_key": line.get("rate_key"),
            "coverage_group": line.get("coverage_group"),
            "status": "incomplete",
            "extension": None,
            "issues": [],
            "warnings": [],
        }
        results.append(result)
        if item is None:
            result["issues"].append("Unknown catalog item_id")
            continue
        result.update({
            "name": item.get("name"),
            "source_pages": deepcopy(item.get("source_pages", [])),
            "catalog_status": item.get("source_status", item.get("status")),
            "source_status": item.get("source_status", item.get("status")),
            "unresolved_fields": deepcopy(item.get("unresolved_fields", [])),
            "includes_item_ids": deepcopy(item.get("includes_item_ids", [])),
        })
        for source_field in ("rate_basis_authority", "rental_billing", "rate_scope", "qualifications"):
            if source_field in item:
                result[source_field] = deepcopy(item[source_field])
        if "published_amount" in item:
            result["reference_published_amount"] = deepcopy(item["published_amount"])
        try:
            key = line.get("rate_key")
            if not isinstance(key, str) or not key:
                raise ValueError("rate_key is required")
            # Quantity is a count of equipment, people or service units, except
            # for per-mile pricing where it is the chargeable distance.
            quantity = number(line.get("quantity", 1), "quantity", whole=key != "per_mile")
            result["quantity"] = decimal_text(quantity)
            minimum = item.get("minimum_people", item.get("min_people"))
            if minimum is not None and quantity < number(minimum, "min_people", whole=True):
                raise ValueError(f"Minimum people requirement is {minimum}; requested quantity is {quantity}")
            rates = item.get("rates") or {}
            if key not in rates or rates[key] is None:
                raise ValueError(f"No supported rate for {key}; no period conversion or published-amount substitution was applied")
            rate = number(rates[key], "unit rate", allow_zero=True)
            if key == "per_visit":
                periods, basis = service_periods(line, catalog)
                result["visits"] = int(periods)
                result["visit_count_basis"] = basis
                if basis == "recommended_visits_per_month":
                    result["planning_months"] = decimal_text(number(line["months"], "months"))
                    result["warnings"].append("Visit count uses the standing recommendation because no explicit visit count was supplied; contract frequency takes precedence")
            else:
                if "months" in line or "visits" in line:
                    raise ValueError("months/visits may only select counts for a per_visit rate; use explicit periods for other rates")
                periods = number(line.get("periods", 1), "periods", whole=True)
                rental_billing = item.get("rental_billing") or {}
                if rental_billing.get("basis") == "monthly_minimum":
                    if key in ("event_1_3_days", "week") and periods != 1:
                        raise ValueError("Monthly-minimum rental uses one flat charge for a continuous rental up to one month; use month with explicit billed periods for longer rentals, or separate lines for distinct bookings")
                    result["warnings"].append("Flat monthly-minimum rental: one day, one week and any continuous rental up to one month have the same charge; no daily or weekly proration applies")
            result.update({
                "unit_rate": decimal_text(rate),
                "periods": decimal_text(periods),
                "extension": money(rate * quantity * periods),
                "status": "priced",
            })
        except (ValueError, InvalidOperation) as error:
            result["issues"].append(str(error))

    conflicts = []
    coverage_checks = []
    for first_index, first in enumerate(results):
        if first["item_id"] not in items or items[first["item_id"]].get("kind") != "service":
            continue
        first_coverage = {first["item_id"]} | set(first.get("includes_item_ids", []))
        for second in results[first_index + 1:]:
            if second["item_id"] not in items or items[second["item_id"]].get("kind") != "service":
                continue
            overlap = first_coverage & ({second["item_id"]} | set(second.get("includes_item_ids", [])))
            if not overlap:
                continue
            first_group = str(first.get("coverage_group") or "").strip()
            second_group = str(second.get("coverage_group") or "").strip()
            detail = {"lines": [first["line"], second["line"]], "overlapping_item_ids": sorted(overlap)}
            if first_group and first_group == second_group:
                detail["coverage_group"] = first_group
                conflicts.append(detail)
                for affected in (first, second):
                    affected["status"] = "coverage_conflict"
                    affected["extension"] = None
                    affected["issues"].append("Overlapping included coverage in the same coverage_group; remove duplicate billing or separate distinct service events")
            elif not first_group or not second_group:
                coverage_checks.append(detail)
    priced_lines = [line for line in results if line["extension"] is not None]
    subtotal = sum((Decimal(line["extension"]) for line in priced_lines), Decimal(0))
    complete = all(line["status"] == "priced" for line in results)
    return {
        "currency": catalog.get("currency", "USD"),
        "catalog_source": deepcopy(catalog.get("source")),
        "calculation_scope": "requested_lines_only",
        "priced_line_count": len(priced_lines),
        "status": "complete" if complete else "incomplete",
        "known_subtotal": money(subtotal) if priced_lines else None,
        "total": money(subtotal) if complete else None,
        "lines": results,
        "coverage_conflicts": conflicts,
        "coverage_checks": coverage_checks,
        "warnings": ["Potential included-service overlap lacks a coverage_group on one or both lines; verify scope before relying on the total"] if coverage_checks else [],
    }


def json_default(value):
    if isinstance(value, Decimal):
        return decimal_text(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("find", help="Search product names and aliases, with bounded output")
    find.add_argument("--query", required=True)
    find.add_argument("--limit", type=int, default=10)
    show = commands.add_parser("show", help="Read one complete source-backed rate record")
    show.add_argument("--id", required=True)
    quote = commands.add_parser("quote", help="Calculate requested lines; unknown rates remain incomplete")
    quote.add_argument("--input", required=True, type=Path)
    for command in (find, show, quote):
        command.add_argument("--catalog", type=Path, default=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
        if args.command == "find":
            result = find_items(catalog, args.query, args.limit)
        elif args.command == "show":
            result = next((item for item in catalog["items"] if item["id"] == args.id), None)
            if result is None:
                raise ValueError(f"Unknown catalog item id: {args.id}")
        else:
            result = calculate_quote(catalog, read_json(args.input))
        print(json.dumps(result, indent=2, ensure_ascii=False, default=json_default))
        return 0
    except (OSError, ValueError, InvalidOperation) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
