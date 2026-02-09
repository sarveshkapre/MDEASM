# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do
- [ ] **Fix auth/token refresh correctness + reliability hardening (highest impact)**
  - Scope: `API/mdeasm.py`
  - Problems observed (trusted: local code read):
    - `__token_expiry__()` threshold appears inverted (`now - 30 >= exp`).
    - Control-plane token refresh assigns to the wrong field (`_dp_token` instead of `_cp_token`) in multiple places.
    - Requests have no explicit timeout and retries have no backoff.
  - Score: Impact 5 | Effort 2 | Strategic fit 5 | Differentiation 2 | Risk 2 | Confidence 5

- [ ] **Add unit tests for critical helper behavior (token expiry, token refresh path, asset id validation)**
  - Scope: new `tests/` with request mocking; no real Azure calls.
  - Score: Impact 4 | Effort 3 | Strategic fit 5 | Differentiation 1 | Risk 1 | Confidence 4

- [ ] **Add dependency manifests + clarify installation (PyJWT naming, runtime vs dev deps)**
  - Scope: `requirements.txt`, `requirements-dev.txt`, doc updates.
  - Score: Impact 4 | Effort 2 | Strategic fit 5 | Differentiation 1 | Risk 1 | Confidence 5

- [ ] **Add GitHub Actions CI (lint + tests)**
  - Scope: `.github/workflows/ci.yml` running ruff + pytest + compileall.
  - Score: Impact 4 | Effort 2 | Strategic fit 5 | Differentiation 1 | Risk 1 | Confidence 4

- [ ] **Upgrade root README to be runnable (quickstart, config, common workflows)**
  - Scope: `README.md` (root) + references to `API/README.md`, `KQL/README.md`, `Workbook/README.md`.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 1 | Risk 1 | Confidence 4

- [ ] **Add a correctly-spelled script alias for risk observations**
  - Scope: add `API/retrieve_risk_observations.py` wrapper; keep `API/retreive_risk_observations.py` for compatibility.
  - Score: Impact 2 | Effort 1 | Strategic fit 3 | Differentiation 0 | Risk 0 | Confidence 5

- [ ] **Market parity exports (CSV/JSON) for common queries via a tiny CLI wrapper**
  - Scope: add `API/mdeasm_cli.py` (opt-in) without breaking existing scripts.
  - Score: Impact 3 | Effort 3 | Strategic fit 4 | Differentiation 2 | Risk 2 | Confidence 3

- [ ] **Docs: add a “Troubleshooting” section (token scopes, workspace selection, common API errors)**
  - Scope: `API/README.md`, `README.md`.
  - Score: Impact 3 | Effort 2 | Strategic fit 4 | Differentiation 1 | Risk 1 | Confidence 3

- [ ] **Static quality bar**
  - Scope: add `pyproject.toml` for ruff/pytest config (lightweight).
  - Score: Impact 2 | Effort 2 | Strategic fit 4 | Differentiation 0 | Risk 1 | Confidence 4

## Implemented

## Insights
- Market scan (untrusted: external web sources; links captured during session):
  - Microsoft Defender EASM exposes both control-plane (ARM) and data-plane endpoints and uses OAuth2 client credentials. This repo’s `Workspaces` helper aligns with that model.
  - Commercial ASM tools generally emphasize: continuous discovery, asset inventory, risk prioritization, exports/integrations, and operational reliability (timeouts/retries).

## Notes
- This file is maintained by the autonomous clone loop.
