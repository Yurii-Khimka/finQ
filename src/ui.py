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
    def display_stats(stats):
        """Displays monthly spending report with category breakdown."""
        print("\n📊 MONTHLY CATEGORY SUMMARY")
        
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
    def display_daily_budget(mand, non_mand, days, usd, eur, base_currency="UAH"):
        """
        Displays daily limits with envelope breakdown.
        If base_currency is UAH: three-currency grid.
        If base_currency is USD or EUR: single-column in that currency.
        """
        def conv(val, rate): return val / rate if rate else 0

        # Calculate daily slices for each spendable envelope
        d_mand = mand / days
        d_non = non_mand / days
        d_total = (mand + non_mand) / days

        if base_currency == "UAH":
            print("\n" + f"📅 DAILY LIMITS (For {days} days)")
            print("-" * 65)
            print(f"{'TYPE':<18} | {'UAH':>14} | {'USD':>12} | {'EUR':>12}")
            print("-" * 65)
            print(f"{'Mandatory':<18} | {d_mand:>14.2f} | {conv(d_mand, usd):>12.2f} | {conv(d_mand, eur):>12.2f}")
            print(f"{'Non-Mandatory':<18} | {d_non:>14.2f} | {conv(d_non, usd):>12.2f} | {conv(d_non, eur):>12.2f}")
            print("-" * 65)
            print(f"{'DAILY TOTAL':<18} | {d_total:>14.2f} | {conv(d_total, usd):>12.2f} | {conv(d_total, eur):>12.2f}")
            print("-" * 65 + "\n")
        else:
            # Single-currency view
            rate = usd if base_currency == "USD" else eur

            if rate is None:
                print(f"\n[!] Rate unavailable — showing UAH (base currency: {base_currency})")
                print("\n" + f"📅 DAILY LIMITS (For {days} days)")
                print("-" * 48)
                print(f"{'TYPE':<18} | {'UAH':>26}")
                print("-" * 48)
                print(f"{'Mandatory':<18} | {d_mand:>26.2f}")
                print(f"{'Non-Mandatory':<18} | {d_non:>26.2f}")
                print("-" * 48)
                print(f"{'DAILY TOTAL':<18} | {d_total:>26.2f}")
                print("-" * 48 + "\n")
            else:
                col_label = base_currency
                print("\n" + f"📅 DAILY LIMITS (For {days} days)")
                print("-" * 48)
                print(f"{'TYPE':<18} | {col_label:>26}")
                print("-" * 48)
                print(f"{'Mandatory':<18} | {conv(d_mand, rate):>26.2f}")
                print(f"{'Non-Mandatory':<18} | {conv(d_non, rate):>26.2f}")
                print("-" * 48)
                print(f"{'DAILY TOTAL':<18} | {conv(d_total, rate):>26.2f}")
                print("-" * 48 + "\n")

    @staticmethod
    def display_categories(sorted_categories):
        """Displays a compact table of all categories."""
        if not sorted_categories:
            print("⚠️ No categories found.")
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
    def display_audit(data: dict) -> None:
        """Renders the monthly budget audit report with breach summary and burn rate forecast."""
        W = 65
        thick = "=" * W
        thin = "-" * W

        month_label = datetime.now().strftime("%B %Y").upper()

        health_raw = data.get("health_signal", "healthy")
        if health_raw == "healthy":
            health_display = "[OK] HEALTHY"
        elif health_raw == "warning":
            health_display = "[!] WARNING"
        else:
            health_display = "!! CRITICAL"

        breach_count = data.get("breach_count", 0)
        breach_total = data.get("breach_total_uah", 0.0)
        breach_by_env = data.get("breach_by_envelope", {})
        top_breaches = data.get("top_breaches", [])
        total_spent = data.get("total_spent_uah", 0.0)
        burn_rate = data.get("burn_rate_daily", 0.0)
        days_remaining = data.get("days_remaining", 0)
        days_to_zero = data.get("days_to_zero", float("inf"))
        safe_daily = data.get("safe_daily_limit", 0.0)

        print("\n" + thick)
        print(f"  BUDGET AUDIT — {month_label}")
        print(thick)
        print(f"  Health Signal       : {health_display}")

        # BREACH SUMMARY
        print()
        print("  BREACH SUMMARY")
        print("  " + thin)
        if breach_count == 0:
            print("  No budget breaches this month.")
        else:
            print(f"  Breach count        : {breach_count:>3} transactions")
            print(f"  Total borrowed      : {breach_total:>12,.2f} UAH")

            env_labels = {
                "mandatory":     "From Mandatory      ",
                "non_mandatory": "From Non-Mandatory  ",
                "investments":   "From Investments    ",
                "dreams":        "From Dreams         ",
            }
            for env_key, label in env_labels.items():
                val = breach_by_env.get(env_key, 0.0)
                if val > 0:
                    print(f"  {label}: {val:>12,.2f} UAH")

        # FORECAST
        print()
        print("  FORECAST")
        print("  " + thin)
        print(f"  Total spent (month) : {total_spent:>12,.2f} UAH")
        print(f"  Burn rate / day     : {burn_rate:>12,.2f} UAH")
        print(f"  Days remaining      : {days_remaining:>10} days")

        dtoz = data["days_to_zero"]
        if dtoz == float("inf"):
            days_to_zero_str = "∞ (no spending yet)"
        elif dtoz <= 0:
            days_to_zero_str = "0.0 days (overdrawn)"
        else:
            days_to_zero_str = f"{dtoz:>9.1f} days"
        print(f"  Days to zero        : {days_to_zero_str}")
        print(f"  Safe daily limit    : {safe_daily:>12,.2f} UAH")

        # TOP BREACHES
        if top_breaches:
            print()
            print("  TOP BREACHES")
            print("  " + thin)
            print(f"  {'DATE':<12} {'CATEGORY':<16}  {'AMOUNT':<10}  {'BORROWED'}")
            print(f"  {'-'*11} {'--' * 8}  {'--' * 5}  {'--' * 5}")
            for b in top_breaches:
                date_short = b["date"][:10]
                cat = b["category"]
                amt = b["amount"]
                breach_amt = b["breach"]
                from_envs = ", ".join(k for k in b.get("from", {}).keys())
                borrowed_str = f"{breach_amt:,.2f} {from_envs}"
                print(f"  {date_short:<12} {cat:<16}  {amt:<10,.2f}  {borrowed_str}")

        print(thick + "\n")

    @staticmethod
    def show_sustainability_forecast(data: dict) -> None:
        """Renders per-pool burn rates, days-to-zero, and safe daily limits."""
        W = 65
        thick = "=" * W
        thin = "-" * W

        def fmt_days(val):
            if val == float("inf"):
                return "--"
            return f"{val:.1f}"

        mandatory_burn = data.get("mandatory_burn", 0.0)
        non_mandatory_burn = data.get("non_mandatory_burn", 0.0)
        combined_burn = data.get("combined_burn", 0.0)
        days_to_zero_mandatory = data.get("days_to_zero_mandatory", float("inf"))
        days_to_zero_non_mandatory = data.get("days_to_zero_non_mandatory", float("inf"))
        days_to_zero_combined = data.get("days_to_zero_combined", float("inf"))
        safe_daily_mandatory = data.get("safe_daily_mandatory", 0.0)
        safe_daily_non_mandatory = data.get("safe_daily_non_mandatory", 0.0)
        safe_daily_combined = data.get("safe_daily_combined", 0.0)

        col_pool = 20
        col_burn = 18
        col_days = 14
        col_safe = 18

        print("\n" + thick)
        print("  SUSTAINABILITY FORECAST")
        print(thick)
        print(
            f"  {'Pool':<{col_pool}}"
            f"{'Avg Daily Burn':>{col_burn}}"
            f"{'Days to Zero':>{col_days}}"
            f"{'Safe Daily Limit':>{col_safe}}"
        )
        print("  " + thin)

        rows = [
            ("Mandatory Pool", mandatory_burn, days_to_zero_mandatory, safe_daily_mandatory),
            ("Non-Mandatory Pool", non_mandatory_burn, days_to_zero_non_mandatory, safe_daily_non_mandatory),
            ("Combined", combined_burn, days_to_zero_combined, safe_daily_combined),
        ]
        for pool_label, burn, dtoz, safe in rows:
            dtoz_str = fmt_days(dtoz)
            print(
                f"  {pool_label:<{col_pool}}"
                f"{burn:>{col_burn - 4},.2f} UAH"
                f"{dtoz_str:>{col_days}}"
                f"{safe:>{col_safe - 4},.2f} UAH"
            )

        print("  " + thin)
        print(f"  Safe to spend today: {safe_daily_combined:,.2f} UAH/day (combined)")
        print(thick + "\n")

    @staticmethod
    def show_impact(data: dict) -> None:
        """Renders the pre-spend financial impact analysis with before/after metrics and risk score."""
        W = 65
        thick = "=" * W
        thin = "-" * W

        amount = data["amount"]
        category = data["category"]
        category_valid = data["category_valid"]
        spendable_before = data["spendable_before"]
        spendable_after = data["spendable_after"]
        daily_limit_before = data["daily_limit_before"]
        daily_limit_after = data["daily_limit_after"]
        days_remaining = data["days_remaining"]
        waterfall_triggered = data["waterfall_triggered"]
        risk_score = data["risk_score"]

        # Format category string
        if category is None:
            category_str = "(not specified)"
        elif category_valid:
            category_str = category
        else:
            category_str = f"{category} (unrecognized)"

        print("\n" + thick)
        print("  FINANCIAL IMPACT ANALYSIS")
        print(thick)
        print(f"  Planned expense         : {amount:>12,.2f} UAH")
        print(f"  Category                : {category_str:>20}")
        print(thin)
        print(f"  {'Metric':<20}  {'Before':>15}  {'After':>15}")
        print(thin)
        print(f"  {'Spendable Balance':<20}  {spendable_before:>12,.2f} UAH  {spendable_after:>12,.2f} UAH")
        print(f"  {'Daily Limit':<20}  {daily_limit_before:>12,.2f} UAH  {daily_limit_after:>12,.2f} UAH")

        if days_remaining == 0:
            print(f"  {'Days Remaining':<20}  {days_remaining:>10} days  (no salary cycle found)")
        else:
            print(f"  {'Days Remaining':<20}  {days_remaining:>10} days")

        print(thin)
        print(f"  Risk Score          : [{risk_score}]")
        if waterfall_triggered:
            print("  [!] WARNING: Discipline Waterfall triggered — other envelopes would be drawn.")
        print(thick + "\n")

    @staticmethod
    def show_error(msg): print(f"❌ ERROR: {msg}")

    @staticmethod
    def show_warning(msg):
        print(f"\n  [!] {msg}")

    @staticmethod
    def show_info(msg): print(f"[OK] {msg}")

    @staticmethod
    def display_help():
        """Full command reference with usage examples."""
        print("\n" + "=" * 75)
        print("📖 finQ PROFESSIONAL TERMINAL GUIDE")
        print("=" * 75)
        print(f"{'fq':<22} - 📊 View Dashboard & NBU Rates")
        print(f"{'fq ls [month/all]':<22} - 📜 History with breach markers & month filters")
        print(f"{'fq cs':<22} - 📈 Monthly Category Stats (Expenses)")
        print(f"{'fq ac':<22} - 📂 List Categories")
        print(f"{'fq db <days>':<22} - 📅 Calculate Daily Budget")
        print(f"{'fq b <cat> <amt> [cur]':<22} - 💸 Record Expense (e.g., fq b taxi 80 | fq b taxi 2 usd)")
        print(f"{'fq e <amt> [flags]':<22} - 💰 Record Income (flags: usd, eur, salary)")
        print(f"{'fq rm <id>':<22} - 🗑️  Remove transaction & restore balance")
        print(f"{'fq sync <total>':<22} - 🔄 Proportional balance adjustment")
        print(f"{'fq cc <UAH|USD|EUR>':<22} - 💱 Set base display currency")
        print(f"{'fq audit':<22} - Monthly breach summary and burn rate forecast")
        print(f"{'fq impact <amt> [cat]':<22} - Simulate expense impact on daily budget & risk score")

        print("\n💡 EXAMPLES & USE CASES:")
        print("-" * 75)
        print("1. Salary (USD):              fq e 1500 usd salary")
        print("2. Income (UAH | EUR):        fq e 10000  |  fq e 850 EUR")
        print("3. Quick Expense UAH | USD:   fq b food 150  |  fq b food 4 USD")
        print("4. Planning for 15 days:      fq db 15")
        print("5. Fixing mistake:            fq rm a1b2c3d4")
        print("6. Transaction this month:    fq ls")
        print("7. All Transaction:           fq ls all")
        print("8. Transaction by month:      fq ls 04 or 4")

        print("\n⚠️  PRO TIP: Use 'salary' flag to flush leftovers to 'Dreams'.")
        print("=" * 75 + "\n")