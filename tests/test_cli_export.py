import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_cli_assets_export_json_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            captured["get_kwargs"] = dict(kwargs)
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
    assert captured["init_kwargs"] == {}
    assert captured["get_kwargs"]["auto_create_facet_filters"] is False
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload == [{"id": "domain$$example.com", "kind": "domain"}]


def test_cli_assets_export_csv_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "assets.csv"
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [
                {"id": "domain$$example.com", "kind": "domain"},
                {"id": "host$$www.example.com", "kind": "host", "ports": [80, 443]},
            ]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            captured["get_kwargs"] = dict(kwargs)
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
    assert captured["init_kwargs"] == {}
    assert captured["get_kwargs"]["auto_create_facet_filters"] is False

    text = out.read_text(encoding="utf-8")
    assert "id,kind,ports" in text.replace("\r\n", "\n").splitlines()[0]
    assert "domain$$example.com" in text
    assert "host$$www.example.com" in text


def test_cli_assets_export_wires_http_knobs(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            captured["get_kwargs"] = dict(kwargs)
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
            "--workspace-name",
            "ws1",
            "--api-version",
            "2024-10-01-preview",
            "--http-timeout",
            "5,30",
            "--no-retry",
            "--max-retry",
            "9",
            "--backoff-max-s",
            "1.5",
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["init_kwargs"] == {
        "workspace_name": "ws1",
        "api_version": "2024-10-01-preview",
        "http_timeout": (5.0, 30.0),
        "retry": False,
        "max_retry": 9,
        "backoff_max_s": 1.5,
    }
    assert captured["get_kwargs"]["workspace_name"] == "ws1"


def test_cli_assets_export_stdout_dash_and_status_to_stderr(monkeypatch, capsys):
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            captured["get_kwargs"] = dict(kwargs)
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
            "-",
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["init_kwargs"] == {}
    assert captured["get_kwargs"]["status_to_stderr"] is True
    # Default behavior should avoid periodic progress chatter.
    assert captured["get_kwargs"]["no_track_time"] is True

    payload = json.loads(capsys.readouterr().out)
    assert payload == [{"id": "domain$$example.com", "kind": "domain"}]


def test_cli_assets_export_wires_max_assets_and_progress(monkeypatch):
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            captured["get_kwargs"] = dict(kwargs)
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
            "-",
            "--max-assets",
            "10",
            "--progress-every-pages",
            "25",
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["get_kwargs"]["max_assets"] == 10
    assert captured["get_kwargs"]["track_every_N_pages"] == 25
