# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Local test/build/smoke verification
- GitHub issue and CI signals (author-filtered)
- Bounded market scan of Microsoft Defender EASM + peer ASM APIs
- Gaps found during codebase exploration

## Candidate Features To Do
Priority order (cycle 9 planning; remaining backlog after selected shipments)

- [ ] **Stream-first JSON array export mode**
  - Gap class: weak (performance/parity)
  - Scope: add optional streaming JSON array output to avoid full buffering for `--format json`.
  - Why: lowers peak memory on very large inventories.
  - Score: Impact 4 | Effort 3 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 3

- [ ] **End-to-end command presets (`--profile @file`)**
  - Gap class: differentiator
  - Scope: support reusable local preset files for filter/orderby/output/reliability flags across commands.
  - Why: reduces repeated long commands and operator error in scheduled jobs.
  - Score: Impact 3 | Effort 3 | Strategic fit 4 | Differentiation 2 | Risk 2 | Confidence 2

- [ ] **Task artifact integration smoke: protected URL auth fallback (live tenant)**
  - Gap class: weak (quality)
  - Scope: add optional live tenant smoke path that confirms auth fallback with a protected artifact URL.
  - Why: closes the remaining confidence gap beyond unit coverage.
  - Score: Impact 3 | Effort 3 | Strategic fit 4 | Differentiation 0 | Risk 2 | Confidence 2

- [ ] **CLI completions + concise recipes**
  - Gap class: weak (DX)
  - Scope: ship shell completions and short copy/paste recipes for top workflows.
  - Why: lowers onboarding friction and syntax mistakes.
  - Score: Impact 3 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **CI matrix evolution (evaluate Python 3.13 lane)**
  - Gap class: weak (reliability)
  - Scope: add `3.13` lane after dependency validation and tune fail-fast strategy.
  - Why: keeps runtime compatibility current.
  - Score: Impact 3 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 2 | Confidence 2

- [ ] **Resource tags CRUD parity**
  - Gap class: missing (feature parity)
  - Scope: add helper + CLI list/get/put/delete operations for resource tags.
  - Why: improves governance automation and downstream enrichment.
  - Score: Impact 3 | Effort 3 | Strategic fit 3 | Differentiation 1 | Risk 2 | Confidence 2

- [ ] **Workspace delete CLI/helper (`mdeasm workspaces delete`)**
  - Gap class: missing (operability)
  - Scope: add explicit workspace deletion with confirmation and `--yes` non-interactive mode.
  - Why: completes workspace lifecycle parity for test/ephemeral environments.
  - Score: Impact 3 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 2 | Confidence 2

- [ ] **Tracker trust-label validation automation**
  - Gap class: differentiator
  - Scope: add a lightweight check for decision/evidence/trust-label shape in `PROJECT_MEMORY.md`.
  - Why: keeps autonomous memory auditable and consistent.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 2 | Risk 1 | Confidence 3

- [ ] **Discovery-group delete retry hardening**
  - Gap class: weak (reliability)
  - Scope: add bounded retry/jitter around transient discovery-group delete failures.
  - Why: reduces flaky cleanup in batch automation.
  - Score: Impact 2 | Effort 1 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 3

- [ ] **List/get parity for API error payload surfacing in CLI**
  - Gap class: weak (operability)
  - Scope: standardize CLI error output to include status + redacted error code/message for all commands.
  - Why: improves incident triage without leaking sensitive fields.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 3

- [ ] **CLI error-code contract tests**
  - Gap class: weak (quality)
  - Scope: add focused tests asserting non-zero exit code behavior across common failure classes.
  - Why: keeps automation contracts stable over refactors.
  - Score: Impact 2 | Effort 2 | Strategic fit 3 | Differentiation 0 | Risk 1 | Confidence 3

- [ ] **Request telemetry hooks (opt-in)**
  - Gap class: differentiator
  - Scope: provide optional per-request timing/status counters for long automation runs.
  - Why: improves diagnosability of tenant/API drift and throttling patterns.
  - Score: Impact 2 | Effort 3 | Strategic fit 2 | Differentiation 2 | Risk 2 | Confidence 2

## Implemented
- [x] **Doctor probe target matrix (`mdeasm doctor --probe --probe-targets ...`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_doctor.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && pytest -q tests/test_cli_doctor.py` (pass); `source .venv/bin/activate && python -m mdeasm_cli doctor --probe --probe-targets all --format json --out - >/tmp/mdeasm_doctor_cycle9.json 2>/tmp/mdeasm_doctor_cycle9.err; rc=$?; echo doctor_rc=$rc; test \"$rc\" -eq 1` (pass; expected without env credentials)

- [x] **Doctor docs/workflow alignment for probe matrix**
  - Date: 2026-02-11
  - Scope: `docs/auth.md`, `.github/workflows/smoke-doctor-probe.yml`
  - Evidence (trusted: local verify): `source .venv/bin/activate && make verify` (pass)

- [x] **Typed helper exceptions (incremental migration for config/validation/auth/workspace/data-connections)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `tests/test_data_connections_helpers.py`, `API/README.md`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && pytest -q tests/test_data_connections_helpers.py::test_data_connection_helpers_raise_typed_validation_errors tests/test_data_connections_helpers.py::test_data_connection_methods_raise_typed_workspace_and_validation_errors tests/test_data_connections_helpers.py::test_workspaces_init_missing_config_raises_configuration_error` (pass); `source .venv/bin/activate && python -m mdeasm_cli doctor --format json --out - >/tmp/mdeasm_doctor_cycle8.json 2>/tmp/mdeasm_doctor_cycle8.err; rc=$?; echo doctor_rc=$rc; test \"$rc\" -eq 1` (pass)

- [x] **Task artifact protected URL auth fallback coverage**
  - Date: 2026-02-11
  - Scope: `tests/test_cli_tasks.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q tests/test_cli_tasks.py::test_cli_tasks_fetch_retries_with_bearer_for_protected_url` (pass)

- [x] **Task artifact checksum verification (`mdeasm tasks fetch --sha256`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_tasks.py`, `docs/tasks.md`, `docs/exports.md`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && pytest -q tests/test_cli_tasks.py::test_cli_tasks_fetch_verifies_sha256 tests/test_cli_tasks.py::test_cli_tasks_fetch_fails_when_sha256_mismatch tests/test_cli_tasks.py::test_cli_tasks_fetch_rejects_invalid_sha256_argument` (pass); `source .venv/bin/activate && python -m mdeasm_cli tasks fetch --help >/dev/null` (pass)

- [x] **Data connections opt-in integration smoke (`MDEASM_INTEGRATION_DATA_CONNECTIONS=1`)**
  - Date: 2026-02-11
  - Scope: `tests/test_integration_smoke.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q tests/test_integration_smoke.py::test_integration_smoke_data_connections_list` (pass; skipped by default without env/credentials)

- [x] **Data connections management (`mdeasm data-connections ...`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `API/mdeasm_cli.py`, `docs/data_connections.md`, `README.md`, `API/README.md`, `tests/test_data_connections_helpers.py`, `tests/test_cli_data_connections.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && pytest -q tests/test_data_connections_helpers.py tests/test_cli_data_connections.py` (pass); `source .venv/bin/activate && python -m mdeasm_cli data-connections --help >/dev/null && python -m mdeasm_cli data-connections list --help >/dev/null` (pass)

- [x] **`tasks wait` CLI ergonomics**
  - Date: 2026-02-11
  - Scope: `API/mdeasm_cli.py`, `docs/tasks.md`, `tests/test_cli_tasks.py`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && pytest -q tests/test_cli_tasks.py::test_cli_tasks_wait_returns_terminal_payload tests/test_cli_tasks.py::test_cli_tasks_wait_times_out` (pass); `source .venv/bin/activate && python -m mdeasm_cli tasks wait --help >/dev/null` (pass)

- [x] **Finish label helper stdout gating with consistent return payloads**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q tests/test_mdeasm_helpers.py::test_label_helpers_support_noprint_and_consistent_returns tests/test_mdeasm_helpers.py::test_label_helpers_print_mode_still_returns_payload` (pass)

- [x] **Opt-in integration smoke: full export task artifact lifecycle (`assets:export -> tasks get/download -> tasks fetch`)**
  - Date: 2026-02-11
  - Scope: `tests/test_integration_smoke.py`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q tests/test_integration_smoke.py::test_integration_smoke_server_export_task_artifact_fetch` (pass; skipped by default when env/credentials are absent)

- [x] **Facet query automation hardening (`query_facet_filter(..., noprint=True)`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm.py`, `tests/test_mdeasm_helpers.py`, `API/README.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q tests/test_mdeasm_helpers.py::test_query_facet_filter_supports_noprint_and_structured_return tests/test_mdeasm_helpers.py::test_query_facet_filter_csv_json_outputs_and_return_payload tests/test_mdeasm_helpers.py::test_query_facet_filter_requires_precomputed_filters` (pass)

- [x] **Schema drift comparator (`mdeasm assets schema diff --baseline`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_export.py`, `docs/exports.md`
  - Evidence (trusted: local tests + smoke): `source .venv/bin/activate && pytest -q tests/test_cli_export.py::test_cli_assets_schema_diff_json_no_drift tests/test_cli_export.py::test_cli_assets_schema_diff_lines_fail_on_drift tests/test_cli_export.py::test_cli_assets_schema_diff_requires_baseline` (pass); `source .venv/bin/activate && python -m mdeasm_cli assets schema diff --help >/dev/null` (pass)

- [x] **Artifact fetch retry-on status policy (`--retry-on-statuses`)**
  - Date: 2026-02-11
  - Scope: `API/mdeasm_cli.py`, `tests/test_cli_tasks.py`, `docs/tasks.md`, `docs/exports.md`
  - Evidence (trusted: local tests): `source .venv/bin/activate && pytest -q tests/test_cli_tasks.py::test_cli_tasks_fetch_retries_on_transient_status tests/test_cli_tasks.py::test_cli_tasks_fetch_does_not_retry_non_retryable_status` (pass)

- [x] **CI hardening: scheduled smoke lane (`doctor --probe`)**
  - Date: 2026-02-11
  - Scope: `.github/workflows/smoke-doctor-probe.yml`
  - Evidence (trusted: config + CI): workflow added with secret-gated probe execution; push CI run `21901545206` (pass)

- [x] **Developer DX: canonical `make` aliases (`lint/test/compile/smoke/verify`)**
  - Date: 2026-02-11
  - Scope: `Makefile`, `README.md`
  - Evidence (trusted: local smoke): `source .venv/bin/activate && make verify` (pass)

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
- Market scan refresh (untrusted; 2026-02-11 cycle 9):
  - Microsoft Defender External Attack Surface Management docs continue to frame task/data-connection endpoint coverage as baseline automation capability, so expanding `doctor` from a control-plane-only check to a selectable endpoint matrix is high-value parity work.
  - Peer ASM/search platforms continue to emphasize API-first export and paging workflows, reinforcing the need for operator-visible diagnostics that quickly isolate endpoint drift per surface.
  - Gap map (cycle 9):
    - Weak -> closed this cycle: `doctor` probe matrix (`workspaces`, `assets`, `tasks`, `data-connections`) with explicit per-target pass/fail results.
    - Weak -> closed this cycle: doctor probe contract tests and docs/CI smoke alignment for new probe-target flags.
    - Remaining high-priority weak gaps: stream-first JSON array mode and live protected-artifact fallback integration smoke.
  - Sources reviewed (untrusted):
    - Microsoft Learn Defender EASM REST API overview: https://learn.microsoft.com/en-us/azure/external-attack-surface-management/rest-api-overview
    - Microsoft Learn tasks operation group: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn data-connections operation group: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/data-connections?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - runZero platform API docs: https://help.runzero.com/docs/platform-api/
    - runZero exports docs: https://help.runzero.com/docs/export-data/
    - Censys CLI/API pagination usage: https://docs.censys.com/docs/cli-v2
    - Shodan API cursor/export guidance: https://developer.shodan.io/api/crawl-internet-data

- Market scan refresh (untrusted; 2026-02-11 cycle 8):
  - Microsoft Defender EASM preview references continue to emphasize task lifecycle endpoints (`list/get/cancel/run/download`) and data-connections lifecycle endpoints as core automation primitives, so reliable machine-readable error handling and artifact retrieval robustness remain high-impact parity areas.
  - Peer ASM/search API guidance (runZero, Shodan) still centers API-first operational workflows, reinforcing that stable typed failures and deterministic retry/fallback behavior are baseline expectations for production automation.
  - Gap map (cycle 8):
    - Weak -> closed this cycle: typed exception migration for config/validation/auth/workspace-not-found paths in selected helper surfaces.
    - Weak -> closed this cycle: protected-download bearer-auth fallback coverage for `tasks fetch`.
    - Remaining high-priority weak gaps: stream-first JSON array mode and doctor probe endpoint matrix.
  - Sources reviewed (untrusted):
    - Microsoft Defender EASM REST API overview: https://learn.microsoft.com/en-us/defender-easm/rest-api
    - Microsoft Learn tasks operation group: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn list tasks operation: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks/list-task?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn data-connections operation group: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/data-connections?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - runZero API docs: https://www.runzero.com/docs/api/
    - Shodan API docs: https://developer.shodan.io/api

- Market scan refresh (untrusted; 2026-02-11 cycle 7):
  - Microsoft Defender EASM docs continue to position task exports and data-connections management as first-class automation surfaces, so reliability checks around artifact integrity and data-connection API drift are high-value parity work.
  - Peer ASM APIs (runZero, Shodan) still prioritize API-first export/query workflows, which reinforces continuing investment in machine-safe CLI flows and repeatable automation ergonomics.
  - Gap map (cycle 7):
    - Weak -> closed this cycle: opt-in live smoke for data-connections list endpoint drift.
    - Differentiator -> closed this cycle: checksum-gated artifact retrieval via `mdeasm tasks fetch --sha256`.
    - Remaining high-priority weak gaps: typed exceptions and protected-download auth-fallback integration smoke.
  - Sources reviewed (untrusted):
    - Microsoft Defender EASM REST API overview: https://learn.microsoft.com/en-us/defender-easm/rest-api
    - Microsoft Learn data-connections operations group: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/data-connections?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn `assets:export` task endpoint: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/get-assets-export?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - runZero API docs: https://www.runzero.com/docs/api/
    - Shodan API docs: https://developer.shodan.io/api
    - Shodan query assistant (DX expectation signal): https://developer.shodan.io/api/api-ai

- Market scan refresh (untrusted; 2026-02-11 cycle 6):
  - Microsoft Defender EASM preview docs expose first-class data-connections lifecycle endpoints (`list/get/create-or-replace/delete/validate`) plus paging controls (`skip`, `maxpagesize`), making CLI parity high-impact for production automation.
  - Peer API tooling (runZero, Shodan) continues to emphasize automation-safe export/query ergonomics and cursor/paging workflows, reinforcing priority on scriptable command surfaces and wait/poll helpers.
  - Gap map (cycle 6):
    - Missing -> closed this cycle: data-connections helper/CLI management coverage with redacted secret-bearing fields.
    - Weak -> closed this cycle: task polling ergonomics via `mdeasm tasks wait`.
    - Remaining weak: typed helper exceptions and live integration smoke for data-connections endpoints.
  - Sources reviewed (untrusted):
    - Microsoft Learn: data-connections operation group: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/data-connections?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn: create or replace data connection: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/data-connections/create-or-replace-data-connection?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn: list data connections: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/data-connections/list-data-connections?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - runZero API docs (export/search-after): https://www.runzero.com/docs/api/
    - Shodan API docs (cursor/paging): https://developer.shodan.io/api

- Market scan refresh (untrusted; 2026-02-11 cycle 5):
  - Microsoft Defender EASM data-plane docs expose first-class `tasks/{id}:download` and data-connections CRUD endpoints, reinforcing parity value in export artifact lifecycle validation and upcoming data-connection CLI coverage.
  - Peer ASM/search APIs continue to emphasize async export workflows and cursor/search-after pagination ergonomics for large datasets.
  - Gap map (cycle 5):
    - Weak -> closed this cycle: full opt-in export-task artifact lifecycle smoke (`assets:export -> task poll/download -> tasks fetch`) and `query_facet_filter` stdout-safe automation mode with structured returns.
    - Remaining weak: broad exception typing migration.
    - Missing: data-connections management commands and scoped TODO debt retirement.
    - Differentiator opportunities: local command presets and artifact integrity verification.
  - Sources reviewed (untrusted):
    - Microsoft Learn: tasks download endpoint: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks/download?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn: data-connections operations group: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/data-connections?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - runZero API: export/download and search-after usage: https://www.runzero.com/docs/api/
    - Shodan API: cursor-style large result retrieval (`search_cursor`): https://developer.shodan.io/api/crawl-internet-data

- Market scan refresh (untrusted; 2026-02-11 cycle 4):
  - Microsoft Defender EASM data-plane docs continue to emphasize task-driven export/download and paging controls (`skip`, `maxpagesize`, `mark`), which reinforces schema-stability and retry-policy tooling as near-term reliability priorities.
  - Comparable ASM/search APIs emphasize robust export/download flows and pagination ergonomics; retry classification and drift detection are baseline expectations for production automation.
  - Gap map (cycle 4):
    - Weak -> closed this cycle: schema diff UX for drift detection (`assets schema diff`), explicit retry-on status policy for `tasks fetch`, scheduled probe smoke lane, canonical maintainer command aliases.
    - Remaining weak: opt-in live integration for full task artifact lifecycle and residual stdout-gating cleanup in helper methods.
    - Missing: data-connections management and scoped upstream TODO retirement.
    - Differentiator opportunities: local reusable command presets and tracker trust-label automation.
  - Sources reviewed (untrusted):
    - Microsoft Learn: tasks list (`filter`, `orderby`, `skip`, `maxpagesize`): https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/tasks/list-task?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - Microsoft Learn: `assets:export` endpoint: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/dataplanepreview/assets/get-assets-export?view=rest-defenderforeasm-dataplanepreview-2024-10-01-preview
    - runZero API docs (export/download and automation patterns): https://www.runzero.com/docs/api/
    - Shodan API docs (query/export ergonomics): https://developer.shodan.io/api/crawl-internet-data

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
