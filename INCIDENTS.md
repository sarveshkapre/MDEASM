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

### 2026-02-11
- Trigger: Code-review sweep of control-plane helper paths during autonomous maintenance cycle 2.
- Impact: `create_workspace()` could fail with `no region` even when `EASM_REGION` was valid, blocking workspace provisioning automation.
- Root Cause: Region fallback and region validation logic were combined in a way that always raised after fallback assignment.
- Fix: Split fallback (`if not region`) from validation (`if region not in _easm_regions`) and add a regression test.
- Prevention Rule: For env fallback logic, test three explicit paths: argument provided, env fallback provided, and both missing.
- Evidence: `source .venv/bin/activate && pytest -q` -> pass (coverage includes `test_create_workspace_uses_default_region_when_argument_missing`).
- Commit: 97be9c2
- Confidence: high

### 2026-02-10
- Trigger: Running `mdeasm assets export ...` with multiple workspaces in a subscription, and no `WORKSPACE_NAME` set.
- Impact: Non-JSON/CSV text could be printed to stdout before the export payload, corrupting pipelines.
- Root Cause: `Workspaces.__init__` calls `get_workspaces()`, which emitted guidance via `print()` (stdout) when no default workspace was selected.
- Fix: Emit the guidance to stderr instead of stdout; add a regression test that asserts stdout remains empty.
- Prevention Rule: Any output emitted before/around CLI machine-readable output must go to stderr, and should be guarded by a stdout-clean test.
- Evidence: `source .venv/bin/activate && ruff check . && pytest` -> pass.
- Commit: b937478
- Confidence: high
