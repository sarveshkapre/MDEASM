# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do
Next Up (keep deduped)
- [ ] **Schema utilities: compare current columns vs baseline file**
  - Gap class: weak (DX)
  - Scope: add `mdeasm assets schema diff --baseline <file>`.
  - Why: detects downstream-breaking schema drift early.
  - Score: Impact 4 | Effort 2 | Strategic fit 4 | Differentiation 1 | Risk 1 | Confidence 3

- [ ] **Reliability: retry jitter + retry-on status policy map**
  - Gap class: weak (resilience)
  - Scope: add jitter and configurable retry-on status list (for example 429/5xx).
  - Why: smoother behavior under throttling and transient errors.
  - Score: Impact 4 | Effort 3 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **CI hardening: scheduled smoke lane (`doctor --probe`)**
  - Gap class: weak (reliability)
  - Scope: add a non-blocking scheduled workflow that runs probe checks when secrets are present.
  - Why: catches tenant/API drift earlier than ad-hoc local runs.
  - Score: Impact 4 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **Integration test: export task artifact lifecycle**
  - Gap class: weak (quality)
  - Scope: add opt-in integration coverage for `assets:export -> tasks get -> tasks download -> fetch`.
  - Why: closes a high-value drift gap around export payload and artifact URL shapes.
  - Score: Impact 4 | Effort 3 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 2

- [ ] **Data connections management (`mdeasm data-connections ...`)**
  - Gap class: missing (feature parity)
  - Scope: list/create/delete data connections (ADX/Log Analytics) with validation.
  - Why: makes downstream SIEM export setup reproducible.
  - Score: Impact 3 | Effort 4 | Strategic fit 4 | Differentiation 1 | Risk 3 | Confidence 2

- [ ] **Refactor: typed exceptions for helper API failures**
  - Gap class: weak (maintainability)
  - Scope: replace broad `Exception` raises with narrower, documented exception classes.
  - Why: safer caller handling and less fragile automation.
  - Score: Impact 3 | Effort 3 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **Refactor: finish remaining legacy `print()` gating for library usage**
  - Gap class: weak (library UX)
  - Scope: extend `noprint`/structured return behavior to remaining noisy helper functions (for example `query_facet_filter` output helpers).
  - Why: avoids stdout side effects in scripts and pipelines.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **Performance: stream-first JSON array mode for large client exports**
  - Gap class: weak (parity)
  - Scope: optional streaming JSON writer that avoids buffering all assets in memory.
  - Why: improves memory profile and time-to-first-byte on large inventories.
  - Score: Impact 3 | Effort 3 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **CLI completions and command recipe snippets**
  - Gap class: weak (DX)
  - Scope: generate bash/zsh completions and add concise examples.
  - Why: improves operator onboarding and lowers command errors.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **Developer DX: add `make` aliases for lint/test/compile/smoke**
  - Gap class: weak (DX)
  - Scope: standardize local maintenance commands.
  - Why: reduces command drift and shortens maintainer loops.
  - Score: Impact 2 | Effort 1 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **Promote remaining upstream TODOs into scoped features**
  - Gap class: missing (debt retirement)
  - Scope: resource tags CRUD, workspace deletion, discovery-group deletion retry path.
  - Why: converts legacy TODO debt into auditable backlog work.
  - Score: Impact 2 | Effort 4 | Strategic fit 3 | Differentiation 0 | Risk 3 | Confidence 2

- [ ] **Packaging/docs cleanup for historical script aliases**
  - Gap class: weak (DX)
  - Scope: document deprecation timeline for `retreive_*` typo alias while keeping compatibility.
  - Why: reduce user confusion without breakage.
  - Score: Impact 2 | Effort 1 | Strategic fit 2 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **CLI local presets for reusable filter/orderby profiles**
  - Gap class: differentiator
  - Scope: support local profile files for recurring export/task arguments.
  - Why: reduces repeated long command lines in scheduled jobs.
  - Score: Impact 2 | Effort 3 | Strategic fit 3 | Differentiation 2 | Risk 2 | Confidence 2

- [ ] **Trust tagging automation for tracker updates**
  - Gap class: differentiator
  - Scope: add a lightweight check for trust labels and evidence formatting in `PROJECT_MEMORY.md`.
  - Why: keeps autonomous maintenance logs consistent and auditable.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 2 | Risk 1 | Confidence 3

## Implemented
- [x] **Refactor: gate legacy helper stdout paths + no-findings risk observation reliability fix**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check .` (pass); `source .venv/bin/activate && pytest` (pass); `source .venv/bin/activate && python -m compileall API` (pass)

- [x] **Task artifact downloader (`mdeasm tasks fetch`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm_cli.py`, `docs/tasks.md`, `docs/exports.md`, `tests/test_cli_tasks.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && pytest -q tests/test_cli_tasks.py` (pass); `source .venv/bin/activate && python -m mdeasm_cli tasks fetch --help >/dev/null` (pass)

- [x] **Security hardening: centralized secret redaction in helper errors/logs**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q tests/test_mdeasm_helpers.py::test_redact_sensitive_text_masks_bearer_tokens_fields_and_query_params tests/test_mdeasm_helpers.py::test_workspace_query_helper_redacts_failure_exception_text` (pass)

- [x] **Client export resume checkpoints (`--resume-from`, `--checkpoint-out`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_cli_export.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && ruff check . && pytest -q && python -m compileall API` (pass); `source .venv/bin/activate && python -m mdeasm_cli --version` (pass)

- [x] **Deterministic client-side export ordering (`--orderby`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_cli_export.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q` (pass)

- [x] **Asset API compatibility + reliability bugfix sweep**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q` (pass)

- [x] **Server-side asset export mode (`mdeasm assets export --mode server`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/exports.md`, `tests/test_mdeasm_helpers.py`, `tests/test_cli_tasks.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && ruff check . && pytest -q && python -m compileall API` (pass); `python -m mdeasm_cli assets export --help >/dev/null` (pass)

- [x] **Task lifecycle CLI (`mdeasm tasks list/get/cancel/run/download`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/tasks.md`, `README.md`, `API/README.md`, `tests/test_cli_tasks.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && ruff check . && pytest -q && python -m compileall API` (pass); `python -m mdeasm_cli tasks --help >/dev/null` (pass)

- [x] **Opt-in integration smoke for task-based export flow**
  - Date: 2026-02-11
  - Scope: `tests/test_integration_smoke.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q` (pass; task-export integration smoke skipped by default)

- [x] **Lint: enforce unused code checks (Ruff `F401`, `F841`)**
  - Date: 2026-02-10
  - Scope: `pyproject.toml`, `API/affected_cvss_validation.py`, `API/expired_certificates_validation.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass)

- [x] **CLI: `mdeasm doctor` (env + auth sanity checks)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm_cli.py`, `docs/auth.md`, `tests/test_cli_doctor.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); commit `00ac4d0`

- [x] **Saved filters: CRUD in helper + CLI (`mdeasm saved-filters ...`)**
  - Date: 2026-02-10
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/saved_filters.md`, `docs/exports.md`, `API/README.md`, `tests/test_cli_saved_filters.py`, `tests/test_saved_filters_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && ruff check . && pytest && python -m compileall API` (pass); commit `db068a2`

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
- Market scan refresh (untrusted; 2026-02-11 cycle 3):
  - Defender EASM task docs explicitly include a download step (`tasks/{id}:download`), and competitor platforms consistently pair async export jobs with artifact retrieval endpoints or URLs. Artifact fetch in CLI is parity-critical for production automation.
  - Cursor/mark-style continuation and deterministic ordering patterns remain common across ASM/search APIs, reinforcing the need to keep resumable flows and stable ordering first-class.
  - Gap map (cycle 3):
    - Missing (closed this session): task artifact fetch command in CLI.
    - Weak (closed this session): centralized redaction for secrets in raised helper error strings.
    - Remaining weak: schema diff UX, retry jitter policy, and deeper integration smoke coverage for task artifact lifecycle.
  - Sources reviewed (untrusted):
    - Microsoft Learn: Defender EASM tasks operation group (includes download action): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn: `tasks/{id}:download` reference: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks/download?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn: `assets:export` reference: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/get-assets-export?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - runZero API docs (export job/status/download lifecycle): https://www.runzero.com/docs/api/
    - Censys Search API v2 (`cursor` continuation): https://docs.censys.com/reference/v2-globaldata-search-query
    - Shodan API usage and cursor guidance: https://developer.shodan.io/api

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
      - Microsoft Learn: Defender EASM saved filters (list): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/savedfilters/list-saved-filter?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Microsoft Learn: Defender EASM saved filters (create/replace): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/savedfilters/create-or-replace-saved-filter?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Tenable ASM: Inventory settings (export all assets as CSV/XLSX/JSON + choose columns): https://docs.tenable.com/attack-surface-management/Content/Topics/Inventory/InventorySettings.htm
      - Tenable Developer: Export assets v2 (API export job pattern): https://developer.tenable.com/reference/export-assets-v2
      - Tenable Developer: Export assets in XLSX format (token + limits): https://developer.tenable.com/reference/io-asm-exports-assets-xlsx
  - Market scan refresh (untrusted; 2026-02-11):
    - Microsoft Defender EASM data-plane documents explicit task lifecycle endpoints (`tasks`, `tasks/{id}`, `tasks/{id}:cancel`, `tasks/{id}:run`, `tasks/{id}:download`) and `assets:export` task kickoff, which supports a task-oriented automation model.
    - Competitor guidance continues to emphasize async export jobs and API-first export automation for large inventories, reinforcing the priority of task introspection and polling support in this repo.
    - Sources reviewed (untrusted):
      - Microsoft Learn: Defender EASM `assets:export` task kickoff: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/get-assets-export?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Microsoft Learn: Defender EASM tasks operation group (list/get/cancel/run/download): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Tenable ASM API changelog (export/integration lifecycle): https://developer.tenable.com/changelog/asm-export-updates
      - Censys changelog (ASM API/task-related enhancements): https://docs.censys.com/changelog/new-data-in-asm-seeds-api
      - Censys changelog (ASM Cloud Connectors API): https://docs.censys.com/changelog/announcing-the-cloud-connectors-api
  - Market scan refresh (untrusted; 2026-02-11 cycle 2):
    - Microsoft Defender EASM asset list and task list references document `filter`, `orderby`, `skip`, `maxpagesize`, and mark-style continuation tokens, so deterministic ordering and resumable paging are baseline parity expectations.
    - Censys and Shodan API guidance both expose cursor-based continuation patterns for high-volume search/export workflows; checkpoint/resume UX is expected in production ASM automation.
    - Gap map (current repo vs market expectations):
      - Missing: centralized secret redaction in raised exception text, task artifact fetch helper (`tasks fetch`).
      - Weak: resumable client export checkpoints (now delivered), deterministic ordering for resumable exports (now delivered), payload-shape compatibility for list responses (`content` vs `value`) (now delivered).
      - Parity: task lifecycle CLI (`list/get/cancel/run/download`), server-side export task kickoff/wait/download metadata.
      - Differentiator opportunities: local export profile presets and tracker trust-label validation automation.
    - Sources reviewed (untrusted):
      - Microsoft Learn: assets list (`filter`, `orderby`, `skip`, `maxpagesize`, `mark`): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/list-asset-resource?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Microsoft Learn: tasks list (`filter`, `orderby`, `skip`, `maxpagesize`): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks/list-task?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Microsoft Learn: assets export task kickoff (`POST /assets:export`): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/get-assets-export?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
      - Censys Search API v2 pagination (`cursor`): https://docs.censys.com/reference/v2-globaldata-search-query
      - Shodan API paging guidance (`search_cursor`): https://help.shodan.io/the-basics/search-query-fundamentals

## Notes
- This file is maintained by the autonomous clone loop.
