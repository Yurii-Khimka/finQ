import sys
import os
from src.core import FinanceManager
from src.ui import FinanceUI

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    manager = FinanceManager(data_dir)
    ui = FinanceUI()

    def get_rates():
        return manager.get_rate("USD"), manager.get_rate("EUR")

    def get_base_currency():
        return manager.load_config().get("base_currency", "UAH")

    def show_dashboard(balances):
        usd, eur = get_rates()
        base_currency = get_base_currency()
        ui.display_summary(balances, usd, eur, manager.get_last_transactions(), base_currency)
        ui.display_forecast(manager.get_daily_forecast())

    if len(sys.argv) < 2:
        show_dashboard(manager._load_json(manager.balances_path))
        return

    cmd = sys.argv[1].lower()

    if cmd in ["help", "-h"]:
        ui.display_help()
    elif cmd == "ac":
        sorted_cats = manager.get_sorted_categories()
        ui.display_categories(sorted_cats)
    elif cmd == "cs":
        filter_val = sys.argv[2].lower() if len(sys.argv) >= 3 else None
        ui.display_stats(manager.get_monthly_stats(filter_val), filter_val)
    elif cmd == "rm" and len(sys.argv) == 3:
        t_id = sys.argv[2]
        new_balances, error = manager.remove_transaction(t_id)
        if error:
            ui.show_error(error)
        else:
            show_dashboard(new_balances)
    elif cmd == "ls":
        from datetime import datetime
        if len(sys.argv) < 3:
            filter_val = datetime.now().strftime("%m")
        else:
            filter_val = sys.argv[2].lower()
        history_data = manager.get_filtered_history(filter_val)
        title = "ALL TIME HISTORY" if filter_val == "all" else f"HISTORY FOR MONTH: {filter_val}"
        ui.display_history_table(history_data, title)
    elif cmd in ["buy", "b"] and len(sys.argv) in [4, 5]:
        try:
            currency = sys.argv[4].upper() if len(sys.argv) == 5 else "UAH"
            balances, note = manager.add_expense(sys.argv[2], float(sys.argv[3]), currency)
            if balances:
                show_dashboard(balances)
                if note:
                    ui.show_warning(note)
            else:
                ui.show_error("Transaction failed. Check category name.")
        except Exception as e:
            ui.show_error(f"Usage: fq b <cat> <amt> [usd|eur]. Error: {e}")
    elif cmd in ["earn", "e"] and len(sys.argv) >= 3:
        try:
            amount = float(sys.argv[2])
            args = " ".join(sys.argv[3:]).lower() if len(sys.argv) > 3 else ""
            final_uah, curr = amount, "UAH"
            for c in ["USD", "EUR"]:
                if c.lower() in args:
                    rate = manager.get_rate(c)
                    if rate:
                        final_uah, curr = amount * rate, c
            manager.flush_leftovers()
            show_dashboard(manager.add_income(final_uah, curr, amount))
        except Exception as e:
            ui.show_error(f"Usage: fq e <amt> [usd|eur]. Error: {e}")
    elif cmd in ["sv", "savings"] and len(sys.argv) >= 3:
        try:
            amount = float(sys.argv[2])
            args = " ".join(sys.argv[3:]).lower() if len(sys.argv) > 3 else ""
            final_uah, curr = amount, "UAH"
            for c in ["USD", "EUR"]:
                if c.lower() in args:
                    rate = manager.get_rate(c)
                    if rate:
                        final_uah, curr = amount * rate, c
            show_dashboard(manager.add_savings(final_uah, curr, amount))
        except Exception as e:
            ui.show_error(f"Usage: fq sv <amt> [usd|eur]. Error: {e}")
    elif cmd in ["sync", "s"] and len(sys.argv) == 3:
        try:
            show_dashboard(manager.sync_balance(float(sys.argv[2])))
        except Exception as e:
            ui.show_error(f"Usage: fq sync <total>. Error: {e}")
    else:
        ui.show_error("Unknown command. Try 'fq help'.")

if __name__ == "__main__":
    main()
