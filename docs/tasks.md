# Tasks (CLI)

Use `mdeasm tasks ...` to inspect and control data-plane task operations.

Prereqs:
```bash
source .venv/bin/activate
python3 -m pip install -e . --upgrade
```

## List
```bash
mdeasm tasks list --format json --get-all
```

## Get
```bash
mdeasm tasks get <task_id>
```

## Cancel
```bash
mdeasm tasks cancel <task_id>
```

## Resume / Run
```bash
mdeasm tasks run <task_id>
```

## Download Artifact Reference
```bash
mdeasm tasks download <task_id>
```

Notes:
- `--workspace-name` can override `WORKSPACE_NAME`.
- Reliability and API version flags are available on all task commands (`--http-timeout`, `--no-retry`, `--max-retry`, `--backoff-max-s`, `--api-version`, `--dp-api-version`, `--cp-api-version`).
