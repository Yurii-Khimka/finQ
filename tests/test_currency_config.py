import pytest
import json
import io
import sys
import os
from src.core import FinanceManager
from src.ui import FinanceUI


# ---------------------------------------------------------------------------
# Shared fixture
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
# Helper
# ---------------------------------------------------------------------------

def _capture_display_summary(balances, usd_rate=None, eur_rate=None,
                              last_transactions=None, base_currency="UAH"):
    """Captures stdout from FinanceUI.display_summary and returns it as a string."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        FinanceUI.display_summary(
            balances,
            usd_rate=usd_rate,
            eur_rate=eur_rate,
            last_transactions=last_transactions,
            base_currency=base_currency,
        )
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_returns_uah_default_when_file_missing(self, manager):
        """No config.json on disk → base_currency defaults to UAH."""
        assert not os.path.exists(manager.config_path)
        config = manager.load_config()
        assert config["base_currency"] == "UAH"

    def test_returns_uah_default_when_key_absent(self, manager, tmp_path):
        """config.json exists but lacks base_currency → key is injected as UAH."""
        (tmp_path / "config.json").write_text(json.dumps({"some_other_key": True}))
        config = manager.load_config()
        assert config["base_currency"] == "UAH"

    def test_reads_existing_usd_config(self, manager, tmp_path):
        """Existing config with USD is returned as-is."""
        (tmp_path / "config.json").write_text(json.dumps({"base_currency": "USD"}))
        config = manager.load_config()
        assert config["base_currency"] == "USD"

    def test_reads_existing_eur_config(self, manager, tmp_path):
        """Existing config with EUR is returned as-is."""
        (tmp_path / "config.json").write_text(json.dumps({"base_currency": "EUR"}))
        config = manager.load_config()
        assert config["base_currency"] == "EUR"

    def test_returns_dict_type(self, manager):
        """load_config always returns a dict."""
        result = manager.load_config()
        assert isinstance(result, dict)

    def test_preserves_extra_keys(self, manager, tmp_path):
        """Additional keys in the file are preserved alongside base_currency."""
        data = {"base_currency": "EUR", "theme": "dark"}
        (tmp_path / "config.json").write_text(json.dumps(data))
        config = manager.load_config()
        assert config.get("theme") == "dark"


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------

class TestSaveConfig:
    def test_creates_config_file(self, manager, tmp_path):
        """save_config writes config.json to the data directory."""
        manager.save_config({"base_currency": "USD"})
        assert os.path.exists(tmp_path / "config.json")

    def test_written_content_is_valid_json(self, manager, tmp_path):
        """The written file is valid JSON."""
        manager.save_config({"base_currency": "EUR"})
        raw = (tmp_path / "config.json").read_text()
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_written_value_matches_input(self, manager, tmp_path):
        """The base_currency value survives a round-trip through save_config."""
        manager.save_config({"base_currency": "USD"})
        saved = json.loads((tmp_path / "config.json").read_text())
        assert saved["base_currency"] == "USD"

    def test_overwrites_previous_config(self, manager, tmp_path):
        """Calling save_config twice with different values keeps only the last."""
        manager.save_config({"base_currency": "USD"})
        manager.save_config({"base_currency": "EUR"})
        saved = json.loads((tmp_path / "config.json").read_text())
        assert saved["base_currency"] == "EUR"

    def test_persists_additional_keys(self, manager, tmp_path):
        """Extra keys in the config dict are also written to disk."""
        manager.save_config({"base_currency": "UAH", "foo": "bar"})
        saved = json.loads((tmp_path / "config.json").read_text())
        assert saved.get("foo") == "bar"


# ---------------------------------------------------------------------------
# set_base_currency
# ---------------------------------------------------------------------------

class TestSetBaseCurrency:
    # --- Happy path ---

    def test_accepts_uah(self, manager):
        config, error = manager.set_base_currency("UAH")
        assert error is None
        assert config["base_currency"] == "UAH"

    def test_accepts_usd(self, manager):
        config, error = manager.set_base_currency("USD")
        assert error is None
        assert config["base_currency"] == "USD"

    def test_accepts_eur(self, manager):
        config, error = manager.set_base_currency("EUR")
        assert error is None
        assert config["base_currency"] == "EUR"

    def test_accepts_lowercase_input(self, manager):
        """Lowercase 'usd' should be normalised and accepted."""
        config, error = manager.set_base_currency("usd")
        assert error is None
        assert config["base_currency"] == "USD"

    def test_accepts_mixed_case_input(self, manager):
        """Mixed-case 'Eur' should be normalised and accepted."""
        config, error = manager.set_base_currency("Eur")
        assert error is None
        assert config["base_currency"] == "EUR"

    # --- Persistence ---

    def test_persists_to_disk(self, manager, tmp_path):
        """After set_base_currency the value is readable from config.json."""
        manager.set_base_currency("USD")
        saved = json.loads((tmp_path / "config.json").read_text())
        assert saved["base_currency"] == "USD"

    def test_load_config_reflects_change(self, manager):
        """load_config after set_base_currency returns the updated value."""
        manager.set_base_currency("EUR")
        assert manager.load_config()["base_currency"] == "EUR"

    def test_successive_changes_persist_last_value(self, manager):
        """The most recent set_base_currency call wins."""
        manager.set_base_currency("USD")
        manager.set_base_currency("EUR")
        assert manager.load_config()["base_currency"] == "EUR"

    # --- Rejection ---

    def test_rejects_unknown_currency(self, manager):
        config, error = manager.set_base_currency("GBP")
        assert config is None
        assert error is not None
        assert isinstance(error, str)
        assert len(error) > 0

    def test_rejects_empty_string(self, manager):
        config, error = manager.set_base_currency("")
        assert config is None
        assert error is not None

    def test_rejects_numeric_string(self, manager):
        config, error = manager.set_base_currency("123")
        assert config is None
        assert error is not None

    def test_invalid_does_not_modify_config(self, manager):
        """A rejected currency must not overwrite a valid existing config."""
        manager.set_base_currency("USD")
        manager.set_base_currency("INVALID")
        assert manager.load_config()["base_currency"] == "USD"

    def test_error_message_mentions_valid_currencies(self, manager):
        """Error string should help the user know the valid options."""
        _, error = manager.set_base_currency("CHF")
        for valid in ("UAH", "USD", "EUR"):
            assert valid in error

    # --- Return-value contract ---

    def test_success_returns_tuple_of_two(self, manager):
        result = manager.set_base_currency("UAH")
        assert len(result) == 2

    def test_failure_returns_tuple_of_two(self, manager):
        result = manager.set_base_currency("XYZ")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# display_summary — currency-mode branching
# ---------------------------------------------------------------------------

class TestDisplaySummaryBaseCurrency:
    """Tests that display_summary renders the correct layout for each base_currency."""

    BALANCES = {
        "mandatory": 5000.0,
        "non_mandatory": 3000.0,
        "investments": 1000.0,
        "dreams": 1000.0,
    }
    USD_RATE = 40.0   # 1 USD = 40 UAH
    EUR_RATE = 44.0   # 1 EUR = 44 UAH

    # --- UAH mode: three-currency grid ---

    def test_uah_mode_shows_uah_column_header(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="UAH"
        )
        assert "UAH" in output

    def test_uah_mode_shows_usd_column_header(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="UAH"
        )
        assert "USD" in output

    def test_uah_mode_shows_eur_column_header(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="UAH"
        )
        assert "EUR" in output

    def test_uah_mode_shows_all_four_envelopes(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="UAH"
        )
        for label in ("Mandatory", "Non-Mandatory", "Investments", "Dreams"):
            assert label in output

    def test_uah_mode_raw_uah_value_present(self):
        """The UAH envelope value (5000.00) appears verbatim in UAH mode."""
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="UAH"
        )
        assert "5000.00" in output

    # --- USD mode: single-column ---

    def test_usd_mode_shows_usd_header(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="USD"
        )
        assert "USD" in output

    def test_usd_mode_does_not_show_eur_header_as_column(self):
        """EUR should not appear as a column heading in USD mode."""
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="USD"
        )
        # The column header row should not contain EUR as a separate heading
        lines = output.splitlines()
        header_line = next(
            (l for l in lines if "ENVELOPE" in l), ""
        )
        assert "EUR" not in header_line

    def test_usd_mode_converted_value_correct(self):
        """5000 UAH / 40 USD_rate = 125.00 USD for mandatory envelope."""
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="USD"
        )
        assert "125.00" in output

    def test_usd_mode_total_converted_correctly(self):
        """Total 10000 UAH / 40 = 250.00 USD."""
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="USD"
        )
        assert "250.00" in output

    def test_usd_mode_single_column_width(self):
        """USD mode uses a narrower 48-char separator, not the 78-char UAH grid."""
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="USD"
        )
        assert "=" * 48 in output
        assert "=" * 78 not in output

    # --- EUR mode: single-column ---

    def test_eur_mode_shows_eur_header(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="EUR"
        )
        assert "EUR" in output

    def test_eur_mode_does_not_show_usd_header_as_column(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="EUR"
        )
        lines = output.splitlines()
        header_line = next(
            (l for l in lines if "ENVELOPE" in l), ""
        )
        assert "USD" not in header_line

    def test_eur_mode_converted_value_correct(self):
        """5000 UAH / 44 EUR_rate ≈ 113.64 EUR for mandatory envelope."""
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="EUR"
        )
        assert "113.64" in output

    def test_eur_mode_total_converted_correctly(self):
        """Total 10000 UAH / 44 ≈ 227.27 EUR."""
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="EUR"
        )
        assert "227.27" in output

    def test_eur_mode_single_column_width(self):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency="EUR"
        )
        assert "=" * 48 in output
        assert "=" * 78 not in output

    # --- Envelope rows always present regardless of currency mode ---

    @pytest.mark.parametrize("currency", ["UAH", "USD", "EUR"])
    def test_all_envelope_labels_present_in_every_mode(self, currency):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency=currency
        )
        for label in ("Mandatory", "Non-Mandatory", "Investments", "Dreams"):
            assert label in output

    @pytest.mark.parametrize("currency", ["UAH", "USD", "EUR"])
    def test_total_and_spendable_rows_present_in_every_mode(self, currency):
        output = _capture_display_summary(
            self.BALANCES, self.USD_RATE, self.EUR_RATE, base_currency=currency
        )
        assert "TOTAL ACCOUNT" in output
        assert "SPENDABLE NOW" in output
