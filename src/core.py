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
        amt_str = f"{orig_amt:.2f} {curr} ({amount_uah:.2f} UAH)" if curr != "UAH" else f"{amount_uah:.2f} UAH"
        self._log_transaction("INCOME", "Total", amt_str, "Distributed")
        return balances

    def add_expense(self, category, amount, comment=""):
        """Adds expense with 'Discipline Waterfall' logic."""
        categories = self._load_json(self.categories_path)
        if category not in categories:
            return None, f"Category '{category}' not found."

        home_env = categories[category]
        balances = self._load_json(self.balances_path)
        
        if home_env == "non-mandatory":
            hierarchy = ["non-mandatory", "mandatory", "investments", "dreams"]
        elif home_env == "mandatory":
            hierarchy = ["mandatory", "non-mandatory", "investments", "dreams"]
        elif home_env == "investments":
            hierarchy = ["investments", "non-mandatory", "mandatory", "dreams"]
        else: # dreams
            hierarchy = ["dreams", "investments", "non-mandatory", "mandatory"]

        remaining_to_pay = amount
        transactions_made = []

        for env in hierarchy:
            if remaining_to_pay <= 0:
                break
                
            env_balance = balances.get(env, 0)
            
            if env == hierarchy[-1]:
                spend_from_this = remaining_to_pay
            else:
                spend_from_this = min(env_balance, remaining_to_pay)
                if spend_from_this <= 0: continue 

            balances[env] -= spend_from_this
            remaining_to_pay -= spend_from_this
            
            import uuid
            from datetime import datetime
            t_id = str(uuid.uuid4())[:8]
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            final_comment = comment
            if env != home_env:
                final_comment = f"{comment} [⚠️ Taken from {env.upper()}]".strip()
            
            row = [t_id, date_str, "EXPENSE", category, f"{spend_from_this:.2f}", env, final_comment]
            transactions_made.append(row)

        self._save_json(self.balances_path, balances)
        import csv
        with open(self.history_path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(transactions_made)

        return balances, None

    def flush_leftovers(self):
        balances = self._load_json(self.balances_path)
        total = balances.get("mandatory", 0) + balances.get("non_mandatory", 0)
        if total > 0:
            balances["mandatory"], balances["non_mandatory"] = 0, 0
            balances["dreams"] = balances.get("dreams", 0) + total
            self._save_json(self.balances_path, balances)
        return total

    def get_monthly_stats(self):
        stats = {
            "mandatory": {"total": 0.0, "cats": {}},
            "non_mandatory": {"total": 0.0, "cats": {}}
        }
        current_month = datetime.now().strftime("%Y-%m")
        if not os.path.exists(self.history_path): return stats

        with open(self.history_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 5: continue
                t_id, date, t_type, cat, amt_str, env = row
                if t_type == "EXPENSE" and date.startswith(current_month):
                    try:
                        val = float(amt_str.replace("UAH", "").strip())
                        env_key = env.lower().replace("-", "_")
                        if env_key in stats:
                            stats[env_key]["total"] += val
                            stats[env_key]["cats"][cat] = stats[env_key]["cats"].get(cat, 0) + val
                    except: continue
        return stats

    def _log_transaction(self, t, cat, amt_str, env):
        t_id = str(uuid.uuid4())[:8] 
        with open(self.history_path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([t_id, datetime.now().strftime("%Y-%m-%d %H:%M"), t, cat, amt_str, env])

    def get_last_transactions(self, n=5):
        if not os.path.exists(self.history_path): 
            return []
            
        with open(self.history_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            transactions = [row for row in reader if row]
            return transactions[-n:]

    def remove_transaction(self, t_id):
        """Removes a transaction by ID, restores balances, and updates files."""
        if not os.path.exists(self.history_path):
            return None, "History file not found."

        rows = []
        target_row = None
        
        # 1. Read all rows and separate the target
        with open(self.history_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == t_id:
                    target_row = row
                else:
                    rows.append(row)

        if not target_row:
            return None, f"Transaction {t_id} not found."

        # 2. Parse target data (id, date, type, cat, amt_str, env)
        _, _, t_type, _, amt_str, env_name = target_row
        try:
            # Extract float from "100.00 UAH"
            amount = float(amt_str.split()[0])
        except:
            return None, "Error parsing transaction amount."

        # 3. Reverse Balance Logic
        balances = self._load_json(self.balances_path)
        
        if t_type == "EXPENSE":
            # Return money to the specific envelope
            env_key = env_name.lower().replace("-", "_")
            if env_key in balances:
                balances[env_key] += amount
        
        elif t_type == "INCOME":
            if env_name == "Distributed":
                # Reverse the 50/30/10/10 distribution
                for key, weight in self.income_rules.items():
                    balances[key] -= amount * weight
            else:
                # Reverse direct income
                env_key = env_name.lower().replace("-", "_")
                if env_key in balances:
                    balances[env_key] -= amount

        # 4. Save both files
        self._save_json(self.balances_path, balances)
        with open(self.history_path, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(rows)

        return balances, None

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