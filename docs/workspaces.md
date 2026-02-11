# Workspaces (CLI)

Use `mdeasm workspaces ...` for control-plane workspace operations.

Prereqs:
```bash
source .venv/bin/activate
python3 -m pip install -e . --upgrade
```

## List
```bash
mdeasm workspaces list --format json --out -
```

## Delete
```bash
# Non-interactive mode (recommended for automation):
mdeasm workspaces delete <workspace_name> --yes --format json --out -

# Optional: supply resource group explicitly if lookup metadata is unavailable.
mdeasm workspaces delete <workspace_name> \
  --resource-group-name <resource_group_name> \
  --yes
```

Notes:
- `workspaces delete` is a control-plane operation and supports reliability flags (`--http-timeout`, `--no-retry`, `--max-retry`, `--backoff-max-s`, `--api-version`, `--cp-api-version`).
- Without `--yes`, delete requires interactive confirmation and will refuse to run in non-interactive mode.
