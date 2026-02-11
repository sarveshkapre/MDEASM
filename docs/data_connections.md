# Data Connections (CLI)

Use `mdeasm data-connections ...` to manage Defender EASM data connections for:
- Log Analytics (`logAnalytics`)
- Azure Data Explorer (`azureDataExplorer`)

Prereqs:
```bash
source .venv/bin/activate
python3 -m pip install -e . --upgrade
```

## List
```bash
mdeasm data-connections list --format json --get-all
```

## Get
```bash
mdeasm data-connections get <name>
```

## Create Or Replace: Log Analytics
```bash
mdeasm data-connections put <name> \
  --kind logAnalytics \
  --workspace-id "/subscriptions/.../resourcegroups/.../providers/microsoft.operationalinsights/workspaces/..." \
  --api-key "<log-analytics-api-key>" \
  --content assets \
  --frequency weekly \
  --frequency-offset 1
```

## Create Or Replace: Azure Data Explorer
```bash
mdeasm data-connections put <name> \
  --kind azureDataExplorer \
  --cluster-name "<cluster-name>" \
  --database-name "<database-name>" \
  --region "eastus" \
  --content attackSurfaceInsights \
  --frequency daily \
  --frequency-offset 0
```

## Validate Payload
```bash
mdeasm data-connections validate <name> \
  --kind logAnalytics \
  --workspace-id "/subscriptions/.../resourcegroups/.../providers/microsoft.operationalinsights/workspaces/..." \
  --api-key "<log-analytics-api-key>"
```

## Delete
```bash
mdeasm data-connections delete <name> --format json

# Structured line output (deleted<TAB>status)
mdeasm data-connections delete <name> --format lines
```

Notes:
- `--workspace-name` overrides `WORKSPACE_NAME`.
- Reliability and API version flags are available on all commands (`--http-timeout`, `--no-retry`, `--max-retry`, `--backoff-max-s`, `--api-version`, `--dp-api-version`, `--cp-api-version`).
- Secret-bearing fields such as `apiKey` are redacted in helper/CLI output.
- If your tenant requires newer preview endpoints, pass `--dp-api-version 2024-10-01-preview`.

## Optional Integration Smoke (Maintainers)
```bash
source .venv/bin/activate
MDEASM_INTEGRATION_DATA_CONNECTIONS=1 pytest -q tests/test_integration_smoke.py -k data_connections
```

Optional env knobs:
- `MDEASM_INTEGRATION_DATA_CONNECTION_NAME`: explicit connection name for `get` smoke.
- `MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_KIND`: `logAnalytics` (default) or `azureDataExplorer`.
- `MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_*`: optional validate payload overrides used by the smoke test.
