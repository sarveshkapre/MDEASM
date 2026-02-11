# Saved Filters (CLI)

Saved filters let you store a query filter once in Defender EASM and reuse it across scripts and exports.

Prereqs:
```bash
source .venv/bin/activate
python3 -m pip install -e . --upgrade
```

## Create Or Update
```bash
mdeasm saved-filters put owned_domains \
  --filter 'state = "confirmed" AND kind = "domain"' \
  --description "Owned domains"
```

You can also keep long filters in a file:
```bash
cat > filter.txt <<'EOF'
state = "confirmed" AND
kind = "domain"
EOF

mdeasm saved-filters put owned_domains \
  --filter @filter.txt \
  --description "Owned domains"
```

## List
```bash
mdeasm saved-filters list --format json --get-all
```

## Get
```bash
mdeasm saved-filters get owned_domains
```

## Delete
```bash
mdeasm saved-filters delete owned_domains

# Structured line output (name<TAB>deleted)
mdeasm saved-filters delete owned_domains --format lines
```

Notes:
- `saved-filters put` validates payload shape locally before API submit (`name`, `filter`, `description` must be non-empty after trimming).
- Saved filter names are treated as path segments and cannot include `/`.
- `saved-filters list --format lines` emits stable tab-delimited columns: `name`, `displayName`, `filter` (control whitespace is normalized for shell-safe parsing).

## Optional Integration Smoke (Maintainers)
```bash
source .venv/bin/activate
MDEASM_INTEGRATION_SAVED_FILTERS=1 pytest -q tests/test_integration_smoke.py -k saved_filters_lifecycle
```
