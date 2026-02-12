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
- Trigger: Attempted scripted rewrite of `CLONE_FEATURES.md` using an invalid `awk` expression during cycle 9 tracker refresh.
- Impact: `CLONE_FEATURES.md` was truncated to zero bytes before feature documentation updates were complete.
- Root Cause: The script used an invalid `awk` variable name and still replaced the destination file without validating generated output.
- Fix: Restored tracker content from `git show HEAD:CLONE_FEATURES.md`, then reapplied tracker edits with bounded `apply_patch` hunks.
- Prevention Rule: For tracker rewrites, avoid one-shot file replacement unless the temp output is validated first (`wc -l > 0`); prefer `apply_patch` for section edits.
- Evidence: `ls -l CLONE_FEATURES.md; wc -l CLONE_FEATURES.md` showed `0` lines before restore, then `git show HEAD:CLONE_FEATURES.md > CLONE_FEATURES.md` restored content successfully.
- Commit: n/a
- Confidence: high

### 2026-02-11
- Trigger: Running helper risk-observation retrieval when summarize returned zero findings.
- Impact: `get_workspace_risk_observations()` could crash with an unbound variable instead of returning cleanly, blocking low/no-risk tenant automations.
- Root Cause: `snapshot_assets` was created only inside the non-empty findings branch, but referenced after the branch unconditionally.
- Fix: Initialize `snapshot_assets` before branch logic, gate completion output on non-empty results, and add regression coverage for empty-findings + `noprint` behavior.
- Prevention Rule: Initialize accumulators before conditional branches and add explicit tests for empty-result paths in any method that consumes paged API summaries.
- Evidence: `source .venv/bin/activate && pytest -q tests/test_mdeasm_helpers.py::test_get_workspace_risk_observations_handles_empty_findings_with_noprint` -> pass.
- Commit: cd9a3e3
- Confidence: high

### 2026-02-11
- Trigger: New secret-redaction tests introduced during cycle 3 failed on first pass.
- Impact: JSON token fields (`"access_token":"..."`) could have remained visible in raised helper exception text, risking credential leakage in logs.
- Root Cause: Initial regex only covered bearer and `key=value` patterns, not quoted JSON key/value payloads.
- Fix: Added explicit JSON token-field redaction and regression tests covering bearer headers, key/value pairs, JSON fields, and signed URL query params.
- Prevention Rule: For any security-redaction change, require a matrix test that includes header, JSON, key/value, and URL query-string token shapes.
- Evidence: `source .venv/bin/activate && pytest -q tests/test_mdeasm_helpers.py::test_redact_sensitive_text_masks_bearer_tokens_fields_and_query_params tests/test_mdeasm_helpers.py::test_workspace_query_helper_redacts_failure_exception_text` -> pass.
- Commit: e955667
- Confidence: high

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

### 2026-02-12T20:00:51Z | Codex execution failure
- Date: 2026-02-12T20:00:51Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-2.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:04:20Z | Codex execution failure
- Date: 2026-02-12T20:04:20Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-3.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:07:49Z | Codex execution failure
- Date: 2026-02-12T20:07:49Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-4.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:11:20Z | Codex execution failure
- Date: 2026-02-12T20:11:20Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-5.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:14:47Z | Codex execution failure
- Date: 2026-02-12T20:14:47Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-6.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:18:23Z | Codex execution failure
- Date: 2026-02-12T20:18:23Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-7.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:21:45Z | Codex execution failure
- Date: 2026-02-12T20:21:45Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-8.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:25:14Z | Codex execution failure
- Date: 2026-02-12T20:25:14Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-9.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:28:50Z | Codex execution failure
- Date: 2026-02-12T20:28:50Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-10.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:32:21Z | Codex execution failure
- Date: 2026-02-12T20:32:21Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-11.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:35:48Z | Codex execution failure
- Date: 2026-02-12T20:35:48Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-12.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:39:18Z | Codex execution failure
- Date: 2026-02-12T20:39:18Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-13.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:42:45Z | Codex execution failure
- Date: 2026-02-12T20:42:45Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-14.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:46:18Z | Codex execution failure
- Date: 2026-02-12T20:46:18Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-15.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:49:47Z | Codex execution failure
- Date: 2026-02-12T20:49:47Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-16.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:53:18Z | Codex execution failure
- Date: 2026-02-12T20:53:18Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-17.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:56:54Z | Codex execution failure
- Date: 2026-02-12T20:56:54Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-18.log
- Commit: pending
- Confidence: medium

### 2026-02-12T21:00:19Z | Codex execution failure
- Date: 2026-02-12T21:00:19Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-19.log
- Commit: pending
- Confidence: medium

### 2026-02-12T21:03:47Z | Codex execution failure
- Date: 2026-02-12T21:03:47Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-20.log
- Commit: pending
- Confidence: medium

### 2026-02-12T21:07:21Z | Codex execution failure
- Date: 2026-02-12T21:07:21Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-21.log
- Commit: pending
- Confidence: medium

### 2026-02-12T21:10:50Z | Codex execution failure
- Date: 2026-02-12T21:10:50Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-MDEASM-cycle-22.log
- Commit: pending
- Confidence: medium
