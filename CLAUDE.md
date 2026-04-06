# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (aliased as `fq` on the host machine)
python3 main.py <command>

# Common commands
python3 main.py              # Dashboard
python3 main.py b <cat> <amt>  # Add expense (e.g., fq b food 150)
python3 main.py e <amt> [usd|eur] [salary]  # Add income
python3 main.py ls [YYYY-MM|all]  # Transaction history
python3 main.py rm <id>     # Remove transaction by 8-char UUID prefix
python3 main.py sync <total>  # Rebalance envelopes to target total
python3 main.py cs           # Monthly stats
python3 main.py db <days>    # Daily budget for next N days

# Migration
python3 scripts/migrate_v2.py  # Upgrade legacy CSV to 7-column format
```

No build step. No external dependencies — standard library only.

## Architecture

Three-layer design with strict separation:

```
main.py → src/core.py → data/{balances.json, categories.json, history.csv}
              ↓
          src/ui.py (display only, never writes data)
```

**`main.py`** — CLI router. Parses `sys.argv`, instantiates `FinanceManager` and `FinanceUI`, calls the appropriate method.

**`src/core.py` (`FinanceManager`)** — All business logic and file I/O.

**`src/ui.py` (`FinanceUI`)** — Terminal rendering only (static methods). Receives data from `core.py`, never reads data files directly.

## Data Schema

**`data/balances.json`** — Four envelope totals:
- `mandatory` (50% of income) — bills, rent, food
- `non_mandatory` (30%) — lifestyle spend
- `investments` (10%)
- `dreams` (10%)

**`data/categories.json`** — ~32 categories, each mapped to one of the four envelopes.

**`data/history.csv`** — 7-column format (never change column order):
```
ID (8-char UUID), DATE (YYYY-MM-DD HH:MM), TYPE (INCOME/EXPENSE/SYNC),
CATEGORY, AMOUNT_UAH, ENVELOPE, DETAILS
```
`DETAILS` is either `"OK"` or a JSON string encoding breach metadata (e.g., `{"non_mandatory": 50.0}`).

## Key Logic

### Discipline Waterfall (expense flow)
When `add_expense(category, amount)` runs:
1. The category's home envelope (`home_env`) is charged first — always, even if non-mandatory is the category's envelope.
2. If `home_env` balance is insufficient, the deficit cascades down the fixed hierarchy: `mandatory → non_mandatory → investments → dreams`.
3. Any "borrowed" amounts from other envelopes are recorded in the `DETAILS` column as JSON.

### Transaction Removal
`remove_transaction(t_id)` reads the `DETAILS` JSON of the original transaction and reverses each envelope charge exactly — it does not simply add back the full amount to one envelope.

### Income / Salary Flag
`add_income` with the `salary` flag calls `flush_leftovers()` first, which moves remaining `mandatory` and `non_mandatory` balances into `dreams` before distributing new income at the 50/30/10/10 split.

### Currency Conversion
`get_rate(currency)` fetches live UAH rates from the NBU public API (no API key needed). The dashboard displays all balances in UAH, USD, and EUR simultaneously.

## Development Conventions

- All code and comments must be in **English**.
- No external libraries — keep it standard-library only.
- Backward compatibility with existing `history.csv` and JSON data files is required; never change column order or key names.
- Git workflow: branch off `main`, open PRs via `gh pr create`, reference issue numbers in commit messages (`Closes #N`).
- The user communicates in Ukrainian; code and comments stay in English.
