# Project Memory

## Objective
- Keep MDEASM production-ready. Current focus: MDEASM. Find the highest-impact pending work, implement it, test it, and push to main.

## Architecture Snapshot

## Open Problems

## Recent Decisions
- Template: YYYY-MM-DD | Decision | Why | Evidence (tests/logs) | Commit | Confidence (high/medium/low) | Trust (trusted/untrusted)
- 2026-02-11 | Refresh autonomous trackers (`CLONE_FEATURES.md`, `PROJECT_MEMORY.md`, `INCIDENTS.md`, `AGENTS.md`) for cycle 2 closeout | Keep backlog, implemented items, incident learnings, and mutable facts aligned with shipped behavior and CI evidence | Tracker files updated with scored backlog, implemented entries, market-scan gap map, and verification evidence | b4ad16f | high | trusted
- 2026-02-11 | Add client export resume checkpoints (`--resume-from`, `--checkpoint-out`) and deterministic ordering (`--orderby`) | Long-running ASM exports need reliable continuation semantics and stable ordering to be automation-safe | `source .venv/bin/activate && ruff check .` (pass); `source .venv/bin/activate && pytest -q` (pass); `source .venv/bin/activate && python -m compileall API` (pass) | 97be9c2 | high | trusted
- 2026-02-11 | Harden asset list compatibility for preview payload drift (`content` vs `value`) and fix `create_workspace` + `create_facet_filter(asset_id=...)` reliability bugs | Preview APIs can drift and helper reliability bugs can block core workflows despite valid configuration | Added regression tests in `tests/test_mdeasm_helpers.py`; full lint/test/compile pass | 97be9c2 | high | trusted
- 2026-02-11 | Prioritize resume/orderby parity from bounded market scan | Microsoft Defender EASM plus peer ASM APIs document cursor/mark + ordering semantics, making resumable deterministic exports baseline expectation | Microsoft Learn assets/tasks references and Censys/Shodan pagination docs captured in `CLONE_FEATURES.md` | n/a | medium | untrusted
- 2026-02-11 | Refresh autonomous trackers (`CLONE_FEATURES.md`, `PROJECT_MEMORY.md`, `AGENTS.md`) after delivery | Keep backlog, decisions, and mutable repo facts aligned with shipped behavior and verification evidence | Tracker files updated with delivered items, remaining backlog, CI evidence, and mutable fact timestamp | 4f6db34 | high | trusted
- 2026-02-11 | Add server-side export task mode (`mdeasm assets export --mode server`) with optional wait/download flow | Large inventories are better handled by async server-side exports; this reduces client memory pressure and aligns with modern ASM export UX | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); `python -m mdeasm_cli assets export --help >/dev/null` (pass) | e6fabeb | high | trusted
- 2026-02-11 | Add task lifecycle operations in helper + CLI (`mdeasm tasks list/get/cancel/run/download`) | Long-running operations need first-class observability/control for production automation reliability | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); `python -m mdeasm_cli tasks --help >/dev/null` (pass) | e6fabeb | high | trusted
- 2026-02-11 | Add opt-in integration smoke for task-based exports (`MDEASM_INTEGRATION_TASK_EXPORT=1`) | Provides a safe path to catch API drift in task/export endpoints without requiring credentials in CI | `source .venv/bin/activate && pytest` (pass; integration task test skipped by default) | e6fabeb | medium | trusted
- 2026-02-11 | Prioritize task/export parity from bounded market scan | Microsoft Defender EASM and peer ASM tooling documentation indicate async export/task orchestration is baseline functionality now | Sources: Microsoft Learn task + `assets:export` references and competitor export/task docs (captured in `CLONE_FEATURES.md`) | n/a | medium | untrusted
- 2026-02-10 | Enforce Ruff `F401` (unused imports) | Prevent dead code / unused imports from silently accumulating while keeping the lint bar small and low-churn | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass) | 62f2817 | high | trusted
- 2026-02-10 | Enforce Ruff `F841` (unused local assignments) | Remove dead local variables (especially in example scripts) and prevent new ones from creeping in | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass) | 0425e00 | high | trusted
- 2026-02-10 | Add `mdeasm doctor` (env + optional control-plane probe) | Provide a standard, non-destructive "is my configuration wired correctly?" command that stays stdout-safe for automation | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); `python -m mdeasm_cli doctor --help >/dev/null` (pass) | 00ac4d0 | high | trusted
- 2026-02-10 | Add saved filters CRUD (data-plane) in helper + CLI | Reduce repetition of brittle filter strings by storing/reusing server-side filters; enable automation via `mdeasm saved-filters ...` | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); `python -m mdeasm_cli saved-filters --help >/dev/null` (pass) | db068a2 | high | trusted
- 2026-02-10 | Fix facet filter single-element tuple specs + regression test | Single-element facet specs without a trailing comma become strings, causing incorrect facet keys/counts for attributes like `cookies`/`ipBlocks` | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass) | 45c272d | high | trusted
- 2026-02-10 | Add `mdeasm workspaces list` (stdout-safe JSON/lines; control-plane only) + opt-in lazy data-plane token init | Multi-workspace environments need a safe discovery primitive; control-plane listing should not require data-plane permissions/scopes | `source .venv/bin/activate && ruff check . && pytest && python3 -m compileall API` (pass); `python3 -m mdeasm_cli workspaces list --help >/dev/null` (pass) | cccd689 | high | trusted
- 2026-02-10 | Stream asset exports for NDJSON and for CSV when columns are explicit | Improves performance and reliability for large inventories (constant memory + faster time-to-first-byte) without changing default JSON/CSV behavior | `source .venv/bin/activate && ruff check . && pytest && python3 -m compileall API` (pass) | d07ab79 | high | trusted
- 2026-02-10 | Add `mdeasm assets schema` to print observed columns (union-of-keys) | Enables deterministic `--columns-from` workflows and faster schema drift detection without exporting full inventories | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass) | c8f0525 | high | trusted
- 2026-02-10 | Add opt-in CLI export integration smoke (`MDEASM_INTEGRATION_EXPORT=1`) | Exercises the end-to-end CLI export wrapper (stdout/stderr separation + encoding) with a tiny capped call while keeping CI credential-free | `source .venv/bin/activate && pytest` (pass; test skipped by default) | 07b9879 | medium | trusted
- 2026-02-10 | Make example scripts import-safe via `main()` guards | Prevent accidental side effects (network calls, `sys.exit`) during imports by tooling/tests while preserving behavior when run as scripts | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass) | da78580 | high | trusted
- 2026-02-10 | Harden `--http-timeout` parsing (reject NaN/inf) + add edge-case tests | Prevent misconfigured reliability knobs from producing confusing runtime failures; keep CLI inputs deterministic | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass) | 8216474 | high | trusted
- 2026-02-10 | Write CLI `--out` exports atomically | Avoid partial/corrupt export files on interruption; safer for scheduled jobs and pipelines | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass) | b0ce4cb | high | trusted
- 2026-02-10 | Add `--columns` / `--columns-from` for CSV exports | Stabilizes schemas and reduces noise/cost for automation pipelines without changing default export behavior | `source .venv/bin/activate && ruff check . && pytest` (pass) | 6efb19a | high | trusted
- 2026-02-10 | Make logging configuration opt-in (`configure_logging`) and add CLI verbosity flags | Avoid surprising root-logger side effects at import while keeping a first-class debugging path in the CLI | `source .venv/bin/activate && ruff check . && pytest` (pass) | 6520e6f | high | trusted
- 2026-02-10 | Split control-plane vs data-plane `api-version` knobs + add opt-in data-plane drift smoke | CP and DP preview versions can drift independently; separate knobs reduce breakage and the opt-in smoke provides a minimal regression probe | `source .venv/bin/activate && ruff check . && pytest` (pass; integration tests skipped by default) | 2b0357f, 0c8559b | high | trusted
- 2026-02-10 | Keep CLI/machine-readable stdout clean by emitting missing-workspace guidance to stderr | `Workspaces.__init__` calls `get_workspaces()` and previously used `print()`, which could corrupt JSON/CSV pipelines when `WORKSPACE_NAME` was unset and multiple workspaces existed | `source .venv/bin/activate && ruff check . && pytest` (pass) | b937478 | high | trusted
- 2026-02-10 | Make the helper pip-installable (editable) and add a console script (`mdeasm`) + CI packaging smoke | Reduce `sys.path`/`cwd` footguns and make CLI usage automation-friendly | `source .venv/bin/activate && python -m pip install -e . && ruff check . && pytest && python -m compileall API && python -m mdeasm_cli --help >/dev/null` (pass) | b6a0599 | high | trusted
- 2026-02-10 | Add compact JSON and NDJSON output modes to the CLI | Improve pipeline ergonomics (smaller JSON, line-oriented ingestion) without changing default behavior | `source .venv/bin/activate && ruff check . && pytest` (pass) | ec831f4 | high | trusted
- 2026-02-10 | Make CLI asset exports stdout-safe (status to stderr) and add `--max-assets`/`--progress-every-pages` knobs | Prevent corrupted JSON/CSV when piping and make long exports controllable/observable | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API && python API/mdeasm_cli.py --help >/dev/null` (pass) | dc5b59d | high | trusted
- 2026-02-10 | Make `Asset.to_dict()` return a dict while preserving default printing | Remove a programmatic usage papercut without breaking existing interactive workflows | `ruff check . && pytest` (pass) | 1f44548 | high | trusted
- 2026-02-10 | Add `docs/auth.md` (env vars + permissions + common failures) and link from READMEs | Reduce onboarding thrash and make auth/permission troubleshooting skimmable | `ruff check . && pytest` (pass) | 539fc66 | high | trusted
- 2026-02-10 | Add opt-in integration smoke test (`MDEASM_INTEGRATION=1`) | Provide a realistic control-plane regression check without forcing credentials in CI | `pytest` (pass; test skipped by default) | 86b4128 | medium | trusted
- 2026-02-10 | Expose CLI flags for HTTP reliability knobs | Reduce brittleness in automation and allow environment-specific tuning without code edits | `ruff check . && pytest && python -m compileall API && python API/mdeasm_cli.py --help` (pass) | dd9ae80 | high | trusted
- 2026-02-10 | Remove `eval()` from facet filter construction; reuse a `requests.Session` | Security hardening + correctness fix for facet counts; improved HTTP performance for paginated exports | `ruff check .` (pass); `pytest` (11 passed); `python -m compileall API` (pass) | 34c636e | high | trusted
- 2026-02-10 | Add dependency manifests + runnable quickstart docs | Make repo installable/runnable without guesswork; fix PyJWT naming confusion | `python -m compileall API` (pass) | d50f47a | high | trusted
- 2026-02-10 | Add minimal lint + unit tests | Prevent regressions in auth/retry and helper behavior without forcing large refactors | `ruff check .` (pass); `pytest` (3 passed) | 54f1289 | high | trusted
- 2026-02-10 | Add CI on main | Keep main production-ready with automated lint/tests/compile | Workflow added at `.github/workflows/ci.yml` | b6f98ae | medium | trusted
- 2026-02-10 | Add correctly spelled risk observations script alias | Reduce papercuts and improve discoverability | `python -m compileall API` (pass) | 6aec111 | high | trusted
- 2026-02-10 | Deduplicate risk observation example scripts | Avoid duplicate example logic; make scripts import-safe and testable while keeping legacy filename working | `ruff check .` (pass); `pytest` (5 passed); `python -m compileall API` (pass) | c41f004 | high | trusted
- 2026-02-10 | Fix `date_range_end`-only asset parsing filter | Prevent silent data loss when users filter by end-date only | `pytest` (pass) | 1e35eb9 | high | trusted
- 2026-02-10 | Make HTTP defaults configurable (timeout/retry/backoff/api-version) | Reduce operational brittleness for bulk exports and evolving preview API versions while keeping defaults backward compatible | `pytest` (pass) | 98e4eac | medium | trusted
- 2026-02-10 | Add opt-in CLI asset export (json/csv) + recipes | Provide a production-friendly automation path for common “inventory export” workflows | `pytest` (pass); `python API/mdeasm_cli.py --help` (pass) | 9a55544 | high | trusted
- 2026-02-10 | Allow `mdeasm assets export --filter @file` / `--filter @-` | Reduce shell-escaping footguns and enable reviewable/versioned long filters for automation pipelines | `source .venv/bin/activate && ruff check . && pytest` (pass) | 4fac209 | high | trusted
- 2026-02-10 | Add CLI `--version` and rely on default `argparse` `prog` | Make the CLI self-describing and ensure `mdeasm --help` reflects the invoked command name | `source .venv/bin/activate && ruff check . && pytest && python -m mdeasm_cli --version` (pass) | a0c1c5b | high | trusted

## Mistakes And Fixes
- Template: YYYY-MM-DD | Issue | Root cause | Fix | Prevention rule | Commit | Confidence
- 2026-02-11 | `create_workspace()` could raise `no region` even when `EASM_REGION` was set to a valid value | Region validation mixed fallback and validation in a single `if/else`, causing the valid fallback path to still raise | Split fallback (`if not region`) from validation (`if region not in _easm_regions`) and add regression coverage | Keep env fallback + validation checks separated in control flow and cover both with tests | 97be9c2 | high
- 2026-02-11 | `create_facet_filter(asset_id=...)` could raise before reaching the `asset_id` path | Function always validated `asset_list_name` first, even when only `asset_id` was supplied | Branch validation by mode (`asset_list_name` vs `asset_id`) and add regression coverage | Add tests for every mutually-exclusive argument path before refactoring validation blocks | 97be9c2 | high
- 2026-02-10 | Facet filters for certain list attributes could collapse into `(None, None, ...)` keys | Single-element facet specs in `_facet_filters` were written as `(\"cookieName\")` which is a string in Python, not a tuple, so code iterated characters instead of facet paths | Add trailing commas for single-element tuples and add a focused unit test that asserts the expected tuple keys | Add regression tests for any special-case parsing table (facet specs, schema maps) and ensure single-element tuples use trailing commas | 45c272d | high
- 2026-02-10 | CLI `mdeasm assets export` could emit non-JSON/CSV text before the payload | `Workspaces.__init__` calls `get_workspaces()` which used `print()` to stdout when `WORKSPACE_NAME` was unset and multiple workspaces existed | Emit guidance to stderr instead of stdout; add regression test for stdout cleanliness | Keep stdout-clean tests for any codepath reachable before the CLI writes machine-readable output | b937478 | high
- 2026-02-10 | CLI exports to stdout could produce invalid JSON/CSV | `get_workspace_assets()` printed status/progress to stdout while the CLI also wrote machine-readable output to stdout | Add `status_to_stderr`/`quiet` knobs and make the CLI send status to stderr; add stdout-mode regression tests | Keep stdout-mode tests for CLI and keep status output configurable in helper methods | dc5b59d | high
- 2026-02-10 | `__validate_asset_id__` could raise `UnboundLocalError` for invalid inputs | Base64 decode path didn't validate input and failed to raise when roundtrip check failed, leaving `verified_asset_id` unset | Use `base64.b64decode(..., validate=True)` and raise on non-canonical/non-base64 values | Keep unit tests for invalid asset ids and run `pytest` in CI | 8cd0881 | high
- 2026-02-10 | `date_range_end`-only filtering referenced `date_start` | Copy/paste oversight in date-range condition and exception handling masked the bug | Use `date_end` in the end-only path and add a focused regression test | Add unit tests for each date-filter mode (start-only, end-only, start+end) before changing filtering logic | 1e35eb9 | high

## Known Risks

## Next Prioritized Tasks
- Add centralized secret redaction for exception/log payloads to prevent credential leakage in shared logs.
- Add task artifact downloader behavior validation with a real tenant (SAS/blob fetch shape can vary by API version/tenant); blocked locally because no EASM credentials are configured.
- Add first-class task artifact fetch command (`mdeasm tasks fetch`) that follows the download reference and writes bytes to disk.
- Evaluate default `EASM_DP_API_VERSION` bump strategy after wider tenant validation of `2024-10-01-preview`.

## Verification Evidence
- Template: YYYY-MM-DD | Command | Key output | Status (pass/fail)
- 2026-02-11 | `gh run watch 21899625738 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `b4ad16f` | pass
- 2026-02-11 | `gh run watch 21899599038 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `97be9c2` | pass
- 2026-02-11 | `gh issue list -R sarveshkapre/MDEASM --limit 30 --json number,title,author,state,url` | repository has issues disabled | pass
- 2026-02-11 | `gh run list -R sarveshkapre/MDEASM --limit 10 --json databaseId,headSha,status,conclusion,name,workflowName,createdAt,updatedAt,url` | recent CI runs all `success` on `main` | pass
- 2026-02-11 | `source .venv/bin/activate && ruff check .` | `All checks passed!` | pass
- 2026-02-11 | `source .venv/bin/activate && pytest -q` | `80 passed, 4 skipped` | pass
- 2026-02-11 | `source .venv/bin/activate && python -m compileall API` | compiled `API/mdeasm.py` and `API/mdeasm_cli.py` | pass
- 2026-02-11 | `source .venv/bin/activate && python -m mdeasm_cli --version` | `python -m mdeasm_cli 1.4.0` | pass
- 2026-02-11 | `source .venv/bin/activate && python -m mdeasm_cli doctor --format json --out -` | returned expected missing-env diagnostics (`TENANT_ID`, `SUBSCRIPTION_ID`, `CLIENT_ID`, `CLIENT_SECRET`) with exit code 1 | pass
- 2026-02-11 | `gh run watch 21898556772 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `4f6db34` | pass
- 2026-02-11 | `source .venv/bin/activate && ruff check .` | `All checks passed!` | pass
- 2026-02-11 | `source .venv/bin/activate && pytest` | `73 passed, 4 skipped in 0.33s` | pass
- 2026-02-11 | `source .venv/bin/activate && python -m compileall API` | compiled `API/` (including updated helper/CLI modules) | pass
- 2026-02-11 | `source .venv/bin/activate && python -m mdeasm_cli --version && python -m mdeasm_cli tasks --help >/dev/null && python -m mdeasm_cli assets export --help >/dev/null` | version `python -m mdeasm_cli 1.4.0`; CLI help paths ok | pass
- 2026-02-11 | `gh run watch 21898525356 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `e6fabeb` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` | `All checks passed!`; `66 passed, 3 skipped`; compile ok | pass
- 2026-02-10 | `gh run watch 21876146038 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `99f7a01` | pass
- 2026-02-10 | `gh run view 21876107678 -R sarveshkapre/MDEASM --json status,conclusion,displayTitle,headSha,updatedAt,url` | conclusion `success` for commit `c1a9707` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest -q && python -m compileall API` | `All checks passed!`; `... (tests passed; integration skipped)`; compile ok | pass
- 2026-02-10 | `source .venv/bin/activate && python -m mdeasm_cli doctor --help >/dev/null && python -m mdeasm_cli saved-filters --help >/dev/null` | CLI help ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` | `All checks passed!`; `54 passed, 3 skipped`; compile ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python3 -m compileall API` | `All checks passed!`; `53 passed, 3 skipped`; compile ok | pass
- 2026-02-10 | `source .venv/bin/activate && python3 -m mdeasm_cli --version && python3 -m mdeasm_cli workspaces list --help >/dev/null && mdeasm --help >/dev/null` | prints `python3 -m mdeasm_cli 1.4.0`; help ok | pass
- 2026-02-10 | `gh run watch 21874659739 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `d07ab79` | pass
- 2026-02-10 | `gh run watch 21874761347 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `d400ef2` | pass
- 2026-02-10 | `gh run watch 21874798539 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `37c704d` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` | `All checks passed!`; `48 passed, 3 skipped`; compile ok | pass
- 2026-02-10 | `source .venv/bin/activate && python -m mdeasm_cli --version && python -m mdeasm_cli assets schema --help >/dev/null && python -m mdeasm_cli assets export --help >/dev/null` | version prints `1.4.0`; CLI help ok | pass
- 2026-02-10 | `gh run watch 21873437081 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `115145d` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` | `All checks passed!`; `45 passed, 2 skipped`; compile ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` | `All checks passed!`; `44 passed, 2 skipped`; compile ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` | `All checks passed!`; `26 passed, 2 skipped`; compile ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest` | `All checks passed!`; `25 passed, 2 skipped` | pass
- 2026-02-10 | `source .venv/bin/activate && python -m compileall API` | compiled `API/` | pass
- 2026-02-10 | `source .venv/bin/activate && python -m pip install -e . --upgrade && python -m mdeasm_cli --help >/dev/null && mdeasm --help >/dev/null` | editable install ok; CLI help ok | pass
- 2026-02-10 | `gh run watch 21870700584 -R sarveshkapre/MDEASM --exit-status` | CI succeeded for commit `0c8559b` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API && mdeasm --help >/dev/null && python -m mdeasm_cli --help >/dev/null` | `All checks passed!`; `19 passed, 1 skipped`; compile ok; CLI help ok | pass
- 2026-02-10 | `gh run watch 21869443801 -R sarveshkapre/MDEASM --exit-status` | CI succeeded for commit `cbea835` | pass
- 2026-02-10 | `source .venv/bin/activate && python -m pip install -e . && ruff check . && pytest && python -m compileall API && python -c "import mdeasm, mdeasm_cli; print('import ok')"` | `All checks passed!`; `16 passed, 1 skipped`; compile ok; import ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API && python -m mdeasm_cli --help >/dev/null && mdeasm --help >/dev/null` | `All checks passed!`; `18 passed, 1 skipped`; compile ok; CLI help ok | pass
- 2026-02-10 | `gh run list -R sarveshkapre/MDEASM -L 2` | CI success for commits `ec831f4` and `b6a0599` (run ids `21869287738`, `21869249414`) | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API && python API/mdeasm_cli.py --help >/dev/null` | `All checks passed!`; `16 passed, 1 skipped`; compile ok; CLI help ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` | `All checks passed!`; `13 passed, 1 skipped`; compile ok | pass
- 2026-02-10 | `gh run list -R sarveshkapre/MDEASM -L 5` | CI success for commits `86b4128`, `539fc66`, `d4984ca` (run ids `21867777681`, `21867755140`, `21867716197`) | pass
- 2026-02-10 | `gh run watch 21867830161 -R sarveshkapre/MDEASM --exit-status` | CI succeeded for commit `ceb9bc5` | pass
- 2026-02-10 | `python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements-dev.txt` | deps installed (pytest, ruff, requests, PyJWT, dotenv, dateutil) | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check .` | `All checks passed!` | pass
- 2026-02-10 | `source .venv/bin/activate && pytest` | `3 passed` | pass
- 2026-02-10 | `source .venv/bin/activate && python -m compileall API` | compiled `API/` | pass
- 2026-02-10 | `source .venv/bin/activate && python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('API').resolve())); import mdeasm; ws=mdeasm.Workspaces.__new__(mdeasm.Workspaces); print(mdeasm._VERSION); print(ws.__validate_asset_id__('domain$$example.com')[1][:12])"` | prints `1.4` and base64 prefix | pass
- 2026-02-10 | `gh run list -R sarveshkapre/MDEASM -L 3` | CI runs succeeded on `main` for commits `b6f98ae`, `6aec111`, `afd37f8` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check .` | `All checks passed!` | pass
- 2026-02-10 | `source .venv/bin/activate && pytest` | `5 passed` | pass
- 2026-02-10 | `source .venv/bin/activate && python -m compileall API` | compiled `API/` (including risk observation scripts) | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check .` | `All checks passed!` | pass
- 2026-02-10 | `source .venv/bin/activate && pytest` | `8 passed` | pass
- 2026-02-10 | `source .venv/bin/activate && python -m compileall API` | compiled `API/` (incl. CLI) | pass
- 2026-02-10 | `source .venv/bin/activate && python API/mdeasm_cli.py --help` | prints CLI usage | pass
- 2026-02-10 | `gh run watch 21864771004 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `6d37a1f` | pass
- 2026-02-10 | `gh run watch 21864790692 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `65482dc` | pass
- 2026-02-10 | `gh run watch 21866672347 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `fe54a94` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API && python API/mdeasm_cli.py --help >/dev/null` | `All checks passed!`; `11 passed`; compile ok; CLI help ok | pass
- 2026-02-10 | `source .venv/bin/activate && python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('API').resolve())); import mdeasm; print('mdeasm version', mdeasm._VERSION)"` | prints `mdeasm version 1.4` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest` | `All checks passed!`; `11 passed` | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest && python -m compileall API && python API/mdeasm_cli.py --help >/dev/null` | `All checks passed!`; `12 passed`; compile ok; CLI help ok | pass
- 2026-02-10 | `source .venv/bin/activate && ruff check . && pytest` | `All checks passed!`; `29 passed, 2 skipped` | pass
- 2026-02-10 | `source .venv/bin/activate && python -m pip install -e . --upgrade && python -m mdeasm_cli --help >/dev/null && python -m mdeasm_cli --version && mdeasm --version && python -m compileall API` | version prints `1.4.0`; compile ok | pass
- 2026-02-10 | `gh run watch 21872023151 -R sarveshkapre/MDEASM --exit-status` | CI succeeded on `main` for commit `9face26` | pass

## Historical Summary
- Keep compact summaries of older entries here when file compaction runs.
