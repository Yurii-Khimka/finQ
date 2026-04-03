## [1.1.2] - 2026-04-03
### Added
- `rm <id>` command: Delete any transaction by ID with automatic balance restoration.
- Help guide updated with the new remove command.

## [1.1.1] - 2026-04-03
### Changed
- Complete project restructuring (Logic moved to `src/`, data to `data/`).
- Database migration: added unique IDs to all transactions.
- Improved UI: dashboard now displays transaction IDs and aligned columns.

### Removed
- `undo` command (deprecated in favor of upcoming `rm` command).

### Added
- Professional README with project philosophy and Roadmap.

## [1.1.0] - 2026-04-03
### Added
- Detailed help guide with currency examples.
- `undo` command to rollback the last transaction.
- Professional README with project philosophy, Roadmap, and AI Context.