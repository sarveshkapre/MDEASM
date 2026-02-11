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
- `delete` performs best-effort post-delete verification by default (`--verify-delete`); disable with `--no-verify-delete`.
- Delete output includes `deleted`, `status`, and `verifiedDeleted` for automation-safe checks.

## Optional Integration Smoke (Maintainers)
```bash
source .venv/bin/activate
MDEASM_INTEGRATION_DISCOVERY_GROUPS=1 pytest -q tests/test_integration_smoke.py -k discovery_groups_list
```
