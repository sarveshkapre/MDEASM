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


def test_parse_resume_from_variants(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(
        json.dumps({"next_page": 12, "next_mark": "m123"}, sort_keys=True), encoding="utf-8"
    )
    assert mdeasm_cli._parse_resume_from("12") == {"page": 12}
    assert mdeasm_cli._parse_resume_from("mark:m123") == {"mark": "m123"}
    assert mdeasm_cli._parse_resume_from("opaque-token") == {"mark": "opaque-token"}
    assert mdeasm_cli._parse_resume_from(f"@{checkpoint}") == {"page": 12, "mark": "m123"}


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


def test_cli_assets_schema_lines_to_stdout(monkeypatch, capsys):
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [
                {"id": "domain$$example.com", "kind": "domain", "displayName": "example.com"},
                {"id": "domain$$example.net", "kind": "domain", "domain": "example.net"},
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

    rc = mdeasm_cli.main(["assets", "schema", "--filter", 'kind = "domain"', "--max-assets", "10"])
    assert rc == 0
    assert captured["init_kwargs"] == {}
    assert captured["get_kwargs"]["auto_create_facet_filters"] is False
    out = capsys.readouterr().out.splitlines()
    assert out == ["displayName", "domain", "id", "kind"]


def test_cli_assets_schema_lines_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "columns.txt"

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "x", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            return None

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["assets", "schema", "--filter", 'kind = "domain"', "--out", str(out)])
    assert rc == 0
    assert out.read_text(encoding="utf-8") == "id\nkind\n"


def test_cli_assets_schema_json_to_stdout(monkeypatch, capsys):
    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "x", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            return None

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        ["assets", "schema", "--filter", 'kind = "domain"', "--format", "json", "--out", "-"]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == ["id", "kind"]


def test_cli_assets_schema_surfaces_api_error_payload(monkeypatch, capsys):
    class ApiRequestError(Exception):
        pass

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_workspace_assets(self, **kwargs):
            raise ApiRequestError(
                'called by: get_workspace_assets -- last_status: 403 -- last_text: '
                '{"error":{"code":"Forbidden","message":"Authorization: bearer secret-token"}}'
            )

    fake_mdeasm = types.SimpleNamespace(
        Workspaces=DummyWS,
        ApiRequestError=ApiRequestError,
        redact_sensitive_text=lambda s: str(s).replace("secret-token", "[REDACTED]"),
    )
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["assets", "schema", "--filter", 'kind = "domain"', "--out", "-"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "assets schema failed" in err
    assert "status=403" in err
    assert "code=Forbidden" in err
    assert "[REDACTED]" in err


def test_cli_assets_schema_diff_json_no_drift(monkeypatch, capsys, tmp_path):
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("id\nkind\n", encoding="utf-8")

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "x", "kind": "domain"}]

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
            "schema",
            "diff",
            "--filter",
            'kind = "domain"',
            "--baseline",
            str(baseline),
            "--format",
            "json",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["has_drift"] is False
    assert payload["added"] == []
    assert payload["removed"] == []


def test_cli_assets_schema_diff_lines_fail_on_drift(monkeypatch, capsys, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(["id", "kind", "domain"]), encoding="utf-8")

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "x", "kind": "domain", "displayName": "example.com"}]

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
            "schema",
            "diff",
            "--filter",
            'kind = "domain"',
            "--baseline",
            str(baseline),
            "--fail-on-drift",
            "--out",
            "-",
        ]
    )
    assert rc == 3
    out = capsys.readouterr().out.splitlines()
    assert "drift=true" in out
    assert "+ displayName" in out
    assert "- domain" in out


def test_cli_assets_schema_diff_requires_baseline(monkeypatch, capsys):
    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "x", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            return None

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["assets", "schema", "diff", "--filter", 'kind = "domain"', "--out", "-"])
    assert rc == 2
    assert "requires --baseline" in capsys.readouterr().err


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


def test_cli_assets_export_ndjson_streams_when_available(tmp_path, monkeypatch):
    out = tmp_path / "assets.ndjson"

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.init_kwargs = dict(kwargs)

        def get_workspace_assets(self, **kwargs):
            raise AssertionError("get_workspace_assets should not be used for streaming ndjson")

        def stream_workspace_assets(self, **kwargs):
            yield {"id": "domain$$example.com", "kind": "domain"}
            yield {"id": "host$$www.example.com", "kind": "host"}

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


def test_cli_assets_export_json_stream_array_when_enabled(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_workspace_assets(self, **kwargs):
            raise AssertionError("get_workspace_assets should not be used for --stream-json-array")

        def stream_workspace_assets(self, **kwargs):
            captured["stream_kwargs"] = dict(kwargs)
            yield {"id": "domain$$example.com", "kind": "domain"}
            yield {"id": "host$$www.example.com", "kind": "host"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--filter",
            'kind in ("domain","host")',
            "--format",
            "json",
            "--stream-json-array",
            "--out",
            str(out),
            "--no-facet-filters",
        ]
    )
    assert rc == 0
    assert captured["stream_kwargs"]["query_filter"] == 'kind in ("domain","host")'
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload == [
        {"id": "domain$$example.com", "kind": "domain"},
        {"id": "host$$www.example.com", "kind": "host"},
    ]


def test_cli_assets_export_json_stream_array_requires_no_facet_filters(monkeypatch, capsys):
    class DummyAssetList:
        def as_dicts(self):
            return []

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
            "--stream-json-array",
            "--out",
            "-",
        ]
    )
    assert rc == 2
    assert "--stream-json-array requires --no-facet-filters" in capsys.readouterr().err


def test_cli_assets_export_stream_array_requires_json_format(monkeypatch, capsys):
    class DummyAssetList:
        def as_dicts(self):
            return []

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
            "ndjson",
            "--stream-json-array",
            "--out",
            "-",
            "--no-facet-filters",
        ]
    )
    assert rc == 2
    assert "--stream-json-array requires --format json" in capsys.readouterr().err


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


def test_cli_assets_export_csv_columns_streams_when_available(tmp_path, monkeypatch):
    out = tmp_path / "assets.csv"

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_workspace_assets(self, **kwargs):
            raise AssertionError("get_workspace_assets should not be used for streaming csv")

        def stream_workspace_assets(self, **kwargs):
            yield {"id": "domain$$example.com", "kind": "domain", "ports": [80, 443]}
            yield {"id": "host$$www.example.com", "kind": "host", "ports": [80]}

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


def test_cli_assets_export_resume_checkpoint_and_orderby(tmp_path, monkeypatch):
    out = tmp_path / "assets.json"
    checkpoint = tmp_path / "checkpoint.json"
    captured = {}

    class DummyAssetList:
        def as_dicts(self):
            return [{"id": "domain$$example.com", "kind": "domain"}]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self.assetList = DummyAssetList()

        def get_workspace_assets(self, **kwargs):
            captured["get_kwargs"] = dict(kwargs)
            cb = kwargs.get("progress_callback")
            if callable(cb):
                cb(
                    {
                        "next_page": 11,
                        "next_mark": "mark-11",
                        "pages_completed": 4,
                        "assets_emitted": 100,
                        "total_elements": 1000,
                        "last": False,
                    }
                )
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
            "--resume-from",
            "7",
            "--checkpoint-out",
            str(checkpoint),
            "--orderby",
            "id asc",
        ]
    )
    assert rc == 0
    assert captured["get_kwargs"]["page"] == 7
    assert captured["get_kwargs"]["orderby"] == "id asc"
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert payload["next_page"] == 11
    assert payload["next_mark"] == "mark-11"


def test_cli_assets_export_stream_resume_from_checkpoint_file(tmp_path, monkeypatch):
    out = tmp_path / "assets.ndjson"
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(
        json.dumps({"next_page": 13, "next_mark": "token-13"}, sort_keys=True), encoding="utf-8"
    )
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def stream_workspace_assets(self, **kwargs):
            captured["stream_kwargs"] = dict(kwargs)
            yield {"id": "domain$$example.com", "kind": "domain"}

        def get_workspace_assets(self, **kwargs):
            raise AssertionError("get_workspace_assets should not be used for streaming ndjson")

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--filter",
            'kind = "domain"',
            "--format",
            "ndjson",
            "--out",
            str(out),
            "--no-facet-filters",
            "--resume-from",
            f"@{checkpoint}",
        ]
    )
    assert rc == 0
    assert captured["stream_kwargs"]["page"] == 13
    assert captured["stream_kwargs"]["mark"] == "token-13"


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


def test_cli_workspaces_list_json_to_stdout(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self._workspaces = {
                "wsB": ("https://dp/wsB", "management.azure.com/wsB"),
                "wsA": ("https://dp/wsA", "management.azure.com/wsA"),
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["workspaces", "list", "--format", "json", "--out", "-"])
    assert rc == 0
    assert captured["init_kwargs"] == {
        "workspace_name": "",
        "init_data_plane_token": False,
        "emit_workspace_guidance": False,
    }

    payload = json.loads(capsys.readouterr().out)
    assert [w["name"] for w in payload] == ["wsA", "wsB"]
    assert payload[0]["dataPlane"].startswith("https://dp/")


def test_cli_workspaces_list_lines_to_stdout(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._workspaces = {"ws1": ("https://dp/ws1", "management.azure.com/ws1")}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["workspaces", "list", "--format", "lines", "--out", "-"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("ws1\t")


def test_cli_workspaces_delete_json_with_yes(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self._workspaces = {"ws1": ("https://dp/ws1", "management.azure.com/ws1")}

        def delete_workspace(self, **kwargs):
            captured["delete_kwargs"] = dict(kwargs)
            return {"deleted": "ws1", "resourceGroup": "rg0", "statusCode": 204}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        ["workspaces", "delete", "ws1", "--yes", "--format", "json", "--out", "-"]
    )
    assert rc == 0
    assert captured["init_kwargs"] == {
        "workspace_name": "",
        "init_data_plane_token": False,
        "emit_workspace_guidance": False,
    }
    assert captured["delete_kwargs"] == {
        "workspace_name": "ws1",
        "resource_group_name": "",
        "noprint": True,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["deleted"] == "ws1"
    assert payload["statusCode"] == 204


def test_cli_workspaces_delete_requires_yes_in_noninteractive_mode(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._workspaces = {}

        def delete_workspace(self, **kwargs):
            raise AssertionError("delete_workspace should not be called")

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["workspaces", "delete", "ws1"])
    assert rc == 2
    assert "refusing to delete workspace without --yes" in capsys.readouterr().err


def test_cli_workspaces_delete_aborts_when_confirmation_mismatch(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._workspaces = {"ws1": ("https://dp/ws1", "management.azure.com/ws1")}

        def delete_workspace(self, **kwargs):
            raise AssertionError("delete_workspace should not be called")

    class DummyInput:
        def isatty(self):
            return True

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(sys, "stdin", DummyInput())
    monkeypatch.setattr("builtins.input", lambda _prompt: "wrong-name")

    rc = mdeasm_cli.main(["workspaces", "delete", "ws1"])
    assert rc == 1
    assert "aborted: confirmation did not match workspace name" in capsys.readouterr().err
