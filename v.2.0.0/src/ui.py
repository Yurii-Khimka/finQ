import json
from datetime import datetime

class FinanceUI:
    @staticmethod
    def display_summary(balances, usd_rate=None, eur_rate=None, last_transactions=None, base_currency="UAH"):
        """
        Displays the main dashboard.
        If base_currency is UAH: shows three columns (UAH | USD | EUR).
        If base_currency is USD or EUR: shows a single column in that currency.
        """
        def conv(val, rate): return val / rate if rate else 0

        keys = [("Mandatory", "mandatory"), ("Non-Mandatory", "non_mandatory"),
                ("Investments", "investments"), ("Dreams", "dreams")]

        total = sum(balances.values())
        spendable = balances.get("mandatory", 0) + balances.get("non_mandatory", 0)

        if base_currency == "UAH":
            # Full three-currency grid
            print("\n" + "=" * 78)
            print(f"{'ENVELOPE':<18} | {'UAH':>14} | {'USD':>12} | {'EUR':>12}")
            print("-" * 78)

            for label, key in keys:
                val = balances.get(key, 0)
                print(f"{label:<18} | {val:>14.2f} | {conv(val, usd_rate):>12.2f} | {conv(val, eur_rate):>12.2f}")

            print("-" * 78)
            print(f"{'TOTAL ACCOUNT':<18} | {total:>14.2f} | {conv(total, usd_rate):>12.2f} | {conv(total, eur_rate):>12.2f}")
            print(f"{'SPENDABLE NOW':<18} | {spendable:>14.2f} | {conv(spendable, usd_rate):>12.2f} | {conv(spendable, eur_rate):>12.2f}")
            print("=" * 78)
        else:
            # Single-currency view — convert all UAH values to the chosen currency
            rate = usd_rate if base_currency == "USD" else eur_rate

            if rate is None:
                print(f"\n[!] Rate unavailable — showing UAH (base currency: {base_currency})")
                print("\n" + "=" * 48)
                print(f"{'ENVELOPE':<18} | {'UAH':>26}")
                print("-" * 48)
                for label, key in keys:
                    val = balances.get(key, 0)
                    print(f"{label:<18} | {val:>26.2f}")
                print("-" * 48)
                print(f"{'TOTAL ACCOUNT':<18} | {total:>26.2f}")
                print(f"{'SPENDABLE NOW':<18} | {spendable:>26.2f}")
                print("=" * 48)
            else:
                col_label = base_currency
                print("\n" + "=" * 48)
                print(f"{'ENVELOPE':<18} | {col_label:>26}")
                print("-" * 48)
                for label, key in keys:
                    val = conv(balances.get(key, 0), rate)
                    print(f"{label:<18} | {val:>26.2f}")
                print("-" * 48)
                print(f"{'TOTAL ACCOUNT':<18} | {conv(total, rate):>26.2f}")
                print(f"{'SPENDABLE NOW':<18} | {conv(spendable, rate):>26.2f}")
                print("=" * 48)

        if last_transactions:
            print("\n🕒 RECENT ACTIVITY:")
            print("-" * 82)
            print(f"{'ID':<9} | {'DATE':<16} | {'TYPE':<8} | {'CAT':<16} | {'AMOUNT':>12}")
            print("-" * 82)
            for row in last_transactions:
                if len(row) >= 6:
                    t_id, date, t_type, cat, amt_str, _ = row[:6]
                    status_mark = " [!]" if len(row) > 6 and row[6] != "OK" else ""
                    print(f"{t_id:<9} | {date:<16} | {t_type:<8} | {cat:<16} | {amt_str + status_mark:>12}")
            print("-" * 82 + "\n")

    @staticmethod
    def display_forecast(data: dict) -> None:
        """Renders daily forecast vs actual spending for the current month."""
        days_elapsed = data.get("days_elapsed", 1)
        days_in_cycle = data.get("days_in_cycle", 30)
        days_remaining = data.get("days_remaining", 0)

        m_forecast = data.get("mandatory_forecast", 0.0)
        m_actual = data.get("mandatory_actual", 0.0)
        m_diff = m_forecast - m_actual

        nm_forecast = data.get("non_mandatory_forecast", 0.0)
        nm_actual = data.get("non_mandatory_actual", 0.0)
        nm_diff = nm_forecast - nm_actual

        t_forecast = data.get("total_forecast", 0.0)
        t_actual = data.get("total_actual", 0.0)
        t_diff = t_forecast - t_actual

        def fmt_diff(val):
            sign = "+" if val >= 0 else ""
            return f"{sign}{val:.2f}"

        print(f"DAILY BUDGET  (day {days_elapsed} of {days_in_cycle}, {days_remaining} days remaining)")
        print("-" * 72)
        print(f"{'ENVELOPE':<18} | {'FORECAST/day':>14} | {'ACTUAL/day':>14} | {'DIFF':>12}")
        print("-" * 72)
        print(f"{'Mandatory':<18} | {m_forecast:>11.2f} UAH | {m_actual:>11.2f} UAH | {fmt_diff(m_diff):>9} UAH")
        print(f"{'Non-Mandatory':<18} | {nm_forecast:>11.2f} UAH | {nm_actual:>11.2f} UAH | {fmt_diff(nm_diff):>9} UAH")
        print("-" * 72)
        print(f"{'TOTAL':<18} | {t_forecast:>11.2f} UAH | {t_actual:>11.2f} UAH | {fmt_diff(t_diff):>9} UAH")
        print("-" * 72 + "\n")

    @staticmethod
    def display_stats(stats, filter_val: str = None):
        """Displays spending report with category breakdown.

        filter_val=None       → current month
        filter_val="all"      → all time
        filter_val="04" etc.  → specific month
        """
        if filter_val is None:
            period_label = f"current month ({datetime.now().strftime('%m/%Y')})"
        elif filter_val == "all":
            period_label = "all time"
        else:
            period_label = f"month {filter_val.zfill(2)}"

        print("\n" + "=" * 55)
        print(f"STATS FOR: {period_label}")
        print("=" * 55)

        for env_key in ["mandatory", "non_mandatory", "investments", "dreams"]:
            data = stats[env_key]
            if not data["cats"]: continue

            title = env_key.upper().replace("_", "-")
            print("\n" + "-" * 55)
            print(f"📂 {title}")
            print("-" * 55)

            sorted_cats = sorted(data["cats"].items(), key=lambda x: x[1], reverse=True)
            for cat, amt in sorted_cats:
                print(f"{cat:<25} | {amt:>18.2f} UAH")

            print("-" * 55)
            print(f"{'TOTAL ' + title:<25} | {data['total']:>18.2f} UAH")
            print("-" * 55)
        print("\n")

    @staticmethod
    def display_categories(sorted_categories):
        """Displays a compact table of all categories."""
        if not sorted_categories:
            print("No categories found.")
            return

        header = f"| {'#':^3} | {'CATEGORY':<20} | {'ENVELOPE':<15} |"
        separator = "-" * len(header)

        print("\n" + separator)
        print(header)
        print(separator)

        for i, (cat, env) in enumerate(sorted_categories, 1):
            env_display = env.upper()
            print(f"| {i:^3} | {cat:<20} | {env_display:<15} |")

        print(separator)
        print(f"Total: {len(sorted_categories)} categories. Use 'fq b <cat> <amt>'\n")

    @staticmethod
    def display_history_table(rows, title="TRANSACTION HISTORY"):
        """Renders history with dynamic summaries and fixed alignment."""
        if not rows:
            print("\nEmpty history for this period.")
            return

        print(f"\n📜 {title}")
        print("=" * 115)
        # Wider column for AMOUNT to handle income strings (e.g. USD + UAH)
        header = f"{'ID':<9} | {'DATE':<16} | {'TYPE':<8} | {'CATEGORY':<15} | {'AMOUNT':<30} | {'ENV':<12} | {'!'}"
        print(header)
        print("-" * 115)

        total_income = 0.0
        total_expense = 0.0

        for row in rows:
            t_id, date, t_type, cat, amt_str, env = row[:6]
            details = row[6] if len(row) > 6 else "OK"
            marker = "[!]" if details != "OK" else "   "

            # AMOUNT column already encodes FX info (e.g. "1500.00 USD (41250.00 UAH)")
            display_amt = amt_str

            # Calculation logic for summary
            try:
                # Legacy rows stored "1000.00 USD (41500.00 UAH)" in AMOUNT_UAH
                if "(" in amt_str:
                    val = float(amt_str.split("(")[1].split()[0])
                else:
                    val = float(amt_str.split()[0])

                if t_type == "INCOME": total_income += val
                elif t_type == "EXPENSE": total_expense += val
            except (ValueError, IndexError): pass

            print(f"{t_id:<9} | {date:<16} | {t_type:<8} | {cat:<15} | {display_amt:<30} | {env.upper():<12} | {marker}")

        print("-" * 115)
        print(f"💰 SUMMARY FOR THIS PERIOD:")
        print(f"   TOTAL INCOME:   {total_income:>15.2f} UAH")
        print(f"   TOTAL EXPENSES: {total_expense:>15.2f} UAH")
        print(f"   NET FLOW:       {total_income - total_expense:>15.2f} UAH")
        print("=" * 115 + "\n")

    @staticmethod
    def display_help():
        print("\n" + "=" * 65)
        print("finQ TERMINAL GUIDE")
        print("=" * 65)
        print(f"{'fq':<24} Dashboard with daily forecast")
        print(f"{'fq ls [month/all]':<24} Transaction history")
        print(f"{'fq cs [month/all]':<24} Category spending stats")
        print(f"{'fq ac':<24} List all categories")
        print(f"{'fq b <cat> <amt> [cur]':<24} Record expense")
        print(f"{'fq e <amt> [usd|eur]':<24} Record salary (50/30/10/10 split)")
        print(f"{'fq sv <amt> [usd|eur]':<24} Record savings (50/50 to investments/dreams)")
        print(f"{'fq rm <id>':<24} Remove transaction and restore balance")
        print(f"{'fq sync <total>':<24} Proportional balance adjustment")
        print("\nEXAMPLES:")
        print("-" * 65)
        print("Salary:                    fq e 50000")
        print("Salary (USD):              fq e 1500 usd")
        print("Savings:                   fq sv 10000")
        print("Savings (USD):             fq sv 500 usd")
        print("Expense:                   fq b food 150")
        print("Expense (USD):             fq b food 4 usd")
        print("History this month:        fq ls")
        print("All history:               fq ls all")
        print("Stats this month:          fq cs")
        print("Stats all time:            fq cs all")
        print("Remove transaction:        fq rm a1b2c3d4")
        print("=" * 65 + "\n")

    @staticmethod
    def show_error(msg): print(f"ERROR: {msg}")

    @staticmethod
    def show_warning(msg):
        print(f"\n  [!] {msg}")

    @staticmethod
    def show_info(msg): print(f"[OK] {msg}")
