import pytest
import json
import csv
from unittest.mock import patch
from src.core import FinanceManager


@pytest.fixture
def manager(tmp_path):
    """Creates an isolated FinanceManager with clean test data."""
    balances = {
        "mandatory": 10000.0,
        "non_mandatory": 5000.0,
        "investments": 2000.0,
        "dreams": 2000.0,
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


def _read_history(manager):
    with open(manager.history_path, newline="", encoding="utf-8") as f:
        return [row for row in csv.reader(f) if row]


def _load_balances(manager):
    with open(manager.balances_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Clean FX expense — no breach
# ---------------------------------------------------------------------------

class TestFxExpenseClean:
    def test_uah_amount_deducted_from_home_envelope(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        bal = _load_balances(manager)
        # 10 USD * 40.0 = 400.0 UAH deducted from non_mandatory (taxi's home)
        assert abs(bal["non_mandatory"] - (5000.0 - 400.0)) < 0.01

    def test_other_envelopes_untouched_on_clean_fx(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        bal = _load_balances(manager)
        assert abs(bal["mandatory"] - 10000.0) < 0.01
        assert abs(bal["investments"] - 2000.0) < 0.01
        assert abs(bal["dreams"] - 2000.0) < 0.01

    def test_details_is_ok_on_clean_fx(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        rows = _read_history(manager)
        assert len(rows) == 1
        assert rows[0][6] == "OK"

    def test_amount_uah_column_contains_converted_value(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        rows = _read_history(manager)
        assert len(rows) == 1
        # AMOUNT column: "400.00 UAH"
        amount_field = rows[0][4]
        uah_value = float(amount_field.split()[0])
        assert abs(uah_value - 400.0) < 0.01

    def test_no_fx_metadata_keys_in_details(self, manager):
        """DETAILS must not contain original/rate keys — only breach envelope keys."""
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        rows = _read_history(manager)
        details = rows[0][6]
        assert details == "OK"

    def test_csv_row_has_exactly_7_columns(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        rows = _read_history(manager)
        assert len(rows[0]) == 7


# ---------------------------------------------------------------------------
# 2. FX expense with waterfall breach
# ---------------------------------------------------------------------------

class TestFxExpenseBreach:
    def test_breach_details_contain_only_envelope_keys(self, manager):
        """Spend 300 USD = 12000 UAH — exceeds non_mandatory (5000) by 7000."""
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")  # 12000 UAH total

        rows = _read_history(manager)
        details = rows[0][6]
        assert details != "OK"
        breach = json.loads(details)
        valid_envelopes = {"mandatory", "non_mandatory", "investments", "dreams"}
        for key in breach:
            assert key in valid_envelopes, f"Unexpected key in DETAILS: {key!r}"
        assert "original" not in breach
        assert "rate" not in breach

    def test_breach_uah_amounts_match_converted_total(self, manager):
        """
        non_mandatory=5000, mandatory=10000. Spend 300 USD = 12000 UAH.
        Waterfall: 5000 from non_mandatory (home), 7000 from mandatory.
        """
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")

        rows = _read_history(manager)
        breach = json.loads(rows[0][6])
        # mandatory should be charged 7000
        assert abs(breach["mandatory"] - 7000.0) < 0.01

    def test_home_envelope_zeroed_before_waterfall(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")

        bal = _load_balances(manager)
        assert abs(bal["non_mandatory"] - 0.0) < 0.01

    def test_mandatory_reduced_by_breach_amount(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")

        bal = _load_balances(manager)
        assert abs(bal["mandatory"] - (10000.0 - 7000.0)) < 0.01

    def test_multi_envelope_breach_sums_to_total(self, manager):
        """
        Spend 500 USD = 20000 UAH.
        non_mandatory=5000 (home, exhausted), mandatory=10000 (exhausted),
        investments=2000 (partially), dreams absorbs rest.
        Total breach = non_mandatory exhausted + mandatory + investments + dreams.
        home is not in breach_data; sum of breach_data + home_taken == total.
        """
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 500, "USD")  # 20000 UAH

        rows = _read_history(manager)
        breach = json.loads(rows[0][6])
        breach_total = sum(breach.values())
        # home (non_mandatory) exhausted 5000, breach covers 15000
        assert abs(breach_total - 15000.0) < 0.01

    def test_csv_row_has_exactly_7_columns_on_breach(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")

        rows = _read_history(manager)
        assert len(rows[0]) == 7


# ---------------------------------------------------------------------------
# 3. UAH expense — get_rate must NOT be called
# ---------------------------------------------------------------------------

class TestUahExpenseUnchanged:
    def test_get_rate_not_called_for_uah(self, manager):
        with patch.object(manager, "get_rate") as mock_rate:
            manager.add_expense("food", 100)
            mock_rate.assert_not_called()

    def test_uah_expense_deducts_correct_amount(self, manager):
        manager.add_expense("food", 100)
        bal = _load_balances(manager)
        assert abs(bal["non_mandatory"] - (5000.0 - 100.0)) < 0.01

    def test_uah_expense_details_is_ok_when_no_breach(self, manager):
        manager.add_expense("food", 100)
        rows = _read_history(manager)
        assert rows[0][6] == "OK"

    def test_uah_expense_explicit_currency_arg_no_rate_call(self, manager):
        """Passing currency='UAH' explicitly must also skip get_rate."""
        with patch.object(manager, "get_rate") as mock_rate:
            manager.add_expense("food", 100, "UAH")
            mock_rate.assert_not_called()


# ---------------------------------------------------------------------------
# 4. get_rate failure
# ---------------------------------------------------------------------------

class TestGetRateFailure:
    def test_returns_none_and_error_string(self, manager):
        with patch.object(manager, "get_rate", return_value=None):
            result = manager.add_expense("taxi", 10, "USD")

        assert result[0] is None
        assert isinstance(result[1], str)
        assert len(result[1]) > 0

    def test_no_row_written_to_history_on_rate_failure(self, manager):
        with patch.object(manager, "get_rate", return_value=None):
            manager.add_expense("taxi", 10, "USD")

        rows = _read_history(manager)
        assert len(rows) == 0

    def test_balances_unchanged_on_rate_failure(self, manager):
        original = _load_balances(manager)
        with patch.object(manager, "get_rate", return_value=None):
            manager.add_expense("taxi", 10, "USD")

        after = _load_balances(manager)
        for key in original:
            assert abs(original[key] - after[key]) < 0.01


# ---------------------------------------------------------------------------
# 5. Reversal of clean FX expense (DETAILS = "OK")
# ---------------------------------------------------------------------------

class TestRemoveCleanFxExpense:
    def test_home_envelope_restored_by_exact_uah_amount(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")  # -400 from non_mandatory

        t_id = _read_history(manager)[0][0]
        manager.remove_transaction(t_id)

        bal = _load_balances(manager)
        assert abs(bal["non_mandatory"] - 5000.0) < 0.01

    def test_other_envelopes_unchanged_after_clean_removal(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        t_id = _read_history(manager)[0][0]
        manager.remove_transaction(t_id)

        bal = _load_balances(manager)
        assert abs(bal["mandatory"] - 10000.0) < 0.01
        assert abs(bal["investments"] - 2000.0) < 0.01
        assert abs(bal["dreams"] - 2000.0) < 0.01

    def test_transaction_removed_from_history(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 10, "USD")

        t_id = _read_history(manager)[0][0]
        manager.remove_transaction(t_id)

        rows = _read_history(manager)
        assert all(row[0] != t_id for row in rows)


# ---------------------------------------------------------------------------
# 6. Reversal of FX expense with waterfall breach
# ---------------------------------------------------------------------------

class TestRemoveBreachFxExpense:
    def test_home_envelope_restored_minus_breach(self, manager):
        """
        300 USD = 12000 UAH. non_mandatory (home) had 5000 — takes all 5000.
        mandatory covers remaining 7000. DETAILS = {"mandatory": 7000.0}.
        On remove: non_mandatory += (12000 - 7000) = 5000, mandatory += 7000.
        """
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")

        t_id = _read_history(manager)[0][0]
        manager.remove_transaction(t_id)

        bal = _load_balances(manager)
        assert abs(bal["non_mandatory"] - 5000.0) < 0.01

    def test_breach_envelopes_restored_by_exact_borrowed_amounts(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")

        t_id = _read_history(manager)[0][0]
        manager.remove_transaction(t_id)

        bal = _load_balances(manager)
        assert abs(bal["mandatory"] - 10000.0) < 0.01

    def test_investments_and_dreams_not_affected_when_not_breached(self, manager):
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 300, "USD")

        t_id = _read_history(manager)[0][0]
        manager.remove_transaction(t_id)

        bal = _load_balances(manager)
        assert abs(bal["investments"] - 2000.0) < 0.01
        assert abs(bal["dreams"] - 2000.0) < 0.01

    def test_old_details_with_original_and_rate_keys_skipped_gracefully(self, manager):
        """
        If a legacy row has {"non_mandatory": 50.0, "original": 10.0, "rate": 40.0}
        only "non_mandatory" is a valid envelope; original/rate must be silently skipped.
        """
        import uuid
        from datetime import datetime

        # Write a synthetic legacy row directly to history.csv
        t_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        legacy_details = json.dumps({"non_mandatory": 50.0, "original": 10.0, "rate": 40.0})
        with open(manager.history_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [t_id, date_str, "EXPENSE", "rent", "200.00 UAH", "mandatory", legacy_details]
            )

        # Pre-load balances to record baseline
        bal_before = _load_balances(manager)

        result = manager.remove_transaction(t_id)
        assert result[0] is not None, f"remove_transaction failed: {result[1]}"

        bal_after = _load_balances(manager)
        # mandatory (home) restored by (200 - 50) = 150
        assert abs(bal_after["mandatory"] - (bal_before["mandatory"] + 150.0)) < 0.01
        # non_mandatory restored by 50
        assert abs(bal_after["non_mandatory"] - (bal_before["non_mandatory"] + 50.0)) < 0.01

    def test_remove_nonexistent_id_returns_none_and_error(self, manager):
        result = manager.remove_transaction("deadbeef")
        assert result[0] is None
        assert isinstance(result[1], str)

    def test_balances_unchanged_on_nonexistent_remove(self, manager):
        original = _load_balances(manager)
        manager.remove_transaction("deadbeef")
        after = _load_balances(manager)
        for key in original:
            assert abs(original[key] - after[key]) < 0.01

    def test_full_multi_envelope_breach_reversal(self, manager):
        """
        500 USD = 20000 UAH.
        non_mandatory=5000 (home, zeroed), mandatory=10000 (zeroed),
        investments=2000 (zeroed), dreams absorbs 3000 (goes to -1000).
        After remove, all envelopes return to starting values.
        """
        with patch.object(manager, "get_rate", return_value=40.0):
            manager.add_expense("taxi", 500, "USD")

        t_id = _read_history(manager)[0][0]
        manager.remove_transaction(t_id)

        bal = _load_balances(manager)
        assert abs(bal["non_mandatory"] - 5000.0) < 0.01
        assert abs(bal["mandatory"] - 10000.0) < 0.01
        assert abs(bal["investments"] - 2000.0) < 0.01
        assert abs(bal["dreams"] - 2000.0) < 0.01
