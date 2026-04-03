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

## 🗺 Roadmap

### 🟢 Phase 1: Foundation (Completed)
- [x] **Core Architecture:** Modular structure with separate logic (`src/`), data (`data/`), and entry point (`main.py`).
- [x] **ID System:** Implementation of unique 8-character IDs for every transaction to ensure data integrity.
- [x] **Transaction Control:** Robust `rm <id>` command with automatic balance restoration and CSV cleanup.
- [x] **Currency Support:** Live NBU API integration for seamless USD/EUR to UAH conversion.
- [x] **Zero-Based Budgeting:** Advanced "Salary" logic with automated leftover flushing (50/30/10/10 distribution).

### 🟡 Phase 2: Navigation & History (In Progress)
- [ ] **Dynamic History (`ls`):**
    - `fq ls` — View transactions for the current month.
    - `fq ls <month>` — Filter history by specific month (e.g., `03` or `march`).
    - `fq ls all` — View full transaction history from the very beginning.
- [ ] **Universal Search (`find`):**
    - Search by **Amount** (e.g., `fq find 500`).
    - Search by **Category or Comment** (e.g., `fq find taxi` or `fq find @dinner`).
    - Combined filters (e.g., Search by amount within a specific month).

### 🟠 Phase 3: Analytics & Intelligence
- [ ] **Monthly Statistics (`stats`):**
    - `fq stats` — Categorized spending breakdown for the current period.
    - `fq stats all` — Lifetime financial summary (Total Earned vs. Total Spent).
- [ ] **Budget Forecasting:**
    - Interactive "Days until next salary" wizard to calculate burn rate.
    - Daily spending limit calculation based on remaining funds and time.
- [ ] **Anomaly Detection:** Alerts for unusually high expenditures in specific categories.

### 🔵 Phase 4: DX & Portability
- [ ] **Auto-Setup:** Automatic creation of the `data/` directory and required files on the first launch.
- [ ] **Data Export:** Tools to backup data or export history to CSV/Excel for external analysis.

---

## 🧠 AI Context (For LLM Collaboration)
*Guidelines for AI assistants working on finQ:*
- **Logic:** Core business logic resides in `core.py`. CLI interactions/UI are in `ui.py`.
- **Data:** Persistent state is in `balances.json`. Full audit log is in `history.csv`.
- **Consistency:** Always validate currency conversions before updating `balances.json`.
- **Tone:** Professional, technical, and data-driven.