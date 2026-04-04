class FinanceUI:
    @staticmethod
    def display_summary(balances, usd_rate=None, eur_rate=None, last_transactions=None):
        def conv(val, rate): return val / rate if rate else 0

        print("\n" + "=" * 78)
        print(f"{'ENVELOPE':<18} | {'UAH':>14} | {'USD':>12} | {'EUR':>12}")
        print("-" * 78)

        keys = [("Mandatory", "mandatory"), ("Non-Mandatory", "non_mandatory"), 
                ("Investments", "investments"), ("Dreams", "dreams")]

        for label, key in keys:
            val = balances.get(key, 0)
            print(f"{label:<18} | {val:>14.2f} | {conv(val, usd_rate):>12.2f} | {conv(val, eur_rate):>12.2f}")

        total = sum(balances.values())
        spendable = balances.get("mandatory", 0) + balances.get("non_mandatory", 0)

        print("-" * 78)
        print(f"{'TOTAL ACCOUNT':<18} | {total:>14.2f} | {conv(total, usd_rate):>12.2f} | {conv(total, eur_rate):>12.2f}")
        print(f"{'SPENDABLE NOW':<18} | {spendable:>14.2f} | {conv(spendable, usd_rate):>12.2f} | {conv(spendable, eur_rate):>12.2f}")
        print("=" * 78)

        if last_transactions:
            print("\n🕒 RECENT ACTIVITY:")
            print("\n" + "-" * 82)
            print(f"{'ID':<9} | {'DATE':<16} | {'TYPE':<8} | {'CAT':<16} | {'AMOUNT':>12}")
            print("-" * 82)
            
            for row in last_transactions:
                # Тепер ми очікуємо 6 колонок: id, date, type, cat, amount, env
                if len(row) >= 5:
                    # Розпаковуємо з урахуванням того, що ID тепер перший
                    t_id = row[0]
                    date = row[1]
                    t_type = row[2]
                    cat = row[3]
                    amt_str = row[4]
                    
                    # Вирівнюємо колонки: ID(9), DATE(16), TYPE(8), CAT(12), AMOUNT(12)
                    print(f"{t_id:<9} | {date:<16} | {t_type:<8} | {cat:<16} | {amt_str:>12}")
            
            print("-" * 82 + "\n")

    @staticmethod
    def display_stats(stats):
        """Звіт 'fq cs' у стилі головного дашборду з пунктирними лініями."""
        print("\n📊 MONTHLY CATEGORY SUMMARY")
        
        for env_key in ["mandatory", "non_mandatory"]:
            data = stats[env_key]
            if not data["cats"]: continue
            
            title = env_key.upper().replace("_", "-")
            print("\n" + "-" * 55)
            print(f"📂 {title}")
            print("-" * 55)
            
            # Сортування: дорожчі категорії зверху
            sorted_cats = sorted(data["cats"].items(), key=lambda x: x[1], reverse=True)
            for cat, amt in sorted_cats:
                print(f"{cat:<25} | {amt:>18.2f} UAH")
            
            print("-" * 55)
            print(f"{'TOTAL ' + title:<25} | {data['total']:>18.2f} UAH")
            print("-" * 55)
        print("\n")

    @staticmethod
    def display_daily_budget(mand, non_mand, days, usd, eur):
        def conv(val, rate): return val / rate if rate else 0
        d_mand, d_non = mand / days, non_mand / days
        d_total = (mand + non_mand) / days

        print("\n" + f"📅 DAILY LIMITS (For {days} days)")
        print("-" * 65)
        print(f"{'TYPE':<18} | {'UAH':>14} | {'USD':>12} | {'EUR':>12}")
        print("-" * 65)
        print(f"{'Mandatory':<18} | {d_mand:>14.2f} | {conv(d_mand, usd):>12.2f} | {conv(d_mand, eur):>12.2f}")
        print(f"{'Non-Mandatory':<18} | {d_non:>14.2f} | {conv(d_non, usd):>12.2f} | {conv(d_non, eur):>12.2f}")
        print("-" * 65)
        print(f"{'DAILY TOTAL':<18} | {d_total:>14.2f} | {conv(d_total, usd):>12.2f} | {conv(d_total, eur):>12.2f}")
        print("-" * 65 + "\n")

    @staticmethod
    def display_categories(sorted_categories):
        """Displays a compact table of all categories."""
        if not sorted_categories:
            print("⚠️ No categories found.")
            return

        # Заголовки таблиці
        header = f"| {'#':^3} | {'CATEGORY':<20} | {'ENVELOPE':<15} |"
        separator = "-" * len(header)

        print("\n" + separator)
        print(header)
        print(separator)

        for i, (cat, env) in enumerate(sorted_categories, 1):
            # Використовуємо колір або верхній регістр для конвертів, щоб вони виділялися
            env_display = env.upper()
            print(f"| {i:^3} | {cat:<20} | {env_display:<15} |")

        print(separator)
        print(f"Total: {len(sorted_categories)} categories. Use 'fq b <cat> <amt>'\n")

    @staticmethod
    def show_error(msg): print(f"❌ ERROR: {msg}")

    @staticmethod
    def display_help():
        print("\n" + "=" * 75)
        print("📖 finQ PROFESSIONAL TERMINAL GUIDE")
        print("=" * 75)
        print(f"{'fq':<22} - 📊 View Dashboard & NBU Rates")
        print(f"{'fq cs':<22} - 📈 Monthly Category Stats (Expenses)")
        print(f"{'fq ac':<22} - 📂 List Categories")
        print(f"{'fq db <days>':<22} - 📅 Calculate Daily Budget")
        print(f"{'fq b <cat> <amt>':<22} - 💸 Record Expense (e.g., fq b taxi 80)")
        print(f"{'fq e <amt> [flags]':<22} - 💰 Record Income (flags: usd, eur, salary)")
        print(f"{'fq rm <id>':<22} - 🗑️  Remove transaction by ID and restore balance")
        
        print("\n💡 EXAMPLES & USE CASES:")
        print("-" * 75)
        print("1. Salary (USD):              fq e 1500 usd salary (flushes leftovers & refills envelopes)")
        print("2. Extra Income (UAH):        fq e 20000 (adds to current balances without flushing)")
        print("3. Bought Coffee:             fq b food 65")
        print("4. Check what I can spend:    fq db 10 (budget for 10 days)")
        print("5. Delete transaction:        fq rm <id> (removes record and restores balance)")
        
        print("\n⚠️  PRO TIP: Use 'salary' flag to flush old 'Non-Mandatory' leftovers.")
        print("=" * 75 + "\n")