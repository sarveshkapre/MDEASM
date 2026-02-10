import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_cli_assets_export_json_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            return None

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--filter",
            'kind = "domain"',
            "--format",
            "json",
            "--out",
            str(out),
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload == [{"id": "domain$$example.com", "kind": "domain"}]


def test_cli_assets_export_csv_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "assets.csv"

    class DummyAssetList:
        def as_dicts(self):
            return [
                {"id": "domain$$example.com", "kind": "domain"},
                {"id": "host$$www.example.com", "kind": "host", "ports": [80, 443]},
            ]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            return None

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--filter",
            'kind in ("domain","host")',
            "--format",
            "csv",
            "--out",
            str(out),
            "--no-facet-filters",
        ]
    )
    assert rc == 0

    text = out.read_text(encoding="utf-8")
    assert "id,kind,ports" in text.replace("\r\n", "\n").splitlines()[0]
    assert "domain$$example.com" in text
    assert "host$$www.example.com" in text

