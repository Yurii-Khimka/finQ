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

---

## 🗺 Roadmap

### Phase 1: Advanced Management
- [ ] **Transaction Control:** Delete/Edit by ID.
- [ ] **Reporting:** Monthly/Yearly summaries and PDF/CSV exports.
- [ ] **Analytics:** Spend anomaly detection and "Runway" forecasting.

### Phase 2: UX & Onboarding
- [ ] **Wizard Mode:** Interactive step-by-step onboarding for new users.
- [ ] **Currency Alias:** Configurable base currency and quick switching.

### Phase 3: AI & Mobile Vision
- [ ] **AI Assistant (Premium):** LLM-powered context recognition and voice-to-command.
- [ ] **Mobile Terminal UI:** A mobile app that preserves the raw CLI aesthetic and speed.

---

## 🧠 AI Context (For LLM Collaboration)
*Guidelines for AI assistants working on finQ:*
- **Logic:** Core business logic resides in `core.py`. CLI interactions/UI are in `ui.py`.
- **Data:** Persistent state is in `balances.json`. Full audit log is in `history.csv`.
- **Consistency:** Always validate currency conversions before updating `balances.json`.
- **Tone:** Professional, technical, and data-driven.