import pytest
import json
import csv
import uuid
import calendar
import subprocess
import sys
import os
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
        "dreams": 100.0,
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
    Patches datetime in src.core so that get_sustainability_forecast() sees a
    frozen now(). core.py uses `from datetime import datetime`, so we patch
    the name as it appears in that module's namespace.
    """
    RealDatetime = datetime

    class FakeDatetime(RealDatetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_dt

    with patch("src.core.datetime", FakeDatetime):
        yield


def _write_row(manager, t_type, cat, amt_str, env, details="OK", date_str=None):
    """Append a synthetic CSV row to history."""
    t_id = str(uuid.uuid4())[:8]
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([t_id, date_str, t_type, cat, amt_str, env, details])
    return t_id


def _current_month_date_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _last_month_date_str():
    first_of_month = datetime.now().replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    return last_month.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# 1. test_mandatory_burn_rate
# ---------------------------------------------------------------------------

class TestMandatoryBurnRate:
    def test_mandatory_burn_rate_equals_spent_over_days_elapsed(self, manager):
        """mandatory_burn = mandatory_spent / days_elapsed (where days_elapsed = now.day)."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        # Two mandatory expenses this month
        _write_row(manager, "EXPENSE", "rent", "300.00 UAH", "mandatory", "OK", date_str)
        _write_row(manager, "EXPENSE", "rent", "200.00 UAH", "mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        days_elapsed = 10
        expected_mandatory_spent = 500.0
        expected_burn = expected_mandatory_spent / days_elapsed
        assert abs(result["mandatory_burn"] - expected_burn) < 0.01

    def test_mandatory_burn_rate_excludes_non_mandatory_expenses(self, manager):
        """Non-mandatory expenses must not inflate mandatory_burn."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "rent", "400.00 UAH", "mandatory", "OK", date_str)
        _write_row(manager, "EXPENSE", "food", "100.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        expected_burn = 400.0 / 10
        assert abs(result["mandatory_burn"] - expected_burn) < 0.01

    def test_mandatory_spent_returned_correctly(self, manager):
        """mandatory_spent key equals the raw sum of mandatory pool charges."""
        frozen = datetime(2026, 4, 5, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "rent", "250.00 UAH", "mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        assert abs(result["mandatory_spent"] - 250.0) < 0.01


# ---------------------------------------------------------------------------
# 2. test_non_mandatory_burn_rate
# ---------------------------------------------------------------------------

class TestNonMandatoryBurnRate:
    def test_non_mandatory_burn_rate_equals_spent_over_days_elapsed(self, manager):
        """non_mandatory_burn = non_mandatory_spent / days_elapsed."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "taxi", "100.00 UAH", "non_mandatory", "OK", date_str)
        _write_row(manager, "EXPENSE", "food", "150.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        expected_burn = 250.0 / 10
        assert abs(result["non_mandatory_burn"] - expected_burn) < 0.01

    def test_non_mandatory_burn_rate_excludes_mandatory_expenses(self, manager):
        """Mandatory expenses must not inflate non_mandatory_burn."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "rent", "400.00 UAH", "mandatory", "OK", date_str)
        _write_row(manager, "EXPENSE", "taxi", "80.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        expected_burn = 80.0 / 10
        assert abs(result["non_mandatory_burn"] - expected_burn) < 0.01

    def test_non_mandatory_spent_returned_correctly(self, manager):
        """non_mandatory_spent key equals the raw sum of non_mandatory pool charges."""
        frozen = datetime(2026, 4, 5, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "food", "180.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        assert abs(result["non_mandatory_spent"] - 180.0) < 0.01


# ---------------------------------------------------------------------------
# 3. test_days_to_zero_combined
# ---------------------------------------------------------------------------

class TestDaysToZeroCombined:
    def test_days_to_zero_combined_formula(self, manager):
        """days_to_zero_combined = combined_balance / combined_burn."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        # mandatory spend: 200, non_mandatory spend: 300
        _write_row(manager, "EXPENSE", "rent", "200.00 UAH", "mandatory", "OK", date_str)
        _write_row(manager, "EXPENSE", "food", "300.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        # Balances: mandatory=1000, non_mandatory=600 → combined=1600
        # Burns per day: mandatory=200/10=20, non_mandatory=300/10=30 → combined=50
        # days_to_zero_combined = 1600 / 50 = 32
        mandatory_balance = 1000.0
        non_mandatory_balance = 600.0
        combined_balance = mandatory_balance + non_mandatory_balance
        combined_burn = (200.0 / 10) + (300.0 / 10)
        expected = combined_balance / combined_burn
        assert abs(result["days_to_zero_combined"] - expected) < 0.01

    def test_days_to_zero_mandatory_formula(self, manager):
        """days_to_zero_mandatory = mandatory_balance / mandatory_burn."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "rent", "200.00 UAH", "mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        expected = 1000.0 / (200.0 / 10)
        assert abs(result["days_to_zero_mandatory"] - expected) < 0.01

    def test_days_to_zero_non_mandatory_formula(self, manager):
        """days_to_zero_non_mandatory = non_mandatory_balance / non_mandatory_burn."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "food", "120.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        expected = 600.0 / (120.0 / 10)
        assert abs(result["days_to_zero_non_mandatory"] - expected) < 0.01


# ---------------------------------------------------------------------------
# 4. test_safe_daily_limit
# ---------------------------------------------------------------------------

class TestSafeDailyLimit:
    def test_safe_daily_combined_formula(self, manager):
        """safe_daily_combined = combined_balance / days_remaining."""
        # April 10: days_remaining = 30 - 10 = 20
        frozen = datetime(2026, 4, 10, 12, 0, 0)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        combined_balance = 1000.0 + 600.0
        days_remaining = 30 - 10
        expected = combined_balance / days_remaining
        assert abs(result["safe_daily_combined"] - expected) < 0.01

    def test_safe_daily_mandatory_formula(self, manager):
        """safe_daily_mandatory = mandatory_balance / days_remaining."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        expected = 1000.0 / (30 - 10)
        assert abs(result["safe_daily_mandatory"] - expected) < 0.01

    def test_safe_daily_non_mandatory_formula(self, manager):
        """safe_daily_non_mandatory = non_mandatory_balance / days_remaining."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        expected = 600.0 / (30 - 10)
        assert abs(result["safe_daily_non_mandatory"] - expected) < 0.01

    def test_safe_daily_combined_zero_on_last_day_of_month(self, manager):
        """safe_daily_combined = 0 when days_remaining = 0 (last day of month)."""
        last_day = datetime(2026, 4, 30, 12, 0, 0)

        with freeze_datetime(last_day):
            result = manager.get_sustainability_forecast()

        assert abs(result["safe_daily_combined"] - 0.0) < 0.01
        assert result["days_remaining"] == 0

    def test_days_remaining_returned_in_result(self, manager):
        """days_remaining key should reflect calendar days left in the month."""
        frozen = datetime(2026, 4, 15, 12, 0, 0)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        assert result["days_remaining"] == 30 - 15


# ---------------------------------------------------------------------------
# 5. test_zero_days_elapsed — no ZeroDivisionError on day 1
# ---------------------------------------------------------------------------

class TestZeroDaysElapsed:
    def test_no_zero_division_error_on_first_of_month(self, manager):
        """When now.day == 1, days_elapsed is clamped to max(1, 1) = 1 — no ZeroDivisionError."""
        first_of_month = datetime(2026, 4, 1, 0, 0, 0)
        date_str = first_of_month.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "rent", "300.00 UAH", "mandatory", "OK", date_str)

        with freeze_datetime(first_of_month):
            result = manager.get_sustainability_forecast()

        assert result is not None

    def test_burn_rate_correct_on_first_of_month(self, manager):
        """days_elapsed = max(1, 1) = 1 → burn = spent / 1 = spent."""
        first_of_month = datetime(2026, 4, 1, 0, 0, 0)
        date_str = first_of_month.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "rent", "300.00 UAH", "mandatory", "OK", date_str)

        with freeze_datetime(first_of_month):
            result = manager.get_sustainability_forecast()

        assert abs(result["mandatory_burn"] - 300.0) < 0.01

    def test_days_remaining_on_first_of_month(self, manager):
        """April 1: days_remaining = 30 - 1 = 29."""
        first_of_month = datetime(2026, 4, 1, 0, 0, 0)

        with freeze_datetime(first_of_month):
            result = manager.get_sustainability_forecast()

        assert result["days_remaining"] == 29


# ---------------------------------------------------------------------------
# 6. test_zero_burn_rate — no ZeroDivisionError when all burns == 0
# ---------------------------------------------------------------------------

class TestZeroBurnRate:
    def test_no_zero_division_when_no_expenses(self, manager):
        """Empty history → all burns == 0 → no ZeroDivisionError."""
        result = manager.get_sustainability_forecast()
        assert result is not None

    def test_days_to_zero_mandatory_is_inf_when_no_spend(self, manager):
        """Zero mandatory spend → days_to_zero_mandatory == float('inf')."""
        result = manager.get_sustainability_forecast()
        assert result["days_to_zero_mandatory"] == float("inf")

    def test_days_to_zero_non_mandatory_is_inf_when_no_spend(self, manager):
        """Zero non_mandatory spend → days_to_zero_non_mandatory == float('inf')."""
        result = manager.get_sustainability_forecast()
        assert result["days_to_zero_non_mandatory"] == float("inf")

    def test_days_to_zero_combined_is_inf_when_no_spend(self, manager):
        """Zero combined spend → days_to_zero_combined == float('inf')."""
        result = manager.get_sustainability_forecast()
        assert result["days_to_zero_combined"] == float("inf")

    def test_income_only_history_gives_inf_days_to_zero(self, manager):
        """INCOME rows this month must not produce a non-zero burn rate."""
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK")
        result = manager.get_sustainability_forecast()
        assert result["days_to_zero_combined"] == float("inf")

    def test_last_month_expenses_give_zero_burn_rate_this_month(self, manager):
        """Expenses from a prior month must not affect current-month burn rates."""
        last_month = _last_month_date_str()
        _write_row(manager, "EXPENSE", "rent", "500.00 UAH", "mandatory", "OK", last_month)
        result = manager.get_sustainability_forecast()
        assert result["mandatory_burn"] == 0.0
        assert result["days_to_zero_mandatory"] == float("inf")


# ---------------------------------------------------------------------------
# 7. Breach-aware attribution — breach amounts attributed to correct pools
# ---------------------------------------------------------------------------

class TestBreachAttribution:
    def test_breach_from_mandatory_added_to_mandatory_spent(self, manager):
        """
        non_mandatory home expense breaches into mandatory pool.
        The mandatory breach amount must be added to mandatory_spent.
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        # 700 UAH: 600 from non_mandatory (home), 100 from mandatory (breach)
        details = json.dumps({"mandatory": 100.0})
        _write_row(manager, "EXPENSE", "taxi", "700.00 UAH", "non_mandatory", details, date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        # mandatory_spent = 100 (breach portion from mandatory)
        assert abs(result["mandatory_spent"] - 100.0) < 0.01
        # non_mandatory_spent = 600 (home portion)
        assert abs(result["non_mandatory_spent"] - 600.0) < 0.01

    def test_home_portion_attributed_to_home_envelope(self, manager):
        """
        When a mandatory home expense partially breaches non_mandatory,
        the home portion goes to mandatory_spent.
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        # 1200 UAH: 1000 from mandatory (home), 200 from non_mandatory (breach)
        details = json.dumps({"non_mandatory": 200.0})
        _write_row(manager, "EXPENSE", "rent", "1200.00 UAH", "mandatory", details, date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        assert abs(result["mandatory_spent"] - 1000.0) < 0.01
        assert abs(result["non_mandatory_spent"] - 200.0) < 0.01

    def test_fx_expense_uses_uah_amount_from_parentheses(self, manager):
        """FX row '500.00 USD (13750.00 UAH)' → 13750 UAH attributed to non_mandatory_spent."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "food", "500.00 USD (13750.00 UAH)", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        assert abs(result["non_mandatory_spent"] - 13750.0) < 0.01


# ---------------------------------------------------------------------------
# 8. All expected dict keys are present
# ---------------------------------------------------------------------------

class TestReturnedKeys:
    EXPECTED_KEYS = {
        "mandatory_burn",
        "non_mandatory_burn",
        "combined_burn",
        "days_to_zero_mandatory",
        "days_to_zero_non_mandatory",
        "days_to_zero_combined",
        "safe_daily_mandatory",
        "safe_daily_non_mandatory",
        "safe_daily_combined",
        "days_remaining",
        "mandatory_spent",
        "non_mandatory_spent",
    }

    def test_all_required_keys_present(self, manager):
        result = manager.get_sustainability_forecast()
        for key in self.EXPECTED_KEYS:
            assert key in result, f"Missing key: {key}"

    def test_combined_burn_equals_sum_of_individual_burns(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        date_str = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "EXPENSE", "rent", "200.00 UAH", "mandatory", "OK", date_str)
        _write_row(manager, "EXPENSE", "food", "100.00 UAH", "non_mandatory", "OK", date_str)

        with freeze_datetime(frozen):
            result = manager.get_sustainability_forecast()

        assert abs(result["combined_burn"] - (result["mandatory_burn"] + result["non_mandatory_burn"])) < 0.01


# ---------------------------------------------------------------------------
# 9. test_audit_forecast_integration — subprocess check for "SUSTAINABILITY FORECAST"
# ---------------------------------------------------------------------------

class TestAuditForecastIntegration:
    def test_audit_command_shows_sustainability_forecast_header(self):
        """Running `python3 main.py audit` must print the SUSTAINABILITY FORECAST section."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "main.py", "audit"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "SUSTAINABILITY FORECAST" in result.stdout, (
            f"Expected 'SUSTAINABILITY FORECAST' in stdout.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_audit_command_exits_without_error(self):
        """Running `python3 main.py audit` must not crash (returncode == 0)."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "main.py", "audit"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Unexpected non-zero exit code: {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
