# Auth And Setup

This repo uses OAuth2 client credentials (service principal) to talk to:
- The **control plane** (ARM): `management.azure.com` (for listing/creating EASM workspaces)
- The **data plane**: `easm.defender.microsoft.com` (for workspace assets, reports, etc.)

## Environment Variables

Recommended flow:
1. Copy `API/.env.template` to `.env` at the repo root.
2. Fill in values.

Required:
- `TENANT_ID`
- `SUBSCRIPTION_ID`
- `CLIENT_ID`
- `CLIENT_SECRET`

Recommended:
- `WORKSPACE_NAME` (avoids interactive prompts/printing when multiple workspaces exist)

Optional:
- `EASM_API_VERSION` (defaults to `2022-04-01-preview`; sets both control-plane and data-plane `api-version` unless overridden)
- `EASM_CP_API_VERSION` (control-plane/ARM only override)
- `EASM_DP_API_VERSION` (data-plane only override)
- `RESOURCE_GROUP_NAME` (used by `create_workspace()`)
- `EASM_REGION` (used by `create_workspace()`)

Notes:
- `.env` is in `.gitignore`; keep secrets out of source control.
- `API/mdeasm.py` uses `python-dotenv` (`load_dotenv()`), which searches the current directory and parents for `.env`.

## Permissions (High Level)

You need a Microsoft Entra ID app registration (service principal) with a client secret, and it must be authorized to:
- Read your subscription’s EASM workspaces via ARM (`Microsoft.Easm` resource provider).
- Access the Defender EASM data plane for your tenant/workspace.

In practice, failures usually come from one of:
- The service principal does not have sufficient role assignment scope (subscription/resource group).
- The tenant/subscription is not onboarded for Defender EASM, or the `Microsoft.Easm` provider/workspace is not set up.

Keep access least-privilege:
- Start with a narrow scope (resource group) and widen only if required for your workflow.
- Prefer separate credentials for automation vs. interactive exploration.

## Common Failures

CLI error diagnostics:
- For API request failures, CLI commands now emit a single-line error with `status=...`, `code=...`, and `message=...` when available from the API response.
- Secret-bearing values are redacted before printing diagnostics.

`missing required configuration: ...`
- `.env` is missing `TENANT_ID`, `SUBSCRIPTION_ID`, `CLIENT_ID`, or `CLIENT_SECRET`.
- Confirm you are running from the repo (so `.env` is discoverable) or pass args to `mdeasm.Workspaces(...)`.

## Doctor (Sanity Checks)

If you installed the repo in editable mode (`python3 -m pip install -e .`), you can run:
```bash
source .venv/bin/activate
mdeasm doctor --format json
```

To also run a tiny control-plane probe (list workspaces):
```bash
mdeasm doctor --probe --format json
```

To run an endpoint matrix probe (control-plane + selected data-plane surfaces):
```bash
mdeasm doctor --probe \
  --probe-targets workspaces,assets,tasks,data-connections \
  --probe-max-page-size 1 \
  --format json
```

Notes:
- Exit code is `0` when checks pass, `1` when required env vars are missing or the probe fails.
- `CLIENT_SECRET` is never printed; only presence is reported.
- `--probe-targets` supports `workspaces`, `assets`, `tasks`, `data-connections`, or `all`.
- Data-plane probe targets require a resolvable workspace (`WORKSPACE_NAME` or `--workspace-name`).
- Probe output now includes per-target `elapsedMs` plus a `summary` block (`targetCount`, `okCount`, `failedCount`, `totalElapsedMs`, `slowestTarget`) for quick latency triage.

`401` (Unauthorized)
- Bad client id/secret, wrong tenant, or token scope mismatch.
- Rotate the client secret and confirm the app registration exists in the tenant referenced by `TENANT_ID`.

`403` (Forbidden)
- The service principal is authenticated but doesn’t have permission to the subscription/resource/workspace.
- Confirm role assignment scope and that Defender EASM is enabled/available for the subscription/tenant.

API version / preview issues
- If you see failures that look like schema or endpoint changes, try overriding:
  - env: `EASM_API_VERSION=...`
  - CLI: `python3 API/mdeasm_cli.py assets export --api-version ...`

## References (External)

Treat these as authoritative for the current platform behavior:
- Microsoft Learn: Defender EASM authentication: https://learn.microsoft.com/en-us/defender-easm/authentication
- Microsoft Learn: Defender EASM REST API overview: https://learn.microsoft.com/en-us/defender-easm/rest-api
- Microsoft Learn: Defender EASM REST API reference root: https://learn.microsoft.com/en-us/rest/api/defenderforeasm/
