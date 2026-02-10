# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do
- [ ] **(Selected) Clarify `Asset.to_dict()` behavior (return value + optional printing)**
  - Scope: make `Asset.to_dict()` return a dict while preserving current default "print" behavior; add a `print_` kwarg; update docs/examples; add unit test coverage.
  - Why: removes a common papercut for programmatic usage without breaking interactive workflows.
  - Score: Impact 3 | Effort 1 | Strategic fit 4 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **(Selected) Add `docs/auth.md` for `.env` + permissions troubleshooting**
  - Scope: document required env vars, optional env vars, Azure roles/permissions at a high level, and common 401/403 failure modes; link from `README.md` and `API/README.md` while keeping those short.
  - Why: reduces setup thrash and makes onboarding deterministic.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **(Selected) Add an opt-in real integration smoke test (skipped by default)**
  - Scope: `pytest` integration test that runs only when `MDEASM_INTEGRATION=1` and required env vars are set; hit a lightweight endpoint (start with `get_workspaces`) and assert response shape.
  - Why: catches auth/API-version regressions that unit tests cannot.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **Add progress logging + `--max-assets` cap for CLI exports**
  - Scope: optional `--max-assets N` to cap results; periodic progress log (every N pages/assets) for long runs.
  - Why: makes large exports observable and prevents runaway automation.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 3

- [ ] **Package the Python helper for ergonomic installs**
  - Scope: turn `API/mdeasm.py` into an installable module (minimal `pyproject` build config) while keeping existing examples working.
  - Why: removes the "copy into same directory" requirement and improves DX.
  - Score: Impact 3 | Effort 4 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **Add `python -m mdeasm_cli` entrypoint (module mode)**
  - Scope: allow `python -m mdeasm.cli ...` (post-packaging) or `python -m API.mdeasm_cli ...` (pre-packaging) so users can run without relying on `cwd`/`sys.path` quirks.
  - Why: makes automation more robust and reduces "import mdeasm" confusion.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 3

- [ ] **Tighten output ergonomics for exports**
  - Scope: allow `--out -` explicitly for stdout; add `--pretty/--no-pretty` for JSON; optionally add `ndjson` for streaming large outputs.
  - Why: improves composability in shell pipelines and large export performance.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 3

- [ ] **Add a "safe logging" mode**
  - Scope: centralize logging config, avoid printing workspace lists by default, add `verbose` flags in examples/CLI, and ensure no secrets ever leak.
  - Why: improves operational safety in CI/logged environments.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 3

## Implemented
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
    - Sources reviewed (untrusted):
      - Tenable ASM: Inventory settings (export all assets as CSV/XLSX/JSON + choose columns): https://docs.tenable.com/attack-surface-management/Content/Topics/Inventory/InventorySettings.htm
      - Tenable Developer: Export assets v2 (API export job pattern): https://developer.tenable.com/reference/export-assets-v2

## Notes
- This file is maintained by the autonomous clone loop.
