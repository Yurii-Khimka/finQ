import pytest
import json
import csv
import uuid
from calendar import monthrange
from contextlib import contextmanager
from datetime import datetime, timedelta
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
    Patches datetime.datetime in the datetime module so that any
    `from datetime import datetime` inside the code under test will
    pick up FakeDatetime.now() = frozen_dt while keeping the
    constructor and all other methods intact.
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
# 1. Empty history this month
# ---------------------------------------------------------------------------

class TestEmptyHistory:
    def test_all_zeros_on_empty_history(self, manager):
        result = manager.get_audit_data()
        assert result["breach_count"] == 0
        assert abs(result["breach_total_uah"] - 0.0) < 0.01
        assert abs(result["total_spent_uah"] - 0.0) < 0.01

    def test_health_signal_healthy_on_empty_history(self, manager):
        result = manager.get_audit_data()
        assert result["health_signal"] == "healthy"

    def test_days_to_zero_is_inf_on_empty_history(self, manager):
        result = manager.get_audit_data()
        assert result["days_to_zero"] == float("inf")

    def test_top_breaches_empty_on_empty_history(self, manager):
        result = manager.get_audit_data()
        assert result["top_breaches"] == []

    def test_breach_by_envelope_all_zero_on_empty_history(self, manager):
        result = manager.get_audit_data()
        for env_val in result["breach_by_envelope"].values():
            assert abs(env_val - 0.0) < 0.01


# ---------------------------------------------------------------------------
# 2. burn_rate_daily == 0 → days_to_zero = inf, health = healthy
# ---------------------------------------------------------------------------

class TestZeroBurnRate:
    def test_days_to_zero_inf_when_no_expenses(self, manager):
        # Write an INCOME row this month — no EXPENSE rows
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed")
        result = manager.get_audit_data()
        assert result["days_to_zero"] == float("inf")

    def test_health_signal_healthy_when_burn_rate_zero(self, manager):
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed")
        result = manager.get_audit_data()
        assert result["health_signal"] == "healthy"


# ---------------------------------------------------------------------------
# 3. Normal expenses, no breaches
# ---------------------------------------------------------------------------

class TestNormalExpensesNoBreaches:
    def test_breach_count_zero_on_ok_details(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "OK")
        _write_row(manager, "EXPENSE", "rent", "500.00 UAH", "mandatory", "OK")
        result = manager.get_audit_data()
        assert result["breach_count"] == 0

    def test_breach_total_zero_on_ok_details(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "OK")
        result = manager.get_audit_data()
        assert abs(result["breach_total_uah"] - 0.0) < 0.01

    def test_top_breaches_empty_on_no_breaches(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "OK")
        result = manager.get_audit_data()
        assert result["top_breaches"] == []

    def test_total_spent_accumulates_ok_expenses(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "OK")
        _write_row(manager, "EXPENSE", "rent", "300.00 UAH", "mandatory", "OK")
        result = manager.get_audit_data()
        assert abs(result["total_spent_uah"] - 500.0) < 0.01


# ---------------------------------------------------------------------------
# 4. Single breach transaction
# ---------------------------------------------------------------------------

class TestSingleBreach:
    def test_breach_count_is_one(self, manager):
        details = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "taxi", "750.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert result["breach_count"] == 1

    def test_breach_total_uah_matches_details_amount(self, manager):
        details = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "taxi", "750.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert abs(result["breach_total_uah"] - 150.0) < 0.01

    def test_breach_by_envelope_mandatory_populated(self, manager):
        details = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "taxi", "750.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert abs(result["breach_by_envelope"]["mandatory"] - 150.0) < 0.01

    def test_breach_by_envelope_other_keys_still_zero(self, manager):
        details = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "taxi", "750.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert abs(result["breach_by_envelope"]["non_mandatory"] - 0.0) < 0.01
        assert abs(result["breach_by_envelope"]["investments"] - 0.0) < 0.01
        assert abs(result["breach_by_envelope"]["dreams"] - 0.0) < 0.01

    def test_top_breaches_has_one_entry(self, manager):
        details = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "taxi", "750.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert len(result["top_breaches"]) == 1

    def test_top_breach_entry_fields(self, manager):
        details = json.dumps({"mandatory": 150.0})
        _write_row(manager, "EXPENSE", "taxi", "750.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        entry = result["top_breaches"][0]
        assert entry["category"] == "taxi"
        assert abs(entry["breach"] - 150.0) < 0.01
        assert abs(entry["amount"] - 750.0) < 0.01


# ---------------------------------------------------------------------------
# 5. FX expense row parsing — "1500.00 USD (41250.00 UAH)"
# ---------------------------------------------------------------------------

class TestFxRowParsing:
    def test_fx_income_row_uses_uah_value_from_parens(self, manager):
        """INCOME rows with FX format should not affect EXPENSE aggregates."""
        _write_row(manager, "INCOME", "Total", "1500.00 USD (41250.00 UAH)", "Distributed", "OK")
        result = manager.get_audit_data()
        # INCOME rows are not counted in total_spent_uah
        assert abs(result["total_spent_uah"] - 0.0) < 0.01

    def test_fx_expense_row_parses_uah_correctly(self, manager):
        """EXPENSE row with FX format: UAH amount must be extracted from parentheses."""
        _write_row(manager, "EXPENSE", "taxi", "1500.00 USD (41250.00 UAH)", "non_mandatory", "OK")
        result = manager.get_audit_data()
        assert abs(result["total_spent_uah"] - 41250.0) < 0.01

    def test_fx_expense_breach_row_parses_uah_for_amount_field(self, manager):
        """Breach entry 'amount' field must also use the UAH value from parentheses."""
        details = json.dumps({"mandatory": 5000.0})
        _write_row(manager, "EXPENSE", "taxi", "200.00 USD (8200.00 UAH)", "non_mandatory", details)
        result = manager.get_audit_data()
        entry = result["top_breaches"][0]
        assert abs(entry["amount"] - 8200.0) < 0.01


# ---------------------------------------------------------------------------
# 6. Malformed DETAILS JSON — treated as "OK", not counted as breach
# ---------------------------------------------------------------------------

class TestMalformedDetails:
    def test_malformed_json_not_counted_as_breach(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "{not: valid json")
        result = manager.get_audit_data()
        assert result["breach_count"] == 0

    def test_malformed_json_does_not_add_to_breach_total(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "{not: valid json")
        result = manager.get_audit_data()
        assert abs(result["breach_total_uah"] - 0.0) < 0.01

    def test_malformed_json_expense_still_counted_in_total_spent(self, manager):
        _write_row(manager, "EXPENSE", "food", "200.00 UAH", "non_mandatory", "{not: valid json")
        result = manager.get_audit_data()
        assert abs(result["total_spent_uah"] - 200.0) < 0.01


# ---------------------------------------------------------------------------
# 7. Legacy row with < 7 columns — handled without crash
# ---------------------------------------------------------------------------

class TestLegacyRows:
    def test_six_column_legacy_row_does_not_crash(self, manager):
        t_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([t_id, date_str, "EXPENSE", "food", "150.00 UAH", "non_mandatory"])
        # Should not raise
        result = manager.get_audit_data()
        assert result is not None

    def test_six_column_legacy_row_treated_as_ok(self, manager):
        t_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([t_id, date_str, "EXPENSE", "food", "150.00 UAH", "non_mandatory"])
        result = manager.get_audit_data()
        assert result["breach_count"] == 0

    def test_empty_rows_skipped_without_crash(self, manager):
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            f.write("\n\n")
        result = manager.get_audit_data()
        assert result is not None


# ---------------------------------------------------------------------------
# 8. breach_count guard — DETAILS with only invalid envelope keys
# ---------------------------------------------------------------------------

class TestBreachCountGuard:
    def test_invalid_envelope_keys_only_not_counted_as_breach(self, manager):
        """DETAILS with only unrecognized keys (e.g. metadata) → row_breach_total stays 0."""
        details = json.dumps({"original": 10.0, "rate": 40.0})
        _write_row(manager, "EXPENSE", "taxi", "400.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert result["breach_count"] == 0

    def test_invalid_envelope_keys_do_not_add_to_breach_total(self, manager):
        details = json.dumps({"original": 10.0, "rate": 40.0})
        _write_row(manager, "EXPENSE", "taxi", "400.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert abs(result["breach_total_uah"] - 0.0) < 0.01

    def test_mixed_valid_and_invalid_keys_only_counts_valid(self, manager):
        """{"mandatory": 50.0, "rate": 40.0} → only mandatory 50.0 counted as breach."""
        details = json.dumps({"mandatory": 50.0, "rate": 40.0})
        _write_row(manager, "EXPENSE", "taxi", "650.00 UAH", "non_mandatory", details)
        result = manager.get_audit_data()
        assert result["breach_count"] == 1
        assert abs(result["breach_total_uah"] - 50.0) < 0.01


# ---------------------------------------------------------------------------
# 9. December rollover — days_in_month computed correctly
# ---------------------------------------------------------------------------

class TestDecemberRollover:
    def test_december_days_remaining_is_correct(self, manager):
        """December 10: days_remaining should be 31 - 10 = 21."""
        dec_date = datetime(2026, 12, 10, 12, 0, 0)
        with freeze_datetime(dec_date):
            result = manager.get_audit_data()
        assert result["days_remaining"] == 21

    def test_december_does_not_crash(self, manager):
        """Ensure the datetime(year+1, 1, 1) branch runs without error."""
        dec_date = datetime(2026, 12, 15, 10, 0, 0)
        date_str = dec_date.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "food", "100.00 UAH", "non_mandatory", "OK", date_str)
        with freeze_datetime(dec_date):
            result = manager.get_audit_data()
        assert result is not None
        assert abs(result["total_spent_uah"] - 100.0) < 0.01


# ---------------------------------------------------------------------------
# 10. days_remaining = 0 (last day of month) → safe_daily_limit = 0.0
# ---------------------------------------------------------------------------

class TestLastDayOfMonth:
    def test_safe_daily_limit_zero_on_last_day(self, manager):
        now = datetime.now()
        year, month = now.year, now.month
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 12, 0, 0)

        with freeze_datetime(last_day):
            result = manager.get_audit_data()

        assert abs(result["safe_daily_limit"] - 0.0) < 0.01

    def test_days_remaining_zero_on_last_day(self, manager):
        now = datetime.now()
        year, month = now.year, now.month
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 12, 0, 0)

        with freeze_datetime(last_day):
            result = manager.get_audit_data()

        assert result["days_remaining"] == 0


# ---------------------------------------------------------------------------
# 11. top_breaches capped at 5
# ---------------------------------------------------------------------------

class TestTopBreachesCap:
    def test_six_breach_rows_returns_only_top_5(self, manager):
        for i in range(6):
            amount = 100.0 + i * 10  # unique breach amounts
            details = json.dumps({"mandatory": float(amount)})
            _write_row(manager, "EXPENSE", "taxi", f"{amount + 50:.2f} UAH", "non_mandatory", details)

        result = manager.get_audit_data()
        assert len(result["top_breaches"]) == 5

    def test_top_5_are_highest_breach_amounts(self, manager):
        """The 5 returned should be the 5 largest breach amounts."""
        amounts = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        for amt in amounts:
            details = json.dumps({"mandatory": amt})
            _write_row(manager, "EXPENSE", "taxi", f"{amt + 50:.2f} UAH", "non_mandatory", details)

        result = manager.get_audit_data()
        returned_breaches = [entry["breach"] for entry in result["top_breaches"]]
        assert min(returned_breaches) >= 20.0  # 10.0 (smallest) must be excluded


# ---------------------------------------------------------------------------
# 12. health_signal = "warning"
# ---------------------------------------------------------------------------

class TestHealthWarning:
    def test_health_signal_warning_when_days_to_zero_between_half_and_full(self, manager):
        """
        Construct a scenario where days_to_zero >= days_remaining * 0.5
        but days_to_zero < days_remaining.

        Freeze to April 10, 2026:
          days_elapsed = 10, days_remaining = 30 - 10 = 20
          spendable = mandatory(1000) + non_mandatory(600) = 1600
          Target days_to_zero = 15 → in [10, 20) → "warning"
          burn_rate_daily = 1600 / 15 ≈ 106.667
          total_spent needed = burn_rate * days_elapsed = 106.667 * 10 = 1066.67
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "food", "1066.67 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_audit_data()

        assert result["health_signal"] == "warning"


# ---------------------------------------------------------------------------
# 13. health_signal = "critical"
# ---------------------------------------------------------------------------

class TestHealthCritical:
    def test_health_signal_critical_when_days_to_zero_below_half_remaining(self, manager):
        """
        days_to_zero < days_remaining * 0.5 → critical.

        Freeze to April 10, 2026:
          days_elapsed = 10, days_remaining = 20
          spendable = 1600
          Target days_to_zero = 5 (< 10 = 20 * 0.5) → "critical"
          burn_rate_daily = 1600 / 5 = 320
          total_spent = 320 * 10 = 3200
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "food", "3200.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_audit_data()

        assert result["health_signal"] == "critical"


# ---------------------------------------------------------------------------
# 14. Previous month rows are excluded
# ---------------------------------------------------------------------------

class TestMonthFiltering:
    def test_last_month_expense_not_counted(self, manager):
        last_month_date = _last_month_date()
        _write_row(manager, "EXPENSE", "food", "500.00 UAH", "non_mandatory", "OK", last_month_date)
        result = manager.get_audit_data()
        assert abs(result["total_spent_uah"] - 0.0) < 0.01

    def test_last_month_breach_not_counted(self, manager):
        last_month_date = _last_month_date()
        details = json.dumps({"mandatory": 200.0})
        _write_row(manager, "EXPENSE", "taxi", "800.00 UAH", "non_mandatory", details, last_month_date)
        result = manager.get_audit_data()
        assert result["breach_count"] == 0
