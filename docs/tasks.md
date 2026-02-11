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

## Wait For Terminal State
```bash
mdeasm tasks wait <task_id> \
  --poll-interval-s 5 \
  --timeout-s 900
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

## Fetch Artifact Bytes To File
```bash
mdeasm tasks fetch <task_id> \
  --artifact-out ./export.csv
```

Optional:
```bash
# Persist the raw tasks/{id}:download payload for troubleshooting.
mdeasm tasks fetch <task_id> \
  --artifact-out ./export.csv \
  --reference-out ./download-reference.json \
  --overwrite

# Verify artifact integrity against an expected digest.
mdeasm tasks fetch <task_id> \
  --artifact-out ./export.csv \
  --sha256 5c9f0f4f3f6a4b8d0fe8d0a1f472f4e5d9510a40a4ed0ce7f3f0f2df1d9cd8de
```

Notes:
- `--workspace-name` can override `WORKSPACE_NAME`.
- Reliability and API version flags are available on all task commands (`--http-timeout`, `--no-retry`, `--max-retry`, `--backoff-max-s`, `--api-version`, `--dp-api-version`, `--cp-api-version`).
- `tasks wait` exits with a non-zero status on timeout and prints the timeout reason to stderr.
- `tasks fetch` supports `--retry-on-statuses` (default `408,425,429,500,502,503,504`) to tune which HTTP responses are treated as transient during artifact download.
- `tasks fetch` respects `Retry-After` response headers in either delay-seconds or HTTP-date format for retryable download responses.
- `tasks fetch` supports `--sha256` to verify artifact integrity before moving the download into place.
- `tasks fetch` follows the URL returned by `tasks/{id}:download` and writes bytes atomically to avoid partial files.
