import pytest
import json
import csv
import os
import subprocess
import sys
import uuid
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
    Patches datetime in src.core so that calculate_impact() sees a frozen now().
    core.py uses `from datetime import datetime`, so we patch the name in that namespace.
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


def _this_month_income_date():
    """Return a date string for an INCOME row in the current month."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _last_month_date():
    """Return a date string in the previous calendar month."""
    first_of_month = datetime.now().replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    return last_month.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# 1. test_impact_green — small expense within home envelope, risk = GREEN
# ---------------------------------------------------------------------------

class TestImpactGreen:
    def test_risk_score_is_green_for_small_amount(self, manager):
        """
        Balances: mandatory=1000, non_mandatory=600, spendable=1600.
        With days_remaining > 0, a small expense (e.g. 50 UAH) should leave
        daily_after / daily_before >= 0.80 → GREEN.
        Freeze to April 10 so days_remaining = 20.
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(50.0, "food")

        assert result["risk_score"] == "GREEN"

    def test_green_waterfall_not_triggered(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(50.0, "food")

        assert result["waterfall_triggered"] is False

    def test_green_spendable_after_reduced_by_amount(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(50.0, "food")

        # food → non_mandatory, so spendable_after = 1600 - 50 = 1550
        assert abs(result["spendable_after"] - 1550.0) < 0.01

    def test_green_daily_limit_after_less_than_before(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(50.0, "food")

        assert result["daily_limit_after"] < result["daily_limit_before"]


# ---------------------------------------------------------------------------
# 2. test_impact_yellow — amount that reduces daily limit to ~65%, risk = YELLOW
# ---------------------------------------------------------------------------

class TestImpactYellow:
    def test_risk_score_is_yellow(self, manager):
        """
        Freeze April 10 (days_remaining = 20).
        spendable_before = 1600, daily_before = 1600 / 20 = 80.
        For YELLOW: ratio in [0.50, 0.80).
        Target ratio = 0.65 → daily_after = 80 * 0.65 = 52.
        spendable_after = 52 * 20 = 1040 → expense = 1600 - 1040 = 560.
        food → non_mandatory (home), so the 560 comes from non_mandatory (600 available) — no breach.
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(560.0, "food")

        assert result["risk_score"] == "YELLOW"

    def test_yellow_waterfall_not_triggered(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(560.0, "food")

        # 560 fits within non_mandatory (600) — no breach
        assert result["waterfall_triggered"] is False

    def test_yellow_daily_ratio_in_correct_range(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(560.0, "food")

        ratio = result["daily_limit_after"] / result["daily_limit_before"]
        assert 0.50 <= ratio < 0.80


# ---------------------------------------------------------------------------
# 3. test_impact_red — amount reducing daily limit below 50%, risk = RED
# ---------------------------------------------------------------------------

class TestImpactRed:
    def test_risk_score_is_red(self, manager):
        """
        Freeze April 10 (days_remaining = 20).
        spendable_before = 1600, daily_before = 80.
        For RED (no waterfall): ratio < 0.50.
        Target ratio = 0.30 → daily_after = 24 → spendable_after = 480.
        expense = 1600 - 480 = 1120.
        food → non_mandatory (600 available). 1120 > 600, so waterfall triggers.
        Use rent → mandatory (1000 available). 1120 fits entirely in mandatory → no waterfall.
        With rent (mandatory home): hierarchy starts at mandatory. 1120 < 1000? No, 1120 > 1000.
        Remaining after mandatory: 120 → spills into non_mandatory.
        That IS a waterfall. So risk = RED via waterfall.

        Instead use a rent expense of 800 UAH:
        mandatory home: 1000 available → 800 taken → no breach.
        spendable_after = (1000 - 800) + 600 = 800.
        ratio = (800/20) / (1600/20) = 40/80 = 0.50 → YELLOW (not RED).

        Use rent expense of 900:
        spendable_after = 100 + 600 = 700, ratio = 35/80 = 0.4375 → RED (no waterfall).
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(900.0, "rent")

        assert result["risk_score"] == "RED"

    def test_red_no_waterfall_triggered_for_ratio_based_red(self, manager):
        """900 UAH for rent — mandatory has 1000, so no breach. RED is from ratio."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(900.0, "rent")

        assert result["waterfall_triggered"] is False

    def test_red_daily_ratio_below_threshold(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(900.0, "rent")

        ratio = result["daily_limit_after"] / result["daily_limit_before"]
        assert ratio < 0.50


# ---------------------------------------------------------------------------
# 4. test_impact_waterfall_triggered — amount exceeds Mandatory + Non-Mandatory
# ---------------------------------------------------------------------------

class TestImpactWaterfallTriggered:
    def test_waterfall_triggered_true_when_spendable_exhausted(self, manager):
        """
        mandatory=1000, non_mandatory=600, spendable=1600.
        food → non_mandatory (home). 1700 > 600 (non_mandatory) → mandatory used → waterfall.
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(1700.0, "food")

        assert result["waterfall_triggered"] is True

    def test_waterfall_triggered_sets_risk_red(self, manager):
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(1700.0, "food")

        assert result["risk_score"] == "RED"

    def test_waterfall_beyond_all_spendable_uses_investments_and_dreams(self, manager):
        """
        food → non_mandatory. 2500 > all spendable (1600).
        Waterfall hits investments and/or dreams.
        """
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(2500.0, "food")

        assert result["waterfall_triggered"] is True
        assert result["risk_score"] == "RED"

    def test_waterfall_spendable_after_can_be_zero(self, manager):
        """When mandatory+non_mandatory is fully consumed, spendable_after = 0."""
        frozen = datetime(2026, 4, 10, 12, 0, 0)
        income_date = frozen.strftime("%Y-%m-%d %H:%M")
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", income_date)

        with freeze_datetime(frozen):
            result = manager.calculate_impact(2500.0, "food")

        assert abs(result["spendable_after"] - 0.0) < 0.01


# ---------------------------------------------------------------------------
# 5. test_impact_zero_days_remaining — no current-month INCOME row
# ---------------------------------------------------------------------------

class TestImpactZeroDaysRemaining:
    def test_no_income_row_gives_zero_days_remaining(self, manager):
        """No history rows at all → days_remaining == 0."""
        result = manager.calculate_impact(100.0, "food")
        assert result["days_remaining"] == 0

    def test_zero_days_remaining_daily_limit_before_is_zero(self, manager):
        result = manager.calculate_impact(100.0, "food")
        assert abs(result["daily_limit_before"] - 0.0) < 0.01

    def test_zero_days_remaining_no_zero_division_error(self, manager):
        """Must not raise ZeroDivisionError."""
        try:
            result = manager.calculate_impact(100.0, "food")
        except ZeroDivisionError:
            pytest.fail("calculate_impact raised ZeroDivisionError with days_remaining == 0")

    def test_prior_month_income_gives_zero_days_remaining(self, manager):
        """An INCOME row from a previous month must NOT activate the salary cycle."""
        prior_date = _last_month_date()
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed", "OK", prior_date)

        result = manager.calculate_impact(100.0, "food")
        assert result["days_remaining"] == 0

    def test_zero_days_remaining_risk_is_red(self, manager):
        """With daily_limit_before == 0, risk_score must be RED (cannot compute ratio)."""
        result = manager.calculate_impact(100.0, "food")
        assert result["risk_score"] == "RED"

    def test_zero_days_remaining_daily_limit_after_is_zero(self, manager):
        result = manager.calculate_impact(100.0, "food")
        assert abs(result["daily_limit_after"] - 0.0) < 0.01


# ---------------------------------------------------------------------------
# 6. test_impact_bad_argv — non-numeric argv[2] does not crash main.py
# ---------------------------------------------------------------------------

class TestImpactBadArgv:
    def test_non_numeric_amount_exits_without_traceback(self):
        """
        `python3 main.py impact abc` must exit cleanly (no unhandled exception /
        no traceback in stderr). The process may use a non-zero exit code, but
        stderr must not contain 'Traceback'.
        """
        main_py = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py",
        )
        result = subprocess.run(
            [sys.executable, main_py, "impact", "abc"],
            capture_output=True,
            text=True,
        )
        assert "Traceback" not in result.stderr, (
            f"Traceback found in stderr:\n{result.stderr}"
        )

    def test_non_numeric_amount_stderr_or_stdout_contains_error_hint(self):
        """main.py should output a usage or error message when amount is non-numeric."""
        main_py = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py",
        )
        result = subprocess.run(
            [sys.executable, main_py, "impact", "abc"],
            capture_output=True,
            text=True,
        )
        combined = result.stdout + result.stderr
        # The error message should contain something meaningful (usage hint or "number")
        assert any(keyword in combined.lower() for keyword in ["usage", "number", "error", "amount"]), (
            f"Expected an error hint in output, got:\nstdout={result.stdout}\nstderr={result.stderr}"
        )


# ---------------------------------------------------------------------------
# 7. Return keys completeness
# ---------------------------------------------------------------------------

class TestReturnKeysCompleteness:
    EXPECTED_KEYS = {
        "amount",
        "category",
        "spendable_before",
        "spendable_after",
        "daily_limit_before",
        "daily_limit_after",
        "days_remaining",
        "waterfall_triggered",
        "risk_score",
        "category_valid",
    }

    def test_all_required_keys_present(self, manager):
        result = manager.calculate_impact(100.0, "food")
        missing = self.EXPECTED_KEYS - set(result.keys())
        assert not missing, f"Missing keys in result: {missing}"

    def test_category_valid_true_for_known_category(self, manager):
        result = manager.calculate_impact(100.0, "food")
        assert result["category_valid"] is True

    def test_category_valid_false_for_unknown_category(self, manager):
        result = manager.calculate_impact(100.0, "unicorn")
        assert result["category_valid"] is False

    def test_category_none_gives_category_valid_false(self, manager):
        result = manager.calculate_impact(100.0, None)
        assert result["category_valid"] is False

    def test_amount_echoed_in_result(self, manager):
        result = manager.calculate_impact(123.45, "food")
        assert abs(result["amount"] - 123.45) < 0.001

    def test_category_echoed_in_result(self, manager):
        result = manager.calculate_impact(100.0, "rent")
        assert result["category"] == "rent"


# ---------------------------------------------------------------------------
# 8. Read-only — no file mutations
# ---------------------------------------------------------------------------

class TestImpactReadOnly:
    def test_balances_file_unchanged_after_calculate_impact(self, manager):
        """calculate_impact must not write to balances.json."""
        before = (manager.tmp_path if hasattr(manager, "tmp_path") else None)
        # Read balances before
        with open(manager.balances_path) as f:
            balances_before = f.read()

        manager.calculate_impact(500.0, "food")

        with open(manager.balances_path) as f:
            balances_after = f.read()

        assert balances_before == balances_after

    def test_history_file_unchanged_after_calculate_impact(self, manager):
        """calculate_impact must not write to history.csv."""
        _write_row(manager, "INCOME", "Total", "5000.00 UAH", "Distributed")

        with open(manager.history_path) as f:
            history_before = f.read()

        manager.calculate_impact(100.0, "food")

        with open(manager.history_path) as f:
            history_after = f.read()

        assert history_before == history_after


# ---------------------------------------------------------------------------
# 9. Non-positive amounts — edge case
# ---------------------------------------------------------------------------

class TestNonPositiveAmount:
    def test_zero_amount_returns_green(self, manager):
        result = manager.calculate_impact(0.0, "food")
        assert result["risk_score"] == "GREEN"

    def test_zero_amount_waterfall_not_triggered(self, manager):
        result = manager.calculate_impact(0.0, "food")
        assert result["waterfall_triggered"] is False

    def test_zero_amount_spendable_unchanged(self, manager):
        result = manager.calculate_impact(0.0, "food")
        assert abs(result["spendable_before"] - result["spendable_after"]) < 0.01

    def test_negative_amount_returns_green(self, manager):
        result = manager.calculate_impact(-100.0, "food")
        assert result["risk_score"] == "GREEN"
