import json
import sys
import types
from pathlib import Path
import io

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_parse_http_timeout_read_only():
    assert mdeasm_cli._parse_http_timeout("30") == (10.0, 30.0)
    assert mdeasm_cli._parse_http_timeout("  30  ") == (10.0, 30.0)


def test_parse_http_timeout_connect_read():
    assert mdeasm_cli._parse_http_timeout("5,30") == (5.0, 30.0)
    assert mdeasm_cli._parse_http_timeout(" 5 , 30 ") == (5.0, 30.0)


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        ",",
        "5,",
        ",30",
        "0",
        "0,30",
        "-1",
        "5,-1",
        "nan",
        "inf",
        "5,nan",
        "1e309",  # inf on most platforms
    ],
)
def test_parse_http_timeout_invalid(value):
    with pytest.raises(ValueError):
        mdeasm_cli._parse_http_timeout(value)


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


def test_cli_assets_export_filter_at_file(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    filter_path = tmp_path / "filter.txt"
    filter_path.write_text(
        '# domains\nstate = "confirmed" AND\nkind = "domain"\n',
        encoding="utf-8",
    )
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
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
            f"@{filter_path}",
            "--format",
            "json",
            "--out",
            str(out),
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["get_kwargs"]["query_filter"] == 'state = "confirmed" AND kind = "domain"'


def test_cli_assets_export_filter_at_stdin(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            captured["get_kwargs"] = dict(kwargs)
            return None

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(sys, "stdin", io.StringIO('state = "confirmed"\nAND kind = "domain"\n'))

    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--filter",
            "@-",
            "--format",
            "json",
            "--out",
            str(out),
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["get_kwargs"]["query_filter"] == 'state = "confirmed" AND kind = "domain"'


def test_cli_version_flag_exits_cleanly(capsys):
    ver = mdeasm_cli._cli_version()
    with pytest.raises(SystemExit) as e:
        mdeasm_cli.main(["--version"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert ver in out


def test_cli_assets_export_json_no_pretty_is_compact(tmp_path, monkeypatch):
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
            "--no-pretty",
            "--out",
            str(out),
            "--no-facet-filters",
        ]
    )
    assert rc == 0

    raw = out.read_text(encoding="utf-8")
    assert "\n  " not in raw
    payload = json.loads(raw)
    assert payload == [{"id": "domain$$example.com", "kind": "domain"}]


def test_cli_assets_export_ndjson_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "assets.ndjson"

    class DummyAssetList:
        def as_dicts(self):
            return [
                {"id": "domain$$example.com", "kind": "domain"},
                {"id": "host$$www.example.com", "kind": "host"},
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
            "ndjson",
            "--out",
            str(out),
            "--no-facet-filters",
        ]
    )
    assert rc == 0

    lines = out.read_text(encoding="utf-8").splitlines()
    assert [json.loads(l) for l in lines] == [
        {"id": "domain$$example.com", "kind": "domain"},
        {"id": "host$$www.example.com", "kind": "host"},
    ]


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


def test_cli_assets_export_csv_columns_limits_header(tmp_path, monkeypatch):
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
            "--columns",
            "id",
            "--columns",
            "kind",
            "--no-facet-filters",
        ]
    )
    assert rc == 0

    header = out.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()[0]
    assert header == "id,kind"


def test_cli_assets_export_csv_columns_from_file_preserves_order(tmp_path, monkeypatch):
    out = tmp_path / "assets.csv"
    cols = tmp_path / "cols.txt"
    cols.write_text("kind\nid\nports\n", encoding="utf-8")

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
            "--columns-from",
            str(cols),
            "--no-facet-filters",
        ]
    )
    assert rc == 0

    header = out.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()[0]
    assert header == "kind,id,ports"


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


def test_cli_assets_export_wires_plane_api_versions(tmp_path, monkeypatch):
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
            "--cp-api-version",
            "cp-v1",
            "--dp-api-version",
            "dp-v1",
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["init_kwargs"] == {"dp_api_version": "dp-v1", "cp_api_version": "cp-v1"}


def test_cli_assets_export_log_level_calls_configure_logging(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            return None

    def configure_logging(level, force=False):
        captured["log_level"] = level
        captured["force"] = force

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, configure_logging=configure_logging)
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
            "--log-level",
            "DEBUG",
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["log_level"] == "DEBUG"


def test_cli_assets_export_verbose_sets_info(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            return None

    def configure_logging(level, force=False):
        captured["log_level"] = level

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, configure_logging=configure_logging)
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
            "-v",
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["log_level"] == "INFO"


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


def test_write_json_is_atomic_on_replace_error(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    out.write_text("OLD\n", encoding="utf-8")

    def boom(_src, _dst):
        raise OSError("rename failed")

    monkeypatch.setattr(mdeasm_cli.os, "replace", boom)

    with pytest.raises(OSError):
        mdeasm_cli._write_json(out, [{"id": "x"}], pretty=False)

    # Atomic write should not truncate/overwrite the original file if rename fails.
    assert out.read_text(encoding="utf-8") == "OLD\n"
    # Temp file should be cleaned up on failure.
    assert list(tmp_path.glob(f".{out.name}.*.tmp")) == []
