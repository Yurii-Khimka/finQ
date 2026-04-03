import json
import csv
import os
import urllib.request
import ssl
import uuid
from datetime import datetime

class FinanceManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.balances_path = os.path.join(base_dir, "balances.json")
        self.categories_path = os.path.join(base_dir, "categories.json")
        self.history_path = os.path.join(base_dir, "history.csv")

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

    def add_expense(self, category, amount):
        categories = self._load_json(self.categories_path)
        balances = self._load_json(self.balances_path)
        cat = category.lower()
        if cat not in categories: return None, balances
        env = categories[cat]
        balances[env] -= amount
        self._save_json(self.balances_path, balances)
        self._log_transaction("EXPENSE", cat, f"{amount:.2f} UAH", env)
        return env, balances

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
                date, t_type, cat, amt_str, env = row
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
        with open(self.history_path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), t, cat, amt_str, env])

    def get_last_transactions(self, n=7):
        if not os.path.exists(self.history_path): return []
        with open(self.history_path, 'r', encoding='utf-8') as f:
            return list(csv.reader(f))[-n:]