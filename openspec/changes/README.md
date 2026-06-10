# OpenSpec — Active Changes

This directory holds in-flight changes for the pruebaMinimax project.

Each change lives in its own folder using kebab-case naming
(e.g. `2026-06-10-define-plate-rule-spec/`).

A change folder contains:

- `proposal.md` — why, scope, and approach.
- `tasks.md` — implementation work units.
- `design.md` — technical design (if needed).
- `specs/<capability>/spec.md` — delta specs.
- `README.md` — change index (optional).

When a change is verified, the `sdd-archive` phase syncs its delta specs
into `openspec/specs/` and moves the change folder into `archive/`.

## archive/

Holds completed changes for traceability. Kept in git history.
