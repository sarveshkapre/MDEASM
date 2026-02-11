# Resource Tags (CLI)

Use `mdeasm resource-tags ...` to manage Azure resource tags on a Defender EASM workspace.

Prereqs:
```bash
source .venv/bin/activate
python3 -m pip install -e . --upgrade
```

## List
```bash
mdeasm resource-tags list --workspace-name <workspace_name> --format json --out -
```

## Get One Tag
```bash
mdeasm resource-tags get Owner --workspace-name <workspace_name>
```

## Put (Create/Update) One Tag
```bash
mdeasm resource-tags put Environment --value Prod --workspace-name <workspace_name>
```

## Delete One Tag
```bash
mdeasm resource-tags delete Owner --workspace-name <workspace_name>
```

Notes:
- These are control-plane operations and do not require data-plane task/assets permissions.
- Reliability and control-plane API flags are available on all commands (`--http-timeout`, `--no-retry`, `--max-retry`, `--backoff-max-s`, `--api-version`, `--cp-api-version`).
- Tag writes use Azure Resource Manager tag semantics at the workspace scope (`Microsoft.Resources/tags/default`).

## Optional Integration Smoke (Maintainers)
```bash
source .venv/bin/activate
MDEASM_INTEGRATION_RESOURCE_TAGS=1 pytest -q tests/test_integration_smoke.py -k resource_tags_lifecycle
```
