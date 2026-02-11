# Exports (CLI)

This repo includes a small opt-in CLI for common automation flows.

After installing the repo in editable mode, you can use either:
- `mdeasm ...` (console script)
- `python3 -m mdeasm_cli ...` (module mode)

## Asset export (JSON)
```bash
source .venv/bin/activate

# Ensure `.env` exists at repo root (see README/API docs), then:
python3 -m pip install -e . --upgrade

mdeasm assets export \
  --filter 'state = "confirmed" AND kind = "domain"' \
  --format json \
  --out assets.json \
  --get-all \
  --no-facet-filters
```

## Long filters from a file (or stdin)
```bash
source .venv/bin/activate

cat > filter.txt <<'EOF'
# comments and blank lines are ignored
state = "confirmed" AND
kind = "domain"
EOF

mdeasm assets export \
  --filter @filter.txt \
  --format json \
  --out assets.json \
  --get-all \
  --no-facet-filters

# Or read from stdin:
cat filter.txt | mdeasm assets export --filter @- --format json --out assets.json --get-all --no-facet-filters
```

## Tip: Store Filters Server-Side

If you want to reuse filters across scripts/exports, you can store them as saved filters in Defender EASM:
- Docs: `docs/saved_filters.md`
- CLI: `mdeasm saved-filters put/list/get/delete`

## Asset export (stdout)
```bash
source .venv/bin/activate

# Machine-readable output goes to stdout; status/progress goes to stderr.
python3 -m mdeasm_cli assets export \
  --filter 'state = "confirmed" AND kind = "domain"' \
  --format json \
  --out - \
  --get-all \
  --no-facet-filters
```

## Asset export (CSV)
```bash
source .venv/bin/activate

mdeasm assets export \
  --filter 'state = "confirmed" AND kind = "host"' \
  --format csv \
  --out assets.csv \
  --get-all \
  --no-facet-filters
```

## Asset export (CSV with selected columns)
```bash
source .venv/bin/activate

# Keep schemas stable for downstream pipelines by explicitly selecting columns.
mdeasm assets export \
  --filter 'state = "confirmed" AND kind = "host"' \
  --format csv \
  --out assets.csv \
  --columns id,kind,displayName,domain,firstSeen,lastSeen
```

## Deterministic ordering for resumable exports (client mode)
```bash
source .venv/bin/activate

mdeasm assets export \
  --filter 'state = "confirmed" AND kind = "host"' \
  --format ndjson \
  --out hosts.ndjson \
  --get-all \
  --orderby 'id asc' \
  --no-facet-filters
```

## Resume interrupted client exports
```bash
source .venv/bin/activate

# During a long run, write a checkpoint after each fetched page.
mdeasm assets export \
  --filter 'state = "confirmed" AND kind = "host"' \
  --format ndjson \
  --out hosts.ndjson \
  --get-all \
  --orderby 'id asc' \
  --checkpoint-out .mdeasm-export-checkpoint.json \
  --no-facet-filters

# Resume from a saved checkpoint file:
mdeasm assets export \
  --filter 'state = "confirmed" AND kind = "host"' \
  --format ndjson \
  --out hosts.ndjson \
  --get-all \
  --orderby 'id asc' \
  --resume-from @.mdeasm-export-checkpoint.json \
  --no-facet-filters
```

`--resume-from` also accepts a direct integer page (`--resume-from 25`) or a mark token (`--resume-from mark:<token>`).

## Server-side asset export task (recommended for large inventories)
```bash
source .venv/bin/activate

# Server-side export requires explicit columns.
mdeasm assets export \
  --mode server \
  --filter 'state = "confirmed" AND kind = "host"' \
  --columns id,kind,displayName,ipAddress,lastSeen \
  --server-file-name hosts_export.csv \
  --wait \
  --download-on-complete \
  --format json \
  --out export_task.json
```

Notes:
- `--mode server` uses Defender EASM `POST /assets:export` and returns task metadata.
- `--wait` polls `tasks/{id}` until a terminal state; use `--poll-interval-s` / `--wait-timeout-s` to tune behavior.
- `--download-on-complete` calls `tasks/{id}:download` after completion and includes that response in output.
- To download artifact bytes to disk, run `mdeasm tasks fetch <task_id> --artifact-out <path>` (or use `--reference-out` to persist the raw download reference JSON). Use `--retry-on-statuses` to tune transient retry behavior and `--sha256` for integrity verification.
- For direct task operations, see `docs/tasks.md`.

## Export schema (columns file)
```bash
source .venv/bin/activate

# Generate a newline-delimited columns file (suitable for --columns-from).
mdeasm assets schema \
  --filter 'state = "confirmed" AND kind = "host"' \
  --out columns.txt

# Use that schema deterministically in CSV exports.
mdeasm assets export \
  --filter 'state = "confirmed" AND kind = "host"' \
  --format csv \
  --out assets.csv \
  --columns-from columns.txt
```

## Schema drift check against a baseline
```bash
source .venv/bin/activate

# Compare current observed columns to a baseline file.
mdeasm assets schema diff \
  --filter 'state = "confirmed" AND kind = "host"' \
  --baseline columns.txt \
  --format json \
  --out schema-diff.json

# CI-friendly mode: return exit code 3 when drift is detected.
mdeasm assets schema diff \
  --filter 'state = "confirmed" AND kind = "host"' \
  --baseline columns.txt \
  --fail-on-drift
```

## Notes
- The CLI uses the same `.env` configuration as the example scripts (`TENANT_ID`, `SUBSCRIPTION_ID`, `CLIENT_ID`, `CLIENT_SECRET`, `WORKSPACE_NAME`).
- When using `--out <path>`, exports are written atomically (temp file + replace) to avoid partial files on interruption.
- For compact JSON in pipelines, consider `--no-pretty`. For line-oriented ingestion, consider `--format ndjson`.
- For large exports:
  - `--format ndjson` streams rows as they are fetched (constant memory) when `--no-facet-filters` is set.
  - `--format csv` can stream rows when columns are explicit (`--columns` / `--columns-from`) and `--no-facet-filters` is set. If columns are not explicit, the CLI buffers rows to infer a union-of-keys header.
- For large exports, consider: `--max-page-size 100`, `--max-page-count N`, `--max-assets N`, and `--no-facet-filters`.
- For stable, resumable client-side exports, use `--orderby` plus `--checkpoint-out`/`--resume-from`.
- For long-running exports, consider `--progress-every-pages 25` (status is printed to stderr).
- For reliability tuning without code edits, see `mdeasm assets export --help` for: `--api-version` (or `--cp-api-version`/`--dp-api-version`), `--http-timeout`, `--no-retry`, `--max-retry`, and `--backoff-max-s`.
- `--http-timeout` examples: `--http-timeout 120` (connect=10, read=120) or `--http-timeout 5,120`.
- For debugging, use `-v`/`-vv` or `--log-level DEBUG`.
- Task export mode (`--mode server`) may require a newer data-plane `api-version` in some tenants; if needed, set `--dp-api-version 2024-10-01-preview` (or `EASM_DP_API_VERSION`).
