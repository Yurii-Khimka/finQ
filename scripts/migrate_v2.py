import csv
import os

def migrate():
    history_path = "data/history.csv"
    temp_path = "data/history_temp.csv"
    
    if not os.path.exists(history_path):
        print("CSV file not found. Nothing to migrate.")
        return

    with open(history_path, 'r', encoding='utf-8') as f_in, \
         open(temp_path, 'w', newline='', encoding='utf-8') as f_out:
        
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        for row in reader:
            if not row: continue
            # Якщо в рядку вже 7 або більше колонок — пропускаємо
            if len(row) < 7:
                row.append("OK")
            writer.writerow(row)
            
    os.replace(temp_path, history_path)
    print("✅ Migration complete: history.csv updated to 7 columns.")

if __name__ == "__main__":
    migrate()