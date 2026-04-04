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
        categories = self._load_json(self.categories_path)
        if category not in categories:
            return None, "Category not found."

        home_env = categories[category]
        balances = self._load_json(self.balances_path)
        
        # Define priority based on the category's home envelope
        if home_env == "non_mandatory":
            hierarchy = ["non_mandatory", "mandatory", "investments", "dreams"]
        else:
            hierarchy = ["mandatory", "non_mandatory", "investments", "dreams"]

        remaining = amount
        breach_data = {} # To store virtual "Budget Breaches"

        for env in hierarchy:
            if remaining <= 0:
                break
                
            current_bal = balances.get(env, 0)
            
            # If it's the last envelope (Dreams), allow it to go negative
            if env == hierarchy[-1]:
                take = remaining
            else:
                take = min(current_bal, remaining)
                if take <= 0: continue 

            balances[env] -= take
            remaining -= take
            
            # If we took money from a non-home envelope, record it
            if env != home_env:
                # We normalize names (non-mandatory -> non_mandatory) for JSON
                env_key = env.lower().replace("-", "_")
                breach_data[env_key] = round(take, 2)

        # 7th column logic: "OK" if within budget, else JSON string of breaches
        details = "OK"
        note = None
        if breach_data:
            details = json.dumps(breach_data)
            # Short notification for the user to see in CLI after transaction
            breach_list = [f"{v} UAH from {k.upper()}" for k, v in breach_data.items()]
            note = f"⚠️ Budget Breach: {', '.join(breach_list)}"

        # Save updated balances
        self._save_json(self.balances_path, balances)
        
        # Log AS A SINGLE TRANSACTION (7 columns)
        self._log_transaction("EXPENSE", category, f"{amount:.2f} UAH", home_env, details)

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
        """Aggregates spending per category for the current month. Corrected for 7-column schema."""
        stats = {
        "mandatory": {"total": 0.0, "cats": {}},
        "non_mandatory": {"total": 0.0, "cats": {}}
        }
        current_month = datetime.now().strftime("%Y-%m")
        if not os.path.exists(self.history_path): return stats

        with open(self.history_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 6: continue 
                # Unpacking ID, Date, Type, Cat, Amount, Envelope, Details
                t_id, date, t_type, cat, amt_str, env = row[:6] # Беремо перші 6, ігноруючи решту
                
                if t_type == "EXPENSE" and date.startswith(current_month):
                    try:
                        val = float(amt_str.replace("UAH", "").strip())
                        env_key = env.lower().replace("-", "_")
                        if env_key in stats:
                            stats[env_key]["total"] += val
                            stats[env_key]["cats"][cat] = stats[env_key]["cats"].get(cat, 0) + val
                    except: continue
        return stats

    def _log_transaction(self, t_type, cat, amt_str, env, details="OK"):
        """Logs transaction with the new 7-column standard."""
        import uuid
        from datetime import datetime
        
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

        # Безпечне розпакування: якщо колонок менше 7, ставимо "OK" за замовчуванням
        t_type = target_row[2]
        amt_str = target_row[4]
        home_env = target_row[5]
        details = target_row[6] if len(target_row) > 6 else "OK"
        
        amount = float(amt_str.split()[0])
        balances = self._load_json(self.balances_path)

        if t_type == "EXPENSE":
            if details == "OK":
                balances[home_env] += amount
            else:
                try:
                    breach_data = json.loads(details)
                    borrowed_total = 0
                    for env, borrowed_amt in breach_data.items():
                        if env in balances:
                            balances[env] += borrowed_amt
                            borrowed_total += borrowed_amt
                    balances[home_env] += (amount - borrowed_total)
                except:
                    balances[home_env] += amount

        elif t_type == "INCOME":
            balances[home_env] -= amount

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