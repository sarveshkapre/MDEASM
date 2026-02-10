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

## Notes
- The CLI uses the same `.env` configuration as the example scripts (`TENANT_ID`, `SUBSCRIPTION_ID`, `CLIENT_ID`, `CLIENT_SECRET`, `WORKSPACE_NAME`).
- For compact JSON in pipelines, consider `--no-pretty`. For line-oriented ingestion, consider `--format ndjson`.
- For large exports, consider: `--max-page-size 100`, `--max-page-count N`, `--max-assets N`, and `--no-facet-filters`.
- For long-running exports, consider `--progress-every-pages 25` (status is printed to stderr).
- For reliability tuning without code edits, see `mdeasm assets export --help` for: `--api-version`, `--http-timeout`, `--no-retry`, `--max-retry`, and `--backoff-max-s`.
