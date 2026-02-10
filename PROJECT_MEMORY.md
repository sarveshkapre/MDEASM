# Project Memory

## Objective
- Keep MDEASM production-ready. Current focus: MDEASM. Find the highest-impact pending work, implement it, test it, and push to main.

## Architecture Snapshot

## Open Problems

## Recent Decisions
- Template: YYYY-MM-DD | Decision | Why | Evidence (tests/logs) | Commit | Confidence (high/medium/low) | Trust (trusted/untrusted)
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
- 2026-02-10 | `__validate_asset_id__` could raise `UnboundLocalError` for invalid inputs | Base64 decode path didn't validate input and failed to raise when roundtrip check failed, leaving `verified_asset_id` unset | Use `base64.b64decode(..., validate=True)` and raise on non-canonical/non-base64 values | Keep unit tests for invalid asset ids and run `pytest` in CI | 8cd0881 | high
- 2026-02-10 | `date_range_end`-only filtering referenced `date_start` | Copy/paste oversight in date-range condition and exception handling masked the bug | Use `date_end` in the end-only path and add a focused regression test | Add unit tests for each date-filter mode (start-only, end-only, start+end) before changing filtering logic | 1e35eb9 | high

## Known Risks

## Next Prioritized Tasks
- Remove `eval()` from facet filter construction and add representative unit tests.
- Consider a `requests.Session` per `Workspaces` instance for performance on large exports.
- Decide whether to keep default `EASM_API_VERSION=2022-04-01-preview` or bump the default after validating against current Microsoft Learn reference versions.

## Verification Evidence
- Template: YYYY-MM-DD | Command | Key output | Status (pass/fail)
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

## Historical Summary
- Keep compact summaries of older entries here when file compaction runs.
