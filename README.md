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

More details: `API/README.md`

Auth/setup details (env vars, permissions, common 401/403 troubleshooting): `docs/auth.md`
