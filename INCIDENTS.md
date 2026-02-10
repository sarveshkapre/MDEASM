# Incidents And Learnings

## Entry Schema
- Date
- Trigger
- Impact
- Root Cause
- Fix
- Prevention Rule
- Evidence
- Commit
- Confidence

## Entries

### 2026-02-10
- Trigger: Running `mdeasm assets export ...` with multiple workspaces in a subscription, and no `WORKSPACE_NAME` set.
- Impact: Non-JSON/CSV text could be printed to stdout before the export payload, corrupting pipelines.
- Root Cause: `Workspaces.__init__` calls `get_workspaces()`, which emitted guidance via `print()` (stdout) when no default workspace was selected.
- Fix: Emit the guidance to stderr instead of stdout; add a regression test that asserts stdout remains empty.
- Prevention Rule: Any output emitted before/around CLI machine-readable output must go to stderr, and should be guarded by a stdout-clean test.
- Evidence: `source .venv/bin/activate && ruff check . && pytest` -> pass.
- Commit: b937478
- Confidence: high
