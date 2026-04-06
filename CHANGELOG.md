## [1.3.0] - 2026-04-06

### 🚀 Added
- **Base Currency Command (`fq cc`)**: Set the app's primary display currency to UAH, USD, or EUR. The choice persists across restarts via a new `data/config.json` file.
- **Adaptive Dashboard Layout**: When USD or EUR is selected as the base currency, the dashboard and `fq db` collapse from a 3-column grid to a focused single-currency view. When UAH is selected, the full UAH | USD | EUR grid is preserved.
- **Rate Unavailable Fallback**: If live exchange rates cannot be fetched and a non-UAH base currency is active, the dashboard falls back to UAH display with a clear `[!] Rate unavailable` warning instead of silently showing zeros.

### 🛠️ Fixed
- **`show_info` UI layer compliance**: The `fq cc` confirmation message now routes through `ui.show_info()` rather than a raw `print()`, keeping output consistent with the three-layer architecture.

---

## [1.2.0] - 2026-04-04

### 🚀 Added
- **Advanced History View (`fq ls`)**: A comprehensive transaction viewer that defaults to the current month but allows filtering by specific months or viewing the entire history.
- **7-Column CSV Standard**: Upgraded the `history.csv` architecture to include a `details` column for granular transaction metadata.
- **JSON Metadata Support**: Integrated JSON-formatted "Budget Breach" logs to track exactly how much was "borrowed" from other envelopes during the waterfall process.
- **Automated Migration Tool**: Included `migrate_v2.py` to seamlessly upgrade existing user data to the new 7-column standard without manual editing.
- **Smart Transaction Reversal**: The `fq rm <id>` command now parses JSON metadata to restore exact funds to their original envelopes (e.g., returning "borrowed" money to Mandatory if a Non-Mandatory expense is deleted).

### 🛠️ Fixed
- **`fq cs` Unpacking Error**: Resolved the `ValueError` crash by implementing safe row slicing (`row[:6]`) to accommodate the new 7-column structure.
- **History Display Stability**: Updated the UI to gracefully handle legacy 5 or 6-column records using fallback logic.
- **Category Sorting**: Fixed the `fq ac` display order to strictly follow the financial priority: Mandatory -> Non-Mandatory -> Investments -> Dreams.

### 🔄 Changed
- **Discipline Waterfall v2.0**: Refined the automatic cascading logic to ensure expenses flow across envelopes in a strictly prioritized hierarchy when the primary envelope is empty.
- **Professional UI Layout**: Enhanced the dashboard and category tables with fixed-width columns and dashed separators for better readability in the terminal.
- **Breach Indicators**: Added a visual `[!]` status mark in the history view for transactions that triggered a budget breach.

---

## [1.1.3] - 2026-04-04
### Fixed
- `fq ac` command: Displays a compact, sorted table of all categories.
- "Discipline Waterfall" logic: Expenses now automatically cascade across envelopes if funds are insufficient (Non-Mandatory -> Mandatory -> Investments -> Dreams).
- Automated logs: Added `[⚠️ Taken from ENV]` markers in transaction comments when the waterfall logic is triggered.
- Category sorting priority: Strictly enforced order (Mandatory -> Non-Mandatory -> Investments -> Dreams).
- Add new expense

---

## [1.1.2] - 2026-04-03
### Added
- `rm <id>` command: Delete any transaction by ID with automatic balance restoration.
- Help guide updated with the new remove command.

---

## [1.1.1] - 2026-04-03
### Changed
- Complete project restructuring (Logic moved to `src/`, data to `data/`).
- Database migration: added unique IDs to all transactions.
- Improved UI: dashboard now displays transaction IDs and aligned columns.

### Removed
- `undo` command (deprecated in favor of upcoming `rm` command).

### Added
- Professional README with project philosophy and Roadmap.

---

## [1.1.0] - 2026-04-03
### Added
- Detailed help guide with currency examples.
- `undo` command to rollback the last transaction.
- Professional README with project philosophy, Roadmap, and AI Context.