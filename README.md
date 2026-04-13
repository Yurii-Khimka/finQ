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

| Command           | Description                                          |
|-------------------|------------------------------------------------------|
| `fq cs`           | Monthly category stats (current month)               |
| `fq cs all`       | Category stats for all time                          |
| `fq cs [month]`   | Category stats for specific month (e.g. 04)          |

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

---

# 🧠 AI AGENT MISSION CONTROL & PROJECT CONTEXT

> **This section is the "Source of Truth" for any AI agent assisting in development.**

## 🎯 1. Project Objective & Philosophy
**finQ** is a professional-grade CLI tool for personal finance management based on the **Zero-Based Budgeting** methodology.
- **Philosophy:** Money isn't just "spent"; it is allocated. If a budget is breached, the user must experience the "friction" of seeing exactly where that money was "borrowed" from.
- **Core Principle:** *Discipline Waterfall*. Envelopes have a strict priority. Expenses automatically cascade down the hierarchy if the primary envelope is empty.

## 🏗 2. Technical Architecture
The project follows a modular Python structure:
- `main.py`: Entry point, handles CLI arguments via `sys.argv`.
- `src/core.py`: The financial engine (calculations, CSV/JSON I/O, NBU API integration).
- `src/ui.py`: Terminal interface (tables, colors, scanning-optimized formatting).
- `data/`: Persistent storage (JSON for balances/categories, CSV for transaction history).

## 📊 3. Data Schema (The 7-Column Standard)
All analytics and the `remove_transaction` (undo) feature rely on a strict 7-column CSV structure in `history.csv`:
1. `ID`: Unique 8-character transaction hash.
2. `DATE`: Format `%Y-%m-%d %H:%M` (No seconds).
3. `TYPE`: `INCOME`, `EXPENSE`, or `SYNC`.
4. `CATEGORY`: Category name (synced with `categories.json`).
5. `AMOUNT`: Full amount with currency (e.g., `100.00 UAH`).
6. `ENVELOPE`: The "Home" envelope of the category.
7. `DETAILS`: Metadata for Waterfall tracking. 
   - Format: `OK` or a JSON string like `{"lending_envelope": amount_borrowed}`.

## ✅ 4. Implemented Logic
- **Smart Income:** The `salary` flag flushes leftovers from `Mandatory` and `Non-Mandatory` to `Dreams` before redistributing new funds.
- **Waterfall v2.0:** A single history entry is created for an expense, but the actual funds are deducted across envelopes based on availability.
- **Budget Breach:** A virtual accounting logic. During reporting, any "borrowed" amount is attributed to a `Budget Breach` category within the lending envelope's statistics.
- **Currency:** Real-time conversion for USD/EUR via the NBU API.

## 🛠 5. AI Developer Instructions (The Rules)
When working on this project, you **MUST** adhere to these strict rules:
1. **English Only:** All code comments, documentation, and logic descriptions provided in the code MUST be in English.
2. **No Bloatware:** Do not add features (comments, tags, GUI elements) unless explicitly requested. Maintain a "Professional Terminal" aesthetic.
3. **Backward Compatibility:** Any logic change must not break the `rm` (remove transaction) or `fq cs` (stats) commands.
4. **Convention over Configuration:** Use existing patterns (e.g., if no `salary` flag is present, treat income as a standard balance top-up).
5. **Git Workflow:** Always suggest `gh issue develop <ID>` and standard git commands for committing changes.
6. **Formatting:** Use tables for data output. Follow the envelope hierarchy: `Mandatory` -> `Non-Mandatory` -> `Investments` -> `Dreams`.

## 🔜 6. Planned Features (Roadmap)
- `fq audit`: Analysis of "Budget Breaches" and a "Days to Zero" forecast.
- `fq ls`: Advanced history view with month-based filters and status markers.
- `Burn Rate`: Calculation of average daily spending and safe-limit recommendations.

---