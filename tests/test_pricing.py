"""Observable pricing behavior using small independent catalog fixtures."""

from copy import deepcopy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "temporary123-proposal-writer/scripts/pricing.py"
SPEC = importlib.util.spec_from_file_location("proposal_pricing", SCRIPT)
pricing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pricing)


def catalog_fixture():
    return {
        "schema_version": 1,
        "currency": "USD",
        "policies": {"service_default": {"price_basis": "per_visit", "recommended_visits_per_month": 2, "contract_frequency_overrides": True}},
        "items": [
            {"id": "rental", "name": "Example combo", "family": "trailer", "kind": "rental", "aliases": ["three stall"], "rates": {"month": "100.10", "week": "40.00"}, "source_pages": [3]},
            {"id": "pump", "name": "Tank pumping", "kind": "service", "rates": {"per_visit": "60.05"}, "source_pages": [9], "source_status": "published", "rate_basis_authority": "approved per-visit rule"},
            {"id": "bladder", "name": "Bladder pumping including tank", "kind": "service", "rates": {"per_visit": 80}, "includes_item_ids": ["pump"], "source_pages": [9]},
            {"id": "unknown-rental", "name": "Rental with unsupported billing basis", "rates": {"event_1_3_days": None, "week": None, "month": None}, "published_amount": 200, "status": "estimate_period_unconfirmed", "unresolved_fields": ["rental_period"], "source_pages": [7, 8]},
            {"id": "camp", "name": "Camp per person", "min_people": 150, "rates": {"per_person_day": 175}, "source_pages": [15]},
        ],
    }


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.catalog = catalog_fixture()

    def quote(self, *lines):
        return pricing.calculate_quote(self.catalog, {"lines": list(lines)})

    def test_decimal_money_and_explicit_quantity_periods(self):
        result = self.quote({"item_id": "rental", "rate_key": "month", "quantity": 3, "periods": 2})
        self.assertEqual(result["total"], "600.60")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["calculation_scope"], "requested_lines_only")
        self.assertEqual(result["priced_line_count"], 1)
        self.assertEqual(result["lines"][0]["source_pages"], [3])

    def test_service_defaults_to_two_visits_per_month_without_fleet_multiplier(self):
        result = self.quote(
            {"item_id": "rental", "rate_key": "month", "quantity": 3, "periods": 4},
            {"item_id": "pump", "rate_key": "per_visit", "months": 4},
        )
        self.assertEqual(result["lines"][1]["visits"], 8)
        self.assertEqual(result["lines"][1]["extension"], "480.40")
        self.assertEqual(result["total"], "1681.60")
        self.assertTrue(result["lines"][1]["warnings"])
        self.assertEqual(result["lines"][1]["source_status"], "published")
        self.assertEqual(result["lines"][1]["rate_basis_authority"], "approved per-visit rule")

    def test_explicit_visits_override_monthly_default_and_periods(self):
        result = self.quote({"item_id": "pump", "rate_key": "per_visit", "months": 4, "periods": 8, "visits": 3, "quantity": 2})
        self.assertEqual(result["total"], "360.30")
        self.assertEqual(result["lines"][0]["visit_count_basis"], "explicit_visits")

    def test_unknown_period_retains_known_subtotal_without_using_published_amount(self):
        result = self.quote(
            {"item_id": "rental", "rate_key": "week", "quantity": 2},
            {"item_id": "unknown-rental", "rate_key": "month", "quantity": 2, "periods": 4},
        )
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["known_subtotal"], "80.00")
        self.assertIsNone(result["total"])
        self.assertIsNone(result["lines"][1]["extension"])
        self.assertEqual(result["lines"][1]["reference_published_amount"], 200)
        self.assertEqual(result["lines"][1]["unresolved_fields"], ["rental_period"])
        self.assertEqual(result["priced_line_count"], 1)

    def test_all_unpriced_rental_has_no_zero_subtotal(self):
        result = self.quote({"item_id": "unknown-rental", "rate_key": "month", "quantity": 2, "periods": 4})
        self.assertIsNone(result["known_subtotal"])
        self.assertIsNone(result["total"])
        self.assertEqual(result["priced_line_count"], 0)
        self.assertEqual(result["lines"][0]["reference_published_amount"], 200)

    def test_supported_zero_price_is_a_priced_zero_not_an_unknown(self):
        self.catalog["items"].append({"id": "included", "rates": {"per_visit": 0}, "kind": "service"})
        result = self.quote({"item_id": "included", "rate_key": "per_visit", "visits": 1})
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["known_subtotal"], "0.00")
        self.assertEqual(result["total"], "0.00")
        self.assertEqual(result["priced_line_count"], 1)

    def test_no_implicit_daily_conversion_of_week_or_month(self):
        result = self.quote({"item_id": "rental", "rate_key": "day", "periods": 7})
        self.assertIsNone(result["total"])
        self.assertIsNone(result["known_subtotal"])

    def test_fractional_discrete_rental_periods_are_not_prorated(self):
        self.catalog["items"][0]["rates"]["event_1_3_days"] = 32
        for key in ("event_1_3_days", "week", "month"):
            with self.subTest(rate_key=key):
                result = self.quote({"item_id": "rental", "rate_key": key, "periods": "0.5"})
                self.assertEqual(result["status"], "incomplete")
                self.assertIsNone(result["known_subtotal"])
                self.assertIn("whole number", result["lines"][0]["issues"][0])

    def test_fractional_equipment_service_and_people_quantities_are_rejected(self):
        for item_id, key, quantity in (("rental", "month", "0.5"), ("pump", "per_visit", "1.5"), ("camp", "per_person_day", "150.5")):
            with self.subTest(item_id=item_id):
                result = self.quote({"item_id": item_id, "rate_key": key, "quantity": quantity})
                self.assertEqual(result["status"], "incomplete")
                self.assertIsNone(result["total"])
                self.assertIn("whole number", result["lines"][0]["issues"][0])

    def test_fractional_chargeable_mileage_is_supported(self):
        self.catalog["items"].append({"id": "transport", "rates": {"per_mile": 4}, "kind": "transport"})
        result = self.quote({"item_id": "transport", "rate_key": "per_mile", "quantity": "12.5", "periods": 2})
        self.assertEqual(result["total"], "100.00")

    def test_partial_service_month_needs_explicit_visit_count(self):
        inferred = self.quote({"item_id": "pump", "rate_key": "per_visit", "months": "0.5"})
        explicit = self.quote({"item_id": "pump", "rate_key": "per_visit", "months": "0.5", "visits": 1})
        self.assertIsNone(inferred["total"])
        self.assertIn("whole number", inferred["lines"][0]["issues"][0])
        self.assertEqual(explicit["total"], "60.05")

    def test_explicit_eight_hour_block_does_not_allow_fractional_proration(self):
        self.catalog["items"].append({"id": "security", "rates": {"per_8_hours": 400}, "kind": "staffing"})
        result = self.quote({"item_id": "security", "rate_key": "per_8_hours", "periods": "0.5"})
        self.assertIsNone(result["total"])
        self.assertIn("whole number", result["lines"][0]["issues"][0])

    def test_same_coverage_group_prevents_double_billing(self):
        result = self.quote(
            {"item_id": "rental", "rate_key": "month"},
            {"item_id": "bladder", "rate_key": "per_visit", "coverage_group": "visit-1"},
            {"item_id": "pump", "rate_key": "per_visit", "coverage_group": "visit-1"},
        )
        self.assertEqual(result["known_subtotal"], "100.10")
        self.assertIsNone(result["total"])
        self.assertEqual(result["coverage_conflicts"][0]["overlapping_item_ids"], ["pump"])
        self.assertEqual([line["status"] for line in result["lines"]], ["priced", "coverage_conflict", "coverage_conflict"])

    def test_distinct_service_events_do_not_overlap(self):
        result = self.quote(
            {"item_id": "bladder", "rate_key": "per_visit", "coverage_group": "visit-1"},
            {"item_id": "pump", "rate_key": "per_visit", "coverage_group": "visit-2"},
        )
        self.assertEqual(result["total"], "140.05")
        self.assertEqual(result["coverage_conflicts"], [])

    def test_missing_coverage_group_flags_check_without_silently_dropping_cost(self):
        result = self.quote({"item_id": "bladder", "rate_key": "per_visit"}, {"item_id": "pump", "rate_key": "per_visit"})
        self.assertEqual(result["known_subtotal"], "140.05")
        self.assertTrue(result["coverage_checks"])
        self.assertTrue(result["warnings"])

    def test_split_rental_period_lines_are_not_included_service_conflicts(self):
        result = self.quote(
            {"item_id": "rental", "rate_key": "week", "coverage_group": "project"},
            {"item_id": "rental", "rate_key": "month", "coverage_group": "project"},
        )
        self.assertEqual(result["total"], "140.10")
        self.assertEqual(result["coverage_conflicts"], [])
        self.assertEqual(result["coverage_checks"], [])
        self.assertEqual(result["warnings"], [])

    def test_man_camp_minimum_rejects_under_150_people(self):
        rejected = self.quote({"item_id": "camp", "rate_key": "per_person_day", "quantity": 149, "periods": 2})
        accepted = self.quote({"item_id": "camp", "rate_key": "per_person_day", "quantity": 150, "periods": 2})
        self.assertIsNone(rejected["total"])
        self.assertIn("Minimum people", rejected["lines"][0]["issues"][0])
        self.assertEqual(accepted["total"], "52500.00")

    def test_normalized_minimum_people_field_is_enforced(self):
        camp = next(item for item in self.catalog["items"] if item["id"] == "camp")
        camp["minimum_people"] = camp.pop("min_people")
        result = self.quote({"item_id": "camp", "rate_key": "per_person_day", "quantity": 149})
        self.assertIsNone(result["total"])

    def test_invalid_numbers_never_become_charges(self):
        for invalid in (-1, True, "NaN", "Infinity"):
            with self.subTest(value=invalid):
                result = self.quote({"item_id": "rental", "rate_key": "month", "quantity": invalid})
                self.assertIsNone(result["total"])
                self.assertIsNone(result["known_subtotal"])

    def test_input_and_catalog_remain_unchanged(self):
        request = {"lines": [{"item_id": "pump", "rate_key": "per_visit", "months": 4}]}
        before = deepcopy((self.catalog, request))
        pricing.calculate_quote(self.catalog, request)
        self.assertEqual((self.catalog, request), before)


class MonthlyMinimumCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = pricing.load_catalog()
        cls.items = {item["id"]: item for item in cls.catalog["items"]}

    def quote(self, *lines):
        return pricing.calculate_quote(self.catalog, {"lines": list(lines)})

    def test_all_eight_portable_offers_use_approved_equal_short_and_monthly_prices(self):
        expected = {
            "portable-standard": 200,
            "portable-standard-with-service": 200,
            "portable-deluxe-without-service": 350,
            "portable-deluxe-with-service": 450,
            "portable-ada-without-service": 500,
            "portable-ada-with-service": 600,
            "handwash-double-without-service": 90,
            "handwash-double-with-service": 140,
        }
        for item_id, amount in expected.items():
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                self.assertEqual(item["rates"], {"event_1_3_days": amount, "week": amount, "month": amount})
                self.assertEqual(item["rental_billing"]["basis"], "monthly_minimum")
                self.assertFalse(item["rental_billing"]["source_duration_stated"])
                self.assertNotIn("rental_billing_period", item["unresolved_fields"])
                totals = []
                for key in ("event_1_3_days", "week", "month"):
                    result = self.quote({"item_id": item_id, "rate_key": key, "quantity": 1})
                    totals.append(result["total"])
                    self.assertTrue(result["lines"][0]["warnings"])
                    self.assertEqual(result["lines"][0]["rental_billing"], item["rental_billing"])
                self.assertEqual(totals, [f"{amount}.00"] * 3)

    def test_monthly_minimum_rejects_repeated_weeks_or_events_for_one_booking(self):
        for key in ("event_1_3_days", "week"):
            with self.subTest(rate_key=key):
                result = self.quote({"item_id": "portable-standard", "rate_key": key, "periods": 2})
                self.assertIsNone(result["total"])
                self.assertIsNone(result["known_subtotal"])
                self.assertIn("one flat charge", result["lines"][0]["issues"][0])

    def test_four_explicit_monthly_periods_use_four_monthly_charges(self):
        result = self.quote({"item_id": "portable-standard", "rate_key": "month", "quantity": 2, "periods": 4})
        self.assertEqual(result["total"], "1600.00")
        self.assertEqual(result["lines"][0]["periods"], "4")

    def test_distinct_short_bookings_may_use_separate_lines(self):
        result = self.quote(
            {"item_id": "portable-standard", "rate_key": "week", "coverage_group": "booking-1"},
            {"item_id": "portable-standard", "rate_key": "week", "coverage_group": "booking-2"},
        )
        self.assertEqual(result["total"], "400.00")

    def test_standalone_visits_and_explicit_trailer_periods_are_preserved(self):
        single = self.quote({"item_id": "pump-restroom-300", "rate_key": "per_visit", "visits": 1})
        recommended = self.quote({"item_id": "pump-restroom-300", "rate_key": "per_visit", "months": 1})
        self.assertEqual(single["total"], "600.00")
        self.assertEqual(recommended["total"], "1200.00")
        self.assertEqual(recommended["lines"][0]["visits"], 2)
        for key, total in (("event_1_3_days", "2796.00"), ("week", "3495.00"), ("month", "3995.00")):
            with self.subTest(rate_key=key):
                result = self.quote({"item_id": "combo-13ft-3-stall", "rate_key": key})
                self.assertEqual(result["total"], total)
                self.assertNotIn("rental_billing", result["lines"][0])
        repeated_week = self.quote({"item_id": "combo-13ft-3-stall", "rate_key": "week", "periods": 2})
        self.assertEqual(repeated_week["total"], "6990.00")

    def test_one_day_selection_uses_flat_event_charge_without_a_daily_rate(self):
        event = self.quote({"item_id": "portable-standard", "rate_key": "event_1_3_days"})
        unsupported = self.quote({"item_id": "portable-standard", "rate_key": "day", "periods": 7})
        self.assertEqual(event["total"], "200.00")
        self.assertIsNone(unsupported["total"])

    def test_find_exposes_monthly_minimum_authority(self):
        result = pricing.find_items(self.catalog, "portable-standard-with-service", 1)
        self.assertEqual(result["items"][0]["rental_billing"], self.items["portable-standard-with-service"]["rental_billing"])


class CliTests(unittest.TestCase):
    def test_find_show_and_quote_with_fixture_files(self):
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / "catalog.json"
            request = Path(temp) / "quote.json"
            catalog.write_text(json.dumps(catalog_fixture()), encoding="utf-8")
            request.write_text(json.dumps({"lines": [{"item_id": "pump", "rate_key": "per_visit", "months": 2}]}), encoding="utf-8")
            def run(*args):
                result = subprocess.run([sys.executable, str(SCRIPT), *args, "--catalog", str(catalog)], capture_output=True, text=True, check=True)
                return json.loads(result.stdout)
            self.assertEqual(run("find", "--query", "three stall", "--limit", "1")["items"][0]["id"], "rental")
            self.assertEqual(run("show", "--id", "unknown-rental")["published_amount"], 200)
            self.assertEqual(run("quote", "--input", str(request))["total"], "240.20")

    def test_find_limit_is_enforced(self):
        result = pricing.find_items(catalog_fixture(), "", 2)
        self.assertEqual(result["matched"], 5)
        self.assertEqual(result["returned"], 2)
        with self.assertRaises(ValueError):
            pricing.find_items(catalog_fixture(), "", 101)


if __name__ == "__main__":
    unittest.main()
