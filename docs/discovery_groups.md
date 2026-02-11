# Discovery Groups (CLI)

Use `mdeasm discovery-groups ...` for data-plane discovery group lifecycle operations.

Prereqs:
```bash
source .venv/bin/activate
python3 -m pip install -e . --upgrade
```

## List
```bash
mdeasm discovery-groups list --workspace-name <workspace_name> --format json --out -
```

List all pages:
```bash
mdeasm discovery-groups list --workspace-name <workspace_name> --get-all --max-page-size 50
```

## Create + Run
Create from a server template:
```bash
mdeasm discovery-groups create \
  --template "Contoso---<template_id>" \
  --workspace-name <workspace_name> \
  --format json \
  --out -
```

Create from a custom payload file:
```bash
mdeasm discovery-groups create \
  --custom-json-file ./discovery_custom.json \
  --workspace-name <workspace_name> \
  --format json \
  --out -
```

The custom payload must be a JSON object compatible with helper expectations, for example:
```json
{
  "name": "Contoso",
  "seeds": {
    "domain": ["contoso.com"],
    "host": ["www.contoso.com"]
  },
  "names": ["Contoso", "Contoso Ltd"]
}
```

## Run Existing Group
```bash
mdeasm discovery-groups run "Contoso seeds" \
  --workspace-name <workspace_name> \
  --format json \
  --out -
```

## Delete
```bash
mdeasm discovery-groups delete "<group_name>" --workspace-name <workspace_name> --format json --out -
```

Line-mode output:
```bash
mdeasm discovery-groups delete "<group_name>" \
  --workspace-name <workspace_name> \
  --format lines \
  --out -
```

Notes:
- These are data-plane operations and support reliability flags (`--http-timeout`, `--no-retry`, `--max-retry`, `--backoff-max-s`, `--api-version`, `--dp-api-version`, `--cp-api-version`).
- `create` requires exactly one of `--template`, `--custom-json`, or `--custom-json-file`.
- `create` and `run` support run-poll controls (`--disco-runs-max-retry`, `--disco-runs-backoff-max-s`).
- `delete` performs best-effort post-delete verification by default (`--verify-delete`); disable with `--no-verify-delete`.
- Delete output includes `deleted`, `status`, and `verifiedDeleted` for automation-safe checks.

## Optional Integration Smoke (Maintainers)
```bash
source .venv/bin/activate
MDEASM_INTEGRATION_DISCOVERY_GROUPS=1 pytest -q tests/test_integration_smoke.py -k discovery_groups
```
