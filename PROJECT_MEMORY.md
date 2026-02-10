# Project Memory

## Objective
- Keep MDEASM production-ready. Current focus: MDEASM. Find the highest-impact pending work, implement it, test it, and push to main.

## Architecture Snapshot

## Open Problems

## Recent Decisions
- Template: YYYY-MM-DD | Decision | Why | Evidence (tests/logs) | Commit | Confidence (high/medium/low) | Trust (trusted/untrusted)
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

## Mistakes And Fixes
- Template: YYYY-MM-DD | Issue | Root cause | Fix | Prevention rule | Commit | Confidence
- 2026-02-10 | CLI `mdeasm assets export` could emit non-JSON/CSV text before the payload | `Workspaces.__init__` calls `get_workspaces()` which used `print()` to stdout when `WORKSPACE_NAME` was unset and multiple workspaces existed | Emit guidance to stderr instead of stdout; add regression test for stdout cleanliness | Keep stdout-clean tests for any codepath reachable before the CLI writes machine-readable output | b937478 | high
- 2026-02-10 | CLI exports to stdout could produce invalid JSON/CSV | `get_workspace_assets()` printed status/progress to stdout while the CLI also wrote machine-readable output to stdout | Add `status_to_stderr`/`quiet` knobs and make the CLI send status to stderr; add stdout-mode regression tests | Keep stdout-mode tests for CLI and keep status output configurable in helper methods | dc5b59d | high
- 2026-02-10 | `__validate_asset_id__` could raise `UnboundLocalError` for invalid inputs | Base64 decode path didn't validate input and failed to raise when roundtrip check failed, leaving `verified_asset_id` unset | Use `base64.b64decode(..., validate=True)` and raise on non-canonical/non-base64 values | Keep unit tests for invalid asset ids and run `pytest` in CI | 8cd0881 | high
- 2026-02-10 | `date_range_end`-only filtering referenced `date_start` | Copy/paste oversight in date-range condition and exception handling masked the bug | Use `date_end` in the end-only path and add a focused regression test | Add unit tests for each date-filter mode (start-only, end-only, start+end) before changing filtering logic | 1e35eb9 | high

## Known Risks

## Next Prioritized Tasks
- Consider atomic export writes for `--out <path>` to avoid partial files on interruption.
- Consider adding `--filter @path` to reduce shell-escaping and make long filters reviewable.
- Decide whether to keep default `EASM_API_VERSION=2022-04-01-preview` or bump defaults after validating against current Microsoft Learn reference versions.

## Verification Evidence
- Template: YYYY-MM-DD | Command | Key output | Status (pass/fail)
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

## Historical Summary
- Keep compact summaries of older entries here when file compaction runs.
