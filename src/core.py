import json
import csv
import os
import urllib.request
import ssl
import uuid
from datetime import datetime

class FinanceManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.balances_path = os.path.join(data_dir, "balances.json")
        self.categories_path = os.path.join(data_dir, "categories.json")
        self.history_path = os.path.join(data_dir, "history.csv")
        self.config_path = os.path.join(data_dir, "config.json")

        self.income_rules = {
            "mandatory": 0.50,
            "non_mandatory": 0.30,
            "investments": 0.10,
            "dreams": 0.10
        }

    def _load_json(self, path):
        if not os.path.exists(path): return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_rate(self, currency="USD"):
        try:
            context = ssl._create_unverified_context()
            url = f"https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode={currency.upper()}&json"
            with urllib.request.urlopen(url, context=context) as response:
                data = json.loads(response.read().decode())
                return data[0]['rate']
        except: return None

    def sync_balance(self, target_total):
        balances = self._load_json(self.balances_path)
        current_total = sum(balances.values())
        if current_total <= 0: return balances
        ratio = target_total / current_total
        for env in balances:
            balances[env] = balances[env] * ratio
        self._save_json(self.balances_path, balances)
        self._log_transaction("SYNC", "Adjustment", f"{target_total - current_total:.2f} UAH", "Balance Sync")
        return balances

    def add_income(self, amount_uah, curr="UAH", orig_amt=None):
        balances = self._load_json(self.balances_path)
        for env, pct in self.income_rules.items():
            balances[env] = balances.get(env, 0) + (amount_uah * pct)
        self._save_json(self.balances_path, balances)
        # FX income: encode original amount in the AMOUNT column; DETAILS is always "OK"
        if curr != "UAH" and orig_amt is not None:
            amt_str = f"{orig_amt:.2f} {curr} ({amount_uah:.2f} UAH)"
        else:
            amt_str = f"{amount_uah:.2f} UAH"
        self._log_transaction("INCOME", "Total", amt_str, "Distributed", "OK")
        return balances

    def add_expense(self, category, amount, currency="UAH"):
        """
        Processes expense with a fixed Waterfall logic.
        The Home Envelope is ALWAYS prioritized first.
        If currency != "UAH", converts amount to UAH via live NBU rate before
        running the waterfall. DETAILS contains breach data only; FX info is
        not stored (UAH equivalent is what the waterfall operates on).
        """
        categories = self._load_json(self.categories_path)
        if category not in categories:
            return None, "Category not found."

        # Convert to UAH if a foreign currency is supplied
        if currency != "UAH":
            rate = self.get_rate(currency)
            if rate is None:
                return None, f"Could not fetch rate for {currency}. Transaction aborted."
            amount_uah = amount * rate
        else:
            amount_uah = amount
            rate = None

        home_env = categories[category]
        balances = self._load_json(self.balances_path)

        # 1. Define the absolute priority order
        base_priority = ["mandatory", "non_mandatory", "investments", "dreams"]

        # 2. Reorganize: Put home_env first, then the rest in base order
        hierarchy = [home_env]
        for env in base_priority:
            if env not in hierarchy:
                hierarchy.append(env)

        remaining = amount_uah
        breach_data = {}

        for env in hierarchy:
            if remaining <= 0:
                break
            current_bal = balances.get(env, 0)

            if env == "dreams":  # Final buffer
                take = remaining
            else:
                take = min(current_bal, remaining)
                if take <= 0:
                    continue

            balances[env] -= take
            remaining -= take

            # Record as breach ONLY if we take from an envelope that IS NOT the home one
            if env != home_env:
                breach_data[env.lower().replace("-", "_")] = round(take, 2)

        # DETAILS contains breach data only; FX metadata lives in the AMOUNT column
        details = json.dumps(breach_data) if breach_data else "OK"

        note = None
        if breach_data:
            breach_list = [f"{v} UAH from {k.upper()}" for k, v in breach_data.items()]
            note = f"⚠️ Budget Breach: {', '.join(breach_list)}"

        self._save_json(self.balances_path, balances)
        self._log_transaction("EXPENSE", category, f"{amount_uah:.2f} UAH", home_env, details)
        return balances, note

    def flush_leftovers(self):
        balances = self._load_json(self.balances_path)
        total = balances.get("mandatory", 0) + balances.get("non_mandatory", 0)
        if total > 0:
            balances["mandatory"], balances["non_mandatory"] = 0, 0
            balances["dreams"] = balances.get("dreams", 0) + total
            self._save_json(self.balances_path, balances)
        return total

    def get_monthly_stats(self):
        """Aggregates spending per category for the current month. Breach-aware virtual splitting across all 4 envelopes."""
        stats = {
            "mandatory": {"total": 0.0, "cats": {}},
            "non_mandatory": {"total": 0.0, "cats": {}},
            "investments": {"total": 0.0, "cats": {}},
            "dreams": {"total": 0.0, "cats": {}}
        }
        current_month = datetime.now().strftime("%Y-%m")
        if not os.path.exists(self.history_path): return stats

        with open(self.history_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 6: continue
                t_id, date, t_type, cat, amt_str, env = row[:6]

                if t_type == "EXPENSE" and date.startswith(current_month):
                    # Parse UAH amount — handle FX rows: "1500.00 USD (41250.00 UAH)"
                    try:
                        if "(" in amt_str:
                            amount = float(amt_str.split("(")[1].split()[0])
                        else:
                            amount = float(amt_str.split()[0])
                    except (ValueError, IndexError):
                        continue

                    env_key = env.lower().replace("-", "_")
                    details_str = row[6] if len(row) > 6 else "OK"

                    if details_str == "OK":
                        # No breach — full amount to home envelope category
                        stats[env_key]["cats"][cat] = stats[env_key]["cats"].get(cat, 0) + amount
                        stats[env_key]["total"] += amount
                    else:
                        try:
                            breach_data = json.loads(details_str)
                            valid_envelopes = {"mandatory", "non_mandatory", "investments", "dreams"}
                            borrowed_total = sum(v for k, v in breach_data.items() if k in valid_envelopes)
                            home_contribution = max(amount - borrowed_total, 0.0)

                            # Home envelope gets only what it actually covered
                            stats[env_key]["cats"][cat] = stats[env_key]["cats"].get(cat, 0) + home_contribution
                            stats[env_key]["total"] += home_contribution

                            # Each breached envelope gets a "Budget Breach" virtual row
                            for breach_env, breach_amt in breach_data.items():
                                if breach_env in valid_envelopes and breach_env in stats:
                                    stats[breach_env]["cats"]["Budget Breach"] = stats[breach_env]["cats"].get("Budget Breach", 0) + breach_amt
                                    stats[breach_env]["total"] += breach_amt
                        except (ValueError, json.JSONDecodeError):
                            # Fallback: treat as OK
                            stats[env_key]["cats"][cat] = stats[env_key]["cats"].get(cat, 0) + amount
                            stats[env_key]["total"] += amount
        return stats

    def get_audit_data(self) -> dict:
        """Returns breach summary and burn rate forecast for the current month."""
        from datetime import datetime

        now = datetime.now()
        current_month = now.strftime("%Y-%m")

        balances = self._load_json(self.balances_path)
        history = self.get_history()

        breach_count = 0
        breach_total_uah = 0.0
        breach_by_envelope = {
            "mandatory": 0.0,
            "non_mandatory": 0.0,
            "investments": 0.0,
            "dreams": 0.0,
        }
        top_breaches_raw = []
        total_spent_uah = 0.0

        for row in history:
            if not row or len(row) < 6:
                continue
            t_id, date, t_type, cat, amt_str, env = row[:6]
            details = row[6] if len(row) > 6 else "OK"

            if t_type != "EXPENSE" or not date.startswith(current_month):
                continue

            # Parse UAH amount — handle FX rows like "1500.00 USD (41250.00 UAH)"
            try:
                if "(" in amt_str:
                    amount = float(amt_str.split("(")[1].split()[0])
                else:
                    amount = float(amt_str.split()[0])
            except (ValueError, IndexError):
                continue

            total_spent_uah += amount

            if details != "OK":
                try:
                    breach_data = json.loads(details)
                    valid_envelopes = {"mandatory", "non_mandatory", "investments", "dreams"}
                    row_breach_total = 0.0
                    for env_key, breach_amt in breach_data.items():
                        if env_key in valid_envelopes:
                            amt = max(breach_amt, 0.0)
                            breach_by_envelope[env_key] += amt
                            breach_total_uah += amt
                            row_breach_total += amt
                    if row_breach_total > 0:
                        breach_count += 1
                        top_breaches_raw.append({
                            "date": date,
                            "category": cat,
                            "amount": amount,
                            "breach": row_breach_total,
                            "from": breach_data,
                        })
                except (ValueError, json.JSONDecodeError):
                    pass  # Malformed DETAILS — treat as OK

        # Burn rate and forecast
        days_elapsed = max(now.day, 1)
        burn_rate_daily = total_spent_uah / days_elapsed

        # Days in current month — handle December rollover
        year, month = now.year, now.month
        if month == 12:
            next_month_first = datetime(year + 1, 1, 1)
        else:
            next_month_first = datetime(year, month + 1, 1)
        days_in_month = (next_month_first - datetime(year, month, 1)).days
        days_remaining = max(days_in_month - now.day, 0)

        spendable_balance = balances.get("mandatory", 0.0) + balances.get("non_mandatory", 0.0)

        if burn_rate_daily == 0:
            days_to_zero = float("inf")
        else:
            days_to_zero = spendable_balance / burn_rate_daily

        safe_daily_limit = spendable_balance / days_remaining if days_remaining > 0 else 0.0

        # Health signal
        if burn_rate_daily == 0 or days_to_zero >= days_remaining:
            health_signal = "healthy"
        elif days_to_zero >= days_remaining * 0.5:
            health_signal = "warning"
        else:
            health_signal = "critical"

        # Sort top breaches by breach amount desc, take top 5
        top_breaches = sorted(top_breaches_raw, key=lambda x: x["breach"], reverse=True)[:5]

        return {
            "breach_count": breach_count,
            "breach_total_uah": breach_total_uah,
            "breach_by_envelope": breach_by_envelope,
            "top_breaches": top_breaches,
            "total_spent_uah": total_spent_uah,
            "burn_rate_daily": burn_rate_daily,
            "days_remaining": days_remaining,
            "days_to_zero": days_to_zero,
            "safe_daily_limit": safe_daily_limit,
            "spendable_balance": spendable_balance,
            "health_signal": health_signal,
        }

    def _log_transaction(self, t_type, cat, amt_str, env, details="OK"):
        """Logs transaction with the new 7-column standard."""
        t_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        with open(self.history_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([t_id, date_str, t_type, cat, amt_str, env, details])

    def get_last_transactions(self, n=5):
        if not os.path.exists(self.history_path): 
            return []
            
        with open(self.history_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            transactions = [row for row in reader if row]
            return transactions[-n:]

    def get_filtered_history(self, filter_val="all"):
        """
        Retrieves history with advanced filtering.
        Default is 'all' or specific month (e.g. '04').
        """
        history = self.get_history()
        if not history: return []

        if filter_val == "all":
            return history

        # Filtering by month (format -MM-)
        # This covers cases like '04' or '4' (via zfill)
        month_str = f"-{filter_val.zfill(2)}-"
        return [row for row in history if month_str in row[1]]

    def remove_transaction(self, t_id):
        history = self.get_history()
        target_row = next((row for row in history if row[0] == t_id), None)
        
        if not target_row:
            return None, f"Transaction ID '{t_id}' not found."

        # Safe unpacking: if fewer than 7 columns, default to "OK"
        t_type = target_row[2]
        amt_str = target_row[4]
        home_env = target_row[5]
        details = target_row[6] if len(target_row) > 6 else "OK"
        
        # Parse UAH amount — handle legacy rows that stored "1000.00 USD (41500.00 UAH)"
        if "(" in amt_str:
            amount = float(amt_str.split("(")[1].split()[0])
        else:
            amount = float(amt_str.split()[0])

        balances = self._load_json(self.balances_path)

        if t_type == "EXPENSE":
            if details == "OK":
                balances[home_env] += amount
            else:
                try:
                    details_dict = json.loads(details)
                    # Only envelope keys are valid reversal targets;
                    # metadata keys like "original" and "rate" are skipped.
                    valid_envelopes = {"mandatory", "non_mandatory", "investments", "dreams"}
                    borrowed_total = 0
                    for env, borrowed_amt in details_dict.items():
                        if env in valid_envelopes and env in balances:
                            balances[env] += borrowed_amt
                            borrowed_total += borrowed_amt
                    balances[home_env] += (amount - borrowed_total)
                except:
                    balances[home_env] += amount

        elif t_type == "INCOME":
            # Reverse the 50/30/10/10 split across all four envelopes
            for env, pct in self.income_rules.items():
                balances[env] = balances.get(env, 0) - (amount * pct)

        new_history = [row for row in history if row[0] != t_id]
        with open(self.history_path, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(new_history)
            
        self._save_json(self.balances_path, balances)
        return balances, None

    def get_history(self):
        """Reads and returns all transactions from the history CSV file."""
        if not os.path.exists(self.history_path):
            return []
        with open(self.history_path, 'r', encoding='utf-8') as f:
            return list(csv.reader(f))

    def get_sorted_categories(self):
        """Returns categories sorted by strict financial priority."""
        categories = self._load_json(self.categories_path)

        priority = {
            "mandatory": 1,
            "non_mandatory": 2,
            "investments": 3,
            "dreams": 4
        }

        return sorted(
            categories.items(),
            key=lambda x: (priority.get(x[1].lower(), 99), x[0])
        )

    def load_config(self):
        """Returns the app config dict. Falls back to defaults if file is missing or corrupt."""
        defaults = {"base_currency": "UAH"}
        if not os.path.exists(self.config_path):
            return defaults
        try:
            config = self._load_json(self.config_path)
            if "base_currency" not in config:
                config["base_currency"] = "UAH"
            return config
        except json.JSONDecodeError:
            return defaults

    def save_config(self, config):
        """Persists the config dict to data/config.json."""
        self._save_json(self.config_path, config)

    def set_base_currency(self, currency):
        """
        Validates and saves the requested base currency.
        Returns (config, None) on success or (None, error_msg) on failure.
        """
        valid = {"UAH", "USD", "EUR"}
        upper = currency.upper()
        if upper not in valid:
            return None, f"Invalid currency '{currency}'. Choose from: UAH, USD, EUR."
        config = self.load_config()
        config["base_currency"] = upper
        self.save_config(config)
        return config, None