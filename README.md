# MDEASM

Helpers and examples for Microsoft Defender External Attack Surface Management (EASM):

- `API/`: Python helper (`API/mdeasm.py`) plus example scripts
- `KQL/`: query samples for Log Analytics / Azure Data Explorer
- `Workbook/`: Azure Workbook template + screenshots
- `docs/exports.md`: CLI export recipes

## Quickstart (API)
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt --upgrade

cp API/.env.template .env
$EDITOR .env

python3 API/retrieve_risk_observations.py
```
For programmatic use of helper methods, prefer `noprint=True` where supported to keep stdout clean; label helpers now also return structured payloads in either mode.

## Optional: Install + CLI
```bash
source .venv/bin/activate
python3 -m pip install -e . --upgrade

# CLI help (no credentials required):
mdeasm --help
mdeasm --version

# List workspaces (requires `.env` credentials):
mdeasm workspaces list --format json --out -
```

More details: `API/README.md`

Auth/setup details (env vars, permissions, common 401/403 troubleshooting): `docs/auth.md`
Export recipes (client + server task mode): `docs/exports.md`
Task operations (`mdeasm tasks ...`): `docs/tasks.md`
Data connections (`mdeasm data-connections ...`): `docs/data_connections.md`
Discovery groups (`mdeasm discovery-groups ...`): `docs/discovery_groups.md`
Workspace operations (`mdeasm workspaces ...`): `docs/workspaces.md`
Resource tag operations (`mdeasm resource-tags ...`): `docs/resource_tags.md`

## Maintainer Loop
```bash
source .venv/bin/activate
make verify
```
