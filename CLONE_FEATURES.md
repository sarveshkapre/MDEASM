# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do
Selected (cycle 10)
- [ ] **CLI: `mdeasm doctor` (env + auth sanity checks)**
  - Scope: add a non-destructive command that validates required env vars, prints configured api-versions, and optionally performs a small control-plane probe (list workspaces). Always keep stdout machine-readable when requested.
  - Why: reduces setup thrash and creates a standard "are my credentials wired correctly?" answer.
  - Score: Impact 4 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **Saved filters: CRUD in helper + CLI (`mdeasm saved-filters ...`)**
  - Scope: implement list/get/put/delete for data-plane saved filters; add CLI commands for automation flows and docs for common use (store a query once, reuse in exports).
  - Why: saved filters are a first-class platform feature and reduce repeated brittle filter strings in scripts/CI.
  - Score: Impact 3 | Effort 3 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

Backlog (keep deduped)
- [ ] **Server-side export via data-plane `assets:export` task**
  - Scope: add an opt-in CLI mode that uses the data-plane `POST /assets:export` endpoint (columns + filename) to kick off an export task, then poll until completion and download the artifact; fall back to the existing paginated GET export path.
  - Why: paginated client-side exports can be slow and memory-heavy; a first-class export job path is a common pattern in mature ASM products.
  - Score: Impact 4 | Effort 5 | Strategic fit 4 | Differentiation 1 | Risk 4 | Confidence 2

- [ ] **Tasks management: list/get/cancel/download (`mdeasm tasks ...`)**
  - Scope: surface data-plane task operations (list, get, cancel, download) with safe defaults and structured output; reuse this for server-side exports and long-running operations.
  - Why: async tasks are core to scaling workflows; having introspection/cancel is table-stakes reliability.
  - Score: Impact 3 | Effort 4 | Strategic fit 3 | Differentiation 0 | Risk 3 | Confidence 2

- [ ] **Data connections management (`mdeasm data-connections ...`)**
  - Scope: list/create/delete data connections (Log Analytics / ADX) and validate parameters; document minimal happy path for exporting into Sentinel/ADX.
  - Why: reduces manual portal steps and makes EASM data integration reproducible.
  - Score: Impact 3 | Effort 4 | Strategic fit 4 | Differentiation 1 | Risk 3 | Confidence 2

- [ ] **Promote remaining upstream TODOs into scoped, testable work**
  - Scope: break `API/mdeasm.py` TODOs into small, test-backed features (asset snapshots; discovery group deletion if endpoint fixed; cancel tasks; resource tagging).
  - Why: avoids a long-lived “TODO pile” and converts it into shippable increments.
  - Score: Impact 2 | Effort 4 | Strategic fit 3 | Differentiation 0 | Risk 3 | Confidence 2

- [ ] **CLI ergonomics: shell completion + examples**
  - Scope: ship `bash`/`zsh` completion generation and add 3-5 focused recipes for exports + saved filters + reliability flags.
  - Why: reduces CLI friction and improves adoption for automation.
  - Score: Impact 2 | Effort 2 | Strategic fit 2 | Differentiation 0 | Risk 1 | Confidence 3

- [ ] **Reliability: make paging/resume first-class for large exports**
  - Scope: add `--resume-skip` / checkpoint file support for long exports; ensure deterministic ordering via `orderby` when available.
  - Why: reduces wasted time on flaky long-running export jobs.
  - Score: Impact 3 | Effort 4 | Strategic fit 3 | Differentiation 1 | Risk 2 | Confidence 2

- [ ] **Security: redact secrets from exceptions/logging across helper + CLI**
  - Scope: add a single redaction utility that scrubs `CLIENT_SECRET` and bearer tokens from any raised/printed error payloads; extend tests to lock in behavior.
  - Why: prevents accidental secret leakage in CI logs and shared terminals.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 1 | Confidence 3

## Implemented
- [x] **Fix facet filter single-element tuple specs**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `tests/test_facet_filters.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); commit `45c272d`

- [x] **CLI: `mdeasm workspaces list` (stdout-safe JSON/lines; control-plane only)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `API/mdeasm.py`, `tests/test_cli_export.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && ruff check . && pytest && python3 -m compileall API` (pass); `python3 -m mdeasm_cli workspaces list --help >/dev/null` (pass); commit `cccd689`

- [x] **Streaming export path (NDJSON; CSV when columns are explicit)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_cli_export.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python3 -m compileall API` (pass); commit `d07ab79`

- [x] **Export schema helper (`mdeasm assets schema`)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_cli_export.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); commit `c8f0525`

- [x] **Add an opt-in “real export” integration smoke (CLI)**
  - Date: 2026-02-10
  - Scope: `tests/test_integration_smoke.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest` (pass; integration test skipped by default); commit `07b9879`

- [x] **Make example scripts import-safe (`main()` guards)**
  - Date: 2026-02-10
  - Scope: `API/affected_cvss_validation.py`, `API/bulk_asset_state_change.py`, `API/cisa_known_exploited_vulns.py`, `API/expired_certificates_validation.py`, `API/extract_associated_certNames_from_query.py`, `API/hosts_with_CNAME_no_IP_possible_subdomain_takeover.py`, `tests/test_example_scripts_imports.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); commit `da78580`

- [x] **HTTP timeout parsing tests + docs**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `docs/exports.md`, `API/mdeasm.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); commit `8216474`

- [x] **Filter input ergonomics (`--filter @file` / `--filter @-`)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest` (pass); commit `4fac209`

- [x] **CLI polish: correct help `prog` + add `--version`**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `README.md`, `.github/workflows/ci.yml`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m mdeasm_cli --version` (pass); commit `a0c1c5b`

- [x] **Atomic export writes**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); commit `b0ce4cb`

- [x] **CSV export column selection**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest` (pass); commit `6efb19a`

- [x] **Add a "safe logging" mode**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest` (pass); commit `6520e6f`

- [x] **Treat API version drift as a first-class concern**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `tests/test_mdeasm_helpers.py`, `tests/test_integration_smoke.py`, `docs/auth.md`, `API/README.md`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest` (pass; integration tests skipped by default); commits `2b0357f`, `0c8559b`

- [x] **Keep CLI stdout clean when `WORKSPACE_NAME` is missing**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest` (pass); commit `b937478`

- [x] **Make the helper pip-installable (editable) + add module/console entrypoints**
  - Date: 2026-02-10
  - Scope: `pyproject.toml`, `.github/workflows/ci.yml`, `.gitignore`, `README.md`, `API/README.md`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && python -m pip install -e . && ruff check . && pytest && python -m compileall API && python -m mdeasm_cli --help` (pass); commit `b6a0599`

- [x] **Export output ergonomics: compact JSON + NDJSON**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest` (pass); commit `ec831f4`

- [x] **Add progress logging + `--max-assets` cap for CLI exports**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_cli_export.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `ruff check . && pytest && python -m compileall API` (pass); commit `dc5b59d`

- [x] **Clarify `Asset.to_dict()` behavior (return value + optional printing)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`, `API/README.md`
  - Evidence (trusted: local tests): `ruff check . && pytest` (pass); commit `1f44548`

- [x] **Add `docs/auth.md` for `.env` + permissions troubleshooting**
  - Date: 2026-02-10
  - Scope: `docs/auth.md`, `README.md`, `API/README.md`
  - Evidence (trusted: local tests): `ruff check . && pytest` (pass); commit `539fc66`

- [x] **Add an opt-in real integration smoke test (skipped by default)**
  - Date: 2026-02-10
  - Scope: `tests/test_integration_smoke.py`
  - Evidence (trusted: local tests): `pytest` (pass; integration test skipped by default); commit `86b4128`

- [x] **Expose CLI flags for HTTP reliability knobs**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_cli_export.py`
  - Evidence (trusted: local tests): `ruff check . && pytest && python -m compileall API && python API/mdeasm_cli.py --help` (pass); commit `dd9ae80`

- [x] **Remove `eval()` from facet filter construction (and fix multi-facet counting bug)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `tests/test_facet_filters.py`
  - Evidence (trusted: local tests): `ruff check .` (pass); `pytest` (pass); commit `34c636e`

- [x] **Lightweight performance improvement: reuse a `requests.Session`**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `pytest` (pass); commit `34c636e`

- [x] **Fix `date_range_end`-only filtering bug in asset parsing**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `tests/test_asset_parsing.py`
  - Evidence (trusted: local tests): `pytest` (pass); commit `1e35eb9`

- [x] **Configurable HTTP behavior (instance defaults)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`
  - Evidence (trusted: local tests): `pytest` (pass); commit `98e4eac`

- [x] **Asset serialization helpers (non-breaking)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`
  - Evidence (trusted: local tests): `pytest` (pass); commit `98e4eac`

- [x] **Market parity exports (CSV/JSON) via a tiny CLI wrapper**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_cli_export.py`, `README.md`, `API/README.md`
  - Evidence (trusted: local tests): `pytest` (pass); commit `9a55544`

- [x] **Fix auth/token refresh correctness + reliability hardening (highest impact)**
  - Date: 2026-02-08
  - Scope: `API/mdeasm.py`
  - Evidence (trusted: local git history): commit `3a5164a` updates token expiry check, control-plane token refresh assignment, request timeouts, retry/backoff.

- [x] **Add dependency manifests + runnable quickstart docs**
  - Date: 2026-02-10
  - Scope: `requirements.txt`, `requirements-dev.txt`, `README.md`, `API/README.md`
  - Evidence (trusted: local git history): commit `d50f47a`

- [x] **Fix asset id validation edge case + remove SyntaxWarning**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `API/extract_associated_certNames_from_query.py`
  - Evidence (trusted: local git history): commit `8cd0881`

- [x] **Static quality bar + unit tests**
  - Date: 2026-02-10
  - Scope: `pyproject.toml`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local git history; local tests): commit `54f1289`

- [x] **Add GitHub Actions CI (lint-lite + tests + compile)**
  - Date: 2026-02-10
  - Scope: `.github/workflows/ci.yml`
  - Evidence (trusted: local git history): commit `b6f98ae`

- [x] **Add correctly-spelled risk observation script alias**
  - Date: 2026-02-10
  - Scope: `API/retrieve_risk_observations.py`, `API/README.md`
  - Evidence (trusted: local git history): commit `6aec111`

- [x] **Deduplicate risk observation example scripts (import-safe `main()` + legacy wrapper)**
  - Date: 2026-02-10
  - Scope: `API/retrieve_risk_observations.py`, `API/retreive_risk_observations.py`, `tests/test_example_scripts.py`, `README.md`
  - Evidence (trusted: local tests; local git history): `pytest` (pass); commit `c41f004`

## Insights
- Market scan (untrusted: external web sources; links captured during session):
  - Microsoft Defender EASM exposes both control-plane (ARM) and data-plane endpoints and uses OAuth2 client credentials. This repo’s `Workspaces` helper aligns with that model.
  - Microsoft’s REST API docs emphasize previewed API versions via the `api-version` query param for data-plane/control-plane operations; making `api-version` configurable reduces breakage as preview versions evolve.
  - Commercial ASM tools generally emphasize: continuous discovery, asset inventory, risk prioritization, exports/integrations, and operational reliability (timeouts/retries).
  - Mature ASM tools ship CLIs and export capabilities (CSV/JSON), often designed to plug into automation workflows (file/stdin, structured output).
  - Sources reviewed (untrusted):
    - Microsoft Learn: Defender EASM REST API overview: https://learn.microsoft.com/en-us/defender-easm/rest-api
    - Microsoft Learn: Defender EASM REST API (preview) reference root: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/
    - Microsoft Learn: example data-plane preview reference (shows `api-version`, `skip`, `maxpagesize`): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/reports/get-snapshot?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn: EASM authentication overview (Microsoft Entra ID): https://learn.microsoft.com/en-us/defender-easm/authentication
    - Censys ASM: exporting assets (CSV): https://support.censys.io/hc/en-us/articles/35338966133524-Exporting-Assets-in-Censys-ASM
    - Censys docs: inventory export UX (CSV): https://docs.censys.com/docs/asm-inventory-assets
    - Censys Python: CLI reference (structured output patterns): https://censys-python.readthedocs.io/en/v2.2.10/cli.html
    - Palo Alto Networks: Cortex Xpanse product overview: https://www.paloaltonetworks.com/cortex/cortex-xpanse
  - Market scan refresh (untrusted; 2026-02-10):
    - Export UX commonly supports multiple formats and column selection (CSV/XLSX/JSON).
    - Large data exports are often implemented as async jobs in APIs (kick off export, poll, download chunks).
    - Microsoft Learn data-plane preview references show a newer `api-version` (`2024-10-01-preview`) than this repo’s historic default; keeping `EASM_API_VERSION` configurable remains important.
    - Microsoft Learn data-plane preview asset listing endpoints document `skip`/`maxpagesize` parameters; CLI paging knobs should stay aligned with those semantics.
    - Some ASM vendors enforce format-specific export limits (for example XLSX max row counts) and provide an async "export token" workflow for downloads.
    - Sources reviewed (untrusted):
      - Microsoft Learn: Defender EASM data-plane preview assets list (shows `api-version`, `skip`, `maxpagesize`): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/list-asset-resource?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Microsoft Learn: Defender EASM data-plane preview `assets:export` (server-side export task): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/get-assets-export?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Tenable ASM: Inventory settings (export all assets as CSV/XLSX/JSON + choose columns): https://docs.tenable.com/attack-surface-management/Content/Topics/Inventory/InventorySettings.htm
      - Tenable Developer: Export assets v2 (API export job pattern): https://developer.tenable.com/reference/export-assets-v2
      - Tenable Developer: Export assets in XLSX format (token + limits): https://developer.tenable.com/reference/io-asm-exports-assets-xlsx

## Notes
- This file is maintained by the autonomous clone loop.
