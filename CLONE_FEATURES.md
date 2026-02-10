# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do
- [ ] **Add dependency manifests + fix docs for correct deps (PyJWT naming)**
  - Scope: `requirements.txt`, `requirements-dev.txt`, `API/README.md`, root `README.md`
  - Why now: repo currently has no installable dependency manifest; docs instruct installing `jwt` (wrong package name).
  - Score: Impact 5 | Effort 2 | Strategic fit 5 | Differentiation 0 | Risk 1 | Confidence 5

- [ ] **Add unit tests for critical helper behavior (token expiry, asset id validation, retry/backoff)**
  - Scope: new `tests/` with request mocking; no real Azure calls.
  - Why now: protects the recently-hardened auth/retry logic from regressions.
  - Score: Impact 5 | Effort 3 | Strategic fit 5 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **Add GitHub Actions CI (lint-lite + tests)**
  - Scope: `.github/workflows/ci.yml` running ruff + pytest + compileall.
  - Why now: keeps main green and gives fast feedback to future changes.
  - Score: Impact 5 | Effort 2 | Strategic fit 5 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **Static quality bar (minimal, non-invasive)**
  - Scope: `pyproject.toml` for ruff/pytest config (keep ruff rules narrow to avoid mass refactors).
  - Score: Impact 4 | Effort 2 | Strategic fit 5 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **Add a correctly-spelled script alias for risk observations**
  - Scope: add `API/retrieve_risk_observations.py` wrapper; keep `API/retreive_risk_observations.py` for compatibility.
  - Score: Impact 3 | Effort 1 | Strategic fit 4 | Differentiation 0 | Risk 0 | Confidence 5

- [ ] **Upgrade root README to be runnable (quickstart, config, common workflows)**
  - Scope: `README.md` (root) + references to `API/README.md`, `KQL/README.md`, `Workbook/README.md`.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 1 | Confidence 4

- [ ] **Docs: add a “Troubleshooting” section (token scopes, .env location, common API errors)**
  - Scope: `API/README.md`, `README.md`.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 1 | Confidence 3

## Implemented
- [x] **Fix auth/token refresh correctness + reliability hardening (highest impact)**
  - Date: 2026-02-08
  - Scope: `API/mdeasm.py`
  - Evidence (trusted: local git history): commit `3a5164a` updates token expiry check, control-plane token refresh assignment, request timeouts, retry/backoff.

## Insights
- Market scan (untrusted: external web sources; links captured during session):
  - Microsoft Defender EASM exposes both control-plane (ARM) and data-plane endpoints and uses OAuth2 client credentials. This repo’s `Workspaces` helper aligns with that model.
  - Commercial ASM tools generally emphasize: continuous discovery, asset inventory, risk prioritization, exports/integrations, and operational reliability (timeouts/retries).
  - Sources reviewed (untrusted):
    - Microsoft Learn: Defender EASM REST API overview
    - Microsoft Learn: EASM authentication overview (Microsoft Entra ID)
    - Censys ASM: exporting assets (CSV)
    - Palo Alto Networks: Cortex Xpanse product overview

## Notes
- This file is maintained by the autonomous clone loop.
