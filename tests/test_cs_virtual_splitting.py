import pytest
import json
import csv
import uuid
from datetime import datetime, timedelta
from contextlib import contextmanager
from unittest.mock import patch
from src.core import FinanceManager


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def manager(tmp_path):
    """Creates an isolated FinanceManager with clean test data."""
    balances = {
        "mandatory": 1000.0,
        "non_mandatory": 600.0,
        "investments": 200.0,
        "dreams": 200.0,
    }
    (tmp_path / "balances.json").write_text(json.dumps(balances))

    categories = {
        "taxi": "non_mandatory",
        "rent": "mandatory",
        "food": "non_mandatory",
        "dreams": "dreams",
        "investments": "investments",
    }
    (tmp_path / "categories.json").write_text(json.dumps(categories))
    (tmp_path / "history.csv").write_text("")

    return FinanceManager(str(tmp_path))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextmanager
def freeze_datetime(frozen_dt):
    """
    Patches datetime.datetime at the module level so that datetime.now()
    inside get_monthly_stats() returns the frozen value.
    """
    RealDatetime = datetime

    class FakeDatetime(RealDatetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_dt

    with patch("datetime.datetime", FakeDatetime):
        yield


def _write_row(manager, t_type, cat, amt_str, env, details="OK", date_str=None):
    """Append a synthetic CSV row to history."""
    t_id = str(uuid.uuid4())[:8]
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([t_id, date_str, t_type, cat, amt_str, env, details])
    return t_id


def _last_month_date():
    first_of_month = datetime.now().replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    return last_month.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# 1. Empty history
# ---------------------------------------------------------------------------

class TestEmptyHistory:
    def test_all_four_envelopes_returned(self, manager):
        result = manager.get_monthly_stats()
        assert set(result.keys()) == {"mandatory", "non_mandatory", "investments", "dreams"}

    def test_all_totals_are_zero(self, manager):
        result = manager.get_monthly_stats()
        for env in result:
            assert abs(result[env]["total"] - 0.0) < 0.01

    def test_all_cats_dicts_are_empty(self, manager):
        result = manager.get_monthly_stats()
        for env in result:
            assert result[env]["cats"] == {}


# ---------------------------------------------------------------------------
# 2. Normal EXPENSE row, DETAILS="OK"
# ---------------------------------------------------------------------------

class TestNormalExpenseOk:
    def test_full_amount_goes_to_home_envelope(self, manager):
        _write_row(manager, "EXPENSE", "food", "300.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["total"] - 300.0) < 0.01

    def test_category_recorded_in_home_envelope_cats(self, manager):
        _write_row(manager, "EXPENSE", "food", "300.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert "food" in result["non_mandatory"]["cats"]
        assert abs(result["non_mandatory"]["cats"]["food"] - 300.0) < 0.01

    def test_other_envelopes_untouched_on_ok_expense(self, manager):
        _write_row(manager, "EXPENSE", "food", "300.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["mandatory"]["total"] - 0.0) < 0.01
        assert abs(result["investments"]["total"] - 0.0) < 0.01
        assert abs(result["dreams"]["total"] - 0.0) < 0.01

    def test_mandatory_expense_ok_goes_to_mandatory(self, manager):
        _write_row(manager, "EXPENSE", "rent", "500.00 UAH", "mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["mandatory"]["total"] - 500.0) < 0.01
        assert "rent" in result["mandatory"]["cats"]

    def test_multiple_ok_expenses_accumulate_in_cats(self, manager):
        _write_row(manager, "EXPENSE", "food", "100.00 UAH", "non_mandatory", "OK")
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["cats"]["food"] - 300.0) < 0.01
        assert abs(result["non_mandatory"]["total"] - 300.0) < 0.01


# ---------------------------------------------------------------------------
# 3. EXPENSE row with breach DETAILS
# ---------------------------------------------------------------------------

class TestBreachExpense:
    def test_home_envelope_gets_amount_minus_borrowed(self, manager):
        # total = 700, borrowed from mandatory = 200 → home (non_mandatory) gets 500
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "food", "700.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["cats"]["food"] - 500.0) < 0.01

    def test_home_envelope_total_is_home_contribution(self, manager):
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "food", "700.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["total"] - 500.0) < 0.01

    def test_breach_envelope_gets_budget_breach_entry(self, manager):
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "food", "700.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert "Budget Breach" in result["mandatory"]["cats"]
        assert abs(result["mandatory"]["cats"]["Budget Breach"] - 200.0) < 0.01

    def test_breach_envelope_total_equals_breach_amount(self, manager):
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "food", "700.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert abs(result["mandatory"]["total"] - 200.0) < 0.01

    def test_breach_across_two_envelopes(self, manager):
        # total = 1000, borrowed: mandatory=300, investments=100 → home gets 600
        details = json.dumps({"mandatory": 300.0, "investments": 100.0})
        _write_row(manager, "EXPENSE", "food", "1000.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["cats"]["food"] - 600.0) < 0.01
        assert abs(result["mandatory"]["cats"]["Budget Breach"] - 300.0) < 0.01
        assert abs(result["investments"]["cats"]["Budget Breach"] - 100.0) < 0.01


# ---------------------------------------------------------------------------
# 4. home_contribution guard — borrowed_total > amount → home_contribution = 0.0
# ---------------------------------------------------------------------------

class TestHomeContributionGuard:
    def test_malformed_breach_where_borrowed_exceeds_amount(self, manager):
        # amount = 100, borrowed = 200 → home_contribution must be clamped to 0.0
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "food", "100.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        # home_contribution = max(100 - 200, 0.0) = 0.0
        assert abs(result["non_mandatory"]["cats"].get("food", 0.0) - 0.0) < 0.01

    def test_home_total_not_negative_on_malformed_breach(self, manager):
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "food", "100.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert result["non_mandatory"]["total"] >= 0.0


# ---------------------------------------------------------------------------
# 5. Multiple breaches accumulate in "Budget Breach"
# ---------------------------------------------------------------------------

class TestMultipleBreachesAccumulate:
    def test_budget_breach_sums_across_two_breach_rows(self, manager):
        details1 = json.dumps({"mandatory": 100.0})
        details2 = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "food", "500.00 UAH", "non_mandatory", details1)
        _write_row(manager, "EXPENSE", "taxi", "600.00 UAH", "non_mandatory", details2)
        result = manager.get_monthly_stats()
        assert abs(result["mandatory"]["cats"]["Budget Breach"] - 250.0) < 0.01

    def test_mandatory_total_sums_both_breach_amounts(self, manager):
        details1 = json.dumps({"mandatory": 100.0})
        details2 = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "food", "500.00 UAH", "non_mandatory", details1)
        _write_row(manager, "EXPENSE", "taxi", "600.00 UAH", "non_mandatory", details2)
        result = manager.get_monthly_stats()
        assert abs(result["mandatory"]["total"] - 250.0) < 0.01

    def test_home_contributions_also_accumulate_correctly(self, manager):
        # food: 500 - 100 = 400 in non_mandatory; taxi: 600 - 150 = 450 in non_mandatory
        details1 = json.dumps({"mandatory": 100.0})
        details2 = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "food", "500.00 UAH", "non_mandatory", details1)
        _write_row(manager, "EXPENSE", "taxi", "600.00 UAH", "non_mandatory", details2)
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["cats"]["food"] - 400.0) < 0.01
        assert abs(result["non_mandatory"]["cats"]["taxi"] - 450.0) < 0.01


# ---------------------------------------------------------------------------
# 6. FX row parsing — "1500.00 USD (41250.00 UAH)"
# ---------------------------------------------------------------------------

class TestFxRowParsing:
    def test_fx_expense_extracts_uah_from_parens(self, manager):
        _write_row(manager, "EXPENSE", "food", "1500.00 USD (41250.00 UAH)", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["total"] - 41250.0) < 0.01

    def test_fx_expense_category_gets_uah_amount(self, manager):
        _write_row(manager, "EXPENSE", "food", "1500.00 USD (41250.00 UAH)", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["cats"]["food"] - 41250.0) < 0.01

    def test_fx_expense_with_breach_uses_uah_for_split(self, manager):
        # UAH total = 10000, borrowed mandatory = 3000 → home gets 7000
        details = json.dumps({"mandatory": 3000.0})
        _write_row(manager, "EXPENSE", "food", "250.00 USD (10000.00 UAH)", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["cats"]["food"] - 7000.0) < 0.01
        assert abs(result["mandatory"]["cats"]["Budget Breach"] - 3000.0) < 0.01


# ---------------------------------------------------------------------------
# 7. Malformed DETAILS JSON — fallback: full amount to home envelope
# ---------------------------------------------------------------------------

class TestMalformedDetailsJson:
    def test_malformed_json_falls_back_to_ok_behaviour(self, manager):
        _write_row(manager, "EXPENSE", "food", "250.00 UAH", "non_mandatory", "{not: valid json")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["cats"]["food"] - 250.0) < 0.01

    def test_malformed_json_full_amount_in_home_total(self, manager):
        _write_row(manager, "EXPENSE", "food", "250.00 UAH", "non_mandatory", "{not: valid json")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["total"] - 250.0) < 0.01

    def test_malformed_json_no_budget_breach_in_other_envelopes(self, manager):
        _write_row(manager, "EXPENSE", "food", "250.00 UAH", "non_mandatory", "{not: valid json")
        result = manager.get_monthly_stats()
        assert "Budget Breach" not in result["mandatory"]["cats"]


# ---------------------------------------------------------------------------
# 8. Legacy row < 7 columns — handled without crash, treated as "OK"
# ---------------------------------------------------------------------------

class TestLegacyRows:
    def test_six_column_row_does_not_crash(self, manager):
        t_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([t_id, date_str, "EXPENSE", "food", "150.00 UAH", "non_mandatory"])
        result = manager.get_monthly_stats()
        assert result is not None

    def test_six_column_row_treated_as_ok(self, manager):
        t_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([t_id, date_str, "EXPENSE", "food", "150.00 UAH", "non_mandatory"])
        result = manager.get_monthly_stats()
        # Should behave as "OK": full amount goes to home envelope
        assert abs(result["non_mandatory"]["cats"]["food"] - 150.0) < 0.01

    def test_empty_rows_skipped_without_crash(self, manager):
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            f.write("\n\n")
        result = manager.get_monthly_stats()
        assert result is not None

    def test_five_column_row_skipped(self, manager):
        t_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([t_id, date_str, "EXPENSE", "food", "150.00 UAH"])
        result = manager.get_monthly_stats()
        # Row with < 6 columns is skipped entirely
        assert abs(result["non_mandatory"]["total"] - 0.0) < 0.01


# ---------------------------------------------------------------------------
# 9. Non-EXPENSE rows (INCOME, SYNC) excluded from stats
# ---------------------------------------------------------------------------

class TestNonExpenseRowsExcluded:
    def test_income_row_excluded_from_stats(self, manager):
        _write_row(manager, "INCOME", "Total", "10000.00 UAH", "Distributed", "OK")
        result = manager.get_monthly_stats()
        for env in result:
            assert abs(result[env]["total"] - 0.0) < 0.01

    def test_sync_row_excluded_from_stats(self, manager):
        _write_row(manager, "SYNC", "Adjustment", "500.00 UAH", "Balance Sync", "OK")
        result = manager.get_monthly_stats()
        for env in result:
            assert abs(result[env]["total"] - 0.0) < 0.01

    def test_income_and_expense_combined_only_expense_counted(self, manager):
        _write_row(manager, "INCOME", "Total", "10000.00 UAH", "Distributed", "OK")
        _write_row(manager, "EXPENSE", "food", "300.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["total"] - 300.0) < 0.01


# ---------------------------------------------------------------------------
# 10. Previous month rows excluded
# ---------------------------------------------------------------------------

class TestPreviousMonthExcluded:
    def test_last_month_expense_not_counted(self, manager):
        last_month = _last_month_date()
        _write_row(manager, "EXPENSE", "food", "400.00 UAH", "non_mandatory", "OK", last_month)
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["total"] - 0.0) < 0.01

    def test_last_month_breach_not_reflected(self, manager):
        last_month = _last_month_date()
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "food", "600.00 UAH", "non_mandatory", details, last_month)
        result = manager.get_monthly_stats()
        assert "Budget Breach" not in result["mandatory"]["cats"]
        assert abs(result["mandatory"]["total"] - 0.0) < 0.01

    def test_current_month_row_counted_last_month_not(self, manager):
        last_month = _last_month_date()
        _write_row(manager, "EXPENSE", "food", "999.00 UAH", "non_mandatory", "OK", last_month)
        _write_row(manager, "EXPENSE", "food", "100.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["non_mandatory"]["total"] - 100.0) < 0.01


# ---------------------------------------------------------------------------
# 11. investments and dreams envelopes appear only when they have data
# ---------------------------------------------------------------------------

class TestInvestmentsDreamsOnlyWhenTouched:
    def test_investments_total_zero_when_no_breach_touched_it(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["investments"]["total"] - 0.0) < 0.01
        assert result["investments"]["cats"] == {}

    def test_dreams_total_zero_when_no_breach_touched_it(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "OK")
        result = manager.get_monthly_stats()
        assert abs(result["dreams"]["total"] - 0.0) < 0.01
        assert result["dreams"]["cats"] == {}

    def test_investments_populated_when_breach_borrows_from_it(self, manager):
        details = json.dumps({"investments": 50.0})
        _write_row(manager, "EXPENSE", "food", "650.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert abs(result["investments"]["cats"]["Budget Breach"] - 50.0) < 0.01
        assert abs(result["investments"]["total"] - 50.0) < 0.01

    def test_dreams_populated_when_breach_borrows_from_it(self, manager):
        details = json.dumps({"dreams": 75.0})
        _write_row(manager, "EXPENSE", "food", "675.00 UAH", "non_mandatory", details)
        result = manager.get_monthly_stats()
        assert abs(result["dreams"]["cats"]["Budget Breach"] - 75.0) < 0.01
        assert abs(result["dreams"]["total"] - 75.0) < 0.01


# ---------------------------------------------------------------------------
# 12. "Budget Breach" key must NOT appear in categories.json
# ---------------------------------------------------------------------------

class TestCategoriesJsonUnmodified:
    def test_budget_breach_not_written_to_categories_json(self, manager):
        details = json.dumps({"mandatory": 100.0})
        _write_row(manager, "EXPENSE", "food", "500.00 UAH", "non_mandatory", details)
        manager.get_monthly_stats()

        with open(manager.categories_path, "r", encoding="utf-8") as f:
            categories = json.load(f)

        assert "Budget Breach" not in categories

    def test_categories_json_unchanged_after_stats_call(self, manager):
        with open(manager.categories_path, "r", encoding="utf-8") as f:
            original = json.load(f)

        details = json.dumps({"mandatory": 100.0})
        _write_row(manager, "EXPENSE", "food", "500.00 UAH", "non_mandatory", details)
        manager.get_monthly_stats()

        with open(manager.categories_path, "r", encoding="utf-8") as f:
            after = json.load(f)

        assert original == after
