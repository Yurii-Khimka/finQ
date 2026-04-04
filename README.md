# 🐚 finQ — Terminal-First Finance OS

**finQ** is a professional-grade personal finance manager designed for power users who live in the CLI. It transforms the way you handle capital by applying a systematic approach directly from your terminal.

The project is built on the **"4 Envelopes"** methodology, ensuring that every cent of your income is automatically allocated toward your future.

---

## 🚀 The "4 Envelopes" Philosophy
Every income entry is automatically split into four strategic "envelopes":
1.  **Mandatory (50%)** — Essential living (rent, groceries, taxes).
2.  **Non-Mandatory (30%)** — Lifestyle, entertainment, and comfort.
3.  **Investments (10%)** — Wealth building (Trading, Stocks, Crypto).
4.  **Dreams (10%)** — Long-term savings and big goals.

---

## 🛠 Current Features (MVP)
- `fq` — Core dashboard (UAH/USD/EUR balances).
- `fq ac` — View categories and envelope mapping.
- `fq b <cat> <amt>` — Quick expense logging.
- `fq e <amt> [flags]` — Income logging with auto-conversion (NBU API) and distribution.
- `fq s <total>` — Account synchronization (manual balance adjustment).
- `fq db <days>` — Daily budget calculation for the remaining period.
- `fq rm <id>` — 🗑️ Remove transaction by ID and restore balance.

---

## 🗺 Roadmap & Future Features

### 🟢 Phase 1: Foundation (Completed)
- [x] **Core Architecture:** Modular structure with separate logic (`src/`), data (`data/`), and entry point (`main.py`).
- [x] **ID System:** Unique 8-character IDs for every transaction.
- [x] **Currency Support:** Live NBU API integration for USD/EUR to UAH conversion.
- [x] **Convention over Configuration:** Income logic (Salary flushes leftovers, Normal income adds to balance).

### 🟡 Phase 2: Data Integrity & Smart Navigation (In Progress)
- [ ] **Schema Migration (7 Columns):** Upgrade CSV structure to include a `STATUS/DETAILS` column for advanced tracking.
- [ ] **Discipline Waterfall v2.0:** - Automatic cross-envelope funding (Mandatory ↔ Non-Mandatory → Invest → Dreams).
    - Single-entry transactions with hidden "funding traces" in metadata.
- [ ] **Advanced History (`ls`):**
    - `fq ls` / `fq ls all` / `fq ls <month>` — Clean table view with "Overrun" markers.
- [ ] **Universal Search (`find`):** Search by amount, category, or status.

### 🟠 Phase 3: Analytics & "Budget Breach" Logic
- [ ] **Smart Monthly Stats (`fq cs`):**
    - Virtual splitting of transactions: Original cost stays in its category.
    - Automated **`Budget Breach`** category: Shows exactly how much was "stolen" from an envelope due to lack of discipline.
- [ ] **Audit Hub (`fq audit`):**
    - List of all budget violations (overruns) for the current period.
    - **Burn Rate Analysis:** Calculation of average daily spending vs. remaining funds.

### 🔵 Phase 4: Intelligence & Forecasting
- [ ] **Predictive Modeling:** - "Days to Zero" forecast: Estimating when the wallet hits 0.00 UAH based on current behavior.
    - Safe Daily Limit recommendations to survive until the next salary.
- [ ] **Anomaly Detection:** Alerts for unusual spending patterns in specific categories.