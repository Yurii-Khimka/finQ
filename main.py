import sys
import os
from core import FinanceManager
from ui import FinanceUI

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manager = FinanceManager(base_dir)
    ui = FinanceUI()

    def get_rates():
        return manager.get_rate("USD"), manager.get_rate("EUR")

    def show_dashboard(balances):
        usd, eur = get_rates()
        ui.display_summary(balances, usd, eur, manager.get_last_transactions())

    if len(sys.argv) < 2:
        show_dashboard(manager._load_json(manager.balances_path))
        return

    cmd = sys.argv[1].lower()

    if cmd in ["help", "-h"]:
        ui.display_help()
    elif cmd == "ac":
        ui.display_categories(manager._load_json(manager.categories_path))
    elif cmd == "cs":
        ui.display_stats(manager.get_monthly_stats())
    elif cmd == "db" and len(sys.argv) == 3:
        try:
            days = int(sys.argv[2])
            bal = manager._load_json(manager.balances_path)
            usd, eur = get_rates()
            ui.display_daily_budget(bal.get("mandatory",0), bal.get("non_mandatory",0), days, usd, eur)
        except: ui.show_error("Usage: fq db <days>")
    elif cmd in ["buy", "b"] and len(sys.argv) == 4:
        try:
            env, bal = manager.add_expense(sys.argv[2], float(sys.argv[3]))
            if env: show_dashboard(bal)
            else: ui.show_error("Category unknown. Use 'fq ac'.")
        except: ui.show_error("Usage: fq b <cat> <amt>")
    elif cmd in ["earn", "e"] and len(sys.argv) >= 3:
        try:
            amount = float(sys.argv[2])
            args = " ".join(sys.argv[3:]).lower()
            final_uah, curr = amount, "UAH"
            for c in ["USD", "EUR"]:
                if c.lower() in args:
                    rate = manager.get_rate(c)
                    if rate: final_uah, curr = amount * rate, c
            if "salary" in args: manager.flush_leftovers()
            show_dashboard(manager.add_income(final_uah, curr, amount))
        except: ui.show_error("Usage: fq e <amt> [flags]")
    elif cmd in ["sync", "s"] and len(sys.argv) == 3:
        try: show_dashboard(manager.sync_balance(float(sys.argv[2])))
        except: ui.show_error("Usage: fq s <total>")
    elif cmd == "hard-reset":
        if input("⚠️ Wipe data? (y/n): ").lower() == 'y':
            manager._save_json(manager.balances_path, {"mandatory":0,"non_mandatory":0,"investments":0,"dreams":0})
            if os.path.exists(manager.history_path): open(manager.history_path, 'w').close()
            print("✅ Reset complete.")
    else: ui.show_error("Unknown command. Try 'fq help'.")

if __name__ == "__main__":
    main()