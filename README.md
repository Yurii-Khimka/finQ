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

---

## 🤖 AI Agent Context & Project Logic (Internal Reference)

> **Role:** You are an expert Python developer and financial architect helping to build **finQ** — a zero-based budgeting CLI tool.

### 🎯 Core Philosophy: "Discipline Waterfall"
- **Waterfall v2.0:** If an envelope is empty, funds are automatically pulled from others in this order: 
  - `Non-Mandatory` ↔ `Mandatory` → `Investments` → `Dreams`.
- **Integrity:** Every transaction remains a **single entry** in the CSV to preserve the "event" reality.
- **Budget Breach:** A virtual category used during analytics. If money is "borrowed" from another envelope, that amount is attributed to `Budget Breach` in the lending envelope's stats.

### 📊 Data Schema (Strict 7-Column Layout)
All logic (including `remove_transaction` and `audit`) depends on this CSV structure:
1. `ID`: Unique 8-char transaction identifier.
2. `DATE`: Format `%Y-%m-%d %H:%M` (No seconds to keep UI clean).
3. `TYPE`: `INCOME`, `EXPENSE`, or `SYNC`.
4. `CATEGORY`: Original category (e.g., `coffee`, `rent`).
5. `AMOUNT`: Full transaction amount (e.g., `200.00 UAH`).
6. `ENVELOPE`: The "home" envelope of the category.
7. `DETAILS`: Metadata for Waterfall splits. 
   - Format: `OK` or `{"lending_envelope": amount_borrowed}`.

### 🛠 Workflow Instructions for AI
When the user provides an **Issue ID** or **Task Name**, follow these rules:
1. **Context Check:** Always verify the 7-column schema in `core.py`.
2. **Logic Check:** Ensure `remove_transaction` reverses the `DETAILS` metadata correctly.
3. **CLI First:** Provide commands for `gh issue develop <ID>` and git workflows.
4. **No Bloat:** Do not add features (like comments) unless explicitly requested. Keep it "Professional Terminal" style.