# --- git-erg --- begin
# Ticket system

This project uses `%erg 0.1` local tickets for work coordination.
The committed CLI is `tickets/erg` (role: traveling; provenance in
`tickets/.erg-assets`) — use it rather than hand-editing where a verb
exists.

## Commands

- `tickets/erg new TITLE` — create a ticket (atomic ID allocation)
- `tickets/erg ready` — list unblocked tickets (`--json` for tooling)
- `tickets/erg close ID REASON` then `tickets/erg archive` — close + file
- `tickets/erg log ID "actor verb detail"` — append a log entry
- `tickets/erg check tickets/` — corpus integrity (duplicate IDs, refs,
  closed-not-archived)
- `tickets/erg migrate tickets/` — idempotent legacy-format fixer

## Notes

- The binary is refreshed by copying from a git-erg release/main build —
  there is no vendored source (`tickets/tools/go/` was removed in the
  2026-06-04 migration, ticket 0407).
- Agent rules live in `tickets/AGENTS.md`.

## Format spec

Run `tickets/erg spec` (print-on-demand; the committed spec file is gone).

# --- git-erg --- end
