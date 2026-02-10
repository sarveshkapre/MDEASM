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

## Notes
- The CLI uses the same `.env` configuration as the example scripts (`TENANT_ID`, `SUBSCRIPTION_ID`, `CLIENT_ID`, `CLIENT_SECRET`, `WORKSPACE_NAME`).
- When using `--out <path>`, exports are written atomically (temp file + replace) to avoid partial files on interruption.
- For compact JSON in pipelines, consider `--no-pretty`. For line-oriented ingestion, consider `--format ndjson`.
- For large exports, consider: `--max-page-size 100`, `--max-page-count N`, `--max-assets N`, and `--no-facet-filters`.
- For long-running exports, consider `--progress-every-pages 25` (status is printed to stderr).
- For reliability tuning without code edits, see `mdeasm assets export --help` for: `--api-version` (or `--cp-api-version`/`--dp-api-version`), `--http-timeout`, `--no-retry`, `--max-retry`, and `--backoff-max-s`.
- `--http-timeout` examples: `--http-timeout 120` (connect=10, read=120) or `--http-timeout 5,120`.
- For debugging, use `-v`/`-vv` or `--log-level DEBUG`.
