import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_cli_data_connections_list_json(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def list_data_connections(self, **kwargs):
            return {"value": [{"name": "dc1", "kind": "logAnalytics", "content": "assets"}]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["data-connections", "list", "--format", "json", "--out", "-"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == [{"name": "dc1", "kind": "logAnalytics", "content": "assets"}]


def test_cli_data_connections_list_lines(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def list_data_connections(self, **kwargs):
            return {
                "value": [
                    {
                        "name": "dc1",
                        "kind": "logAnalytics",
                        "content": "assets",
                        "frequency": "weekly",
                        "frequencyOffset": 1,
                        "provisioningState": "Succeeded",
                    }
                ]
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["data-connections", "list", "--format", "lines", "--out", "-"])
    assert rc == 0
    out_lines = capsys.readouterr().out.splitlines()
    assert out_lines == ["dc1\tlogAnalytics\tassets\tweekly\t1\tSucceeded"]


def test_cli_data_connections_list_content_fallback(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def list_data_connections(self, **kwargs):
            return {"content": [{"name": "dc-content", "kind": "azureDataExplorer"}]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["data-connections", "list", "--format", "json", "--out", "-"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == [{"name": "dc-content", "kind": "azureDataExplorer"}]


def test_cli_data_connections_get_surfaces_api_error_payload(monkeypatch, capsys):
    class ApiRequestError(Exception):
        pass

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_data_connection(self, name, **kwargs):
            raise ApiRequestError(
                'called by: get_data_connection -- last_status: 404 -- last_text: '
                '{"error":{"code":"DataConnectionNotFound","message":"connection dc-missing not found"}}'
            )

    fake_mdeasm = types.SimpleNamespace(
        Workspaces=DummyWS,
        ApiRequestError=ApiRequestError,
        redact_sensitive_text=lambda s: s,
    )
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["data-connections", "get", "dc-missing", "--out", "-"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "data-connections get failed" in err
    assert "status=404" in err
    assert "code=DataConnectionNotFound" in err


def test_cli_data_connections_put_log_analytics(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def create_or_replace_data_connection(self, name, **kwargs):
            captured["name"] = name
            captured["kwargs"] = dict(kwargs)
            return {"name": name, "kind": kwargs["kind"]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "data-connections",
            "put",
            "dc-la",
            "--kind",
            "logAnalytics",
            "--workspace-id",
            "workspace-id-123",
            "--api-key",
            "secret-key",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "dc-la"
    assert captured["name"] == "dc-la"
    assert captured["kwargs"]["properties"] == {
        "workspaceId": "workspace-id-123",
        "apiKey": "secret-key",
    }


def test_cli_data_connections_put_missing_required_argument(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "data-connections",
            "put",
            "dc-la",
            "--kind",
            "logAnalytics",
            "--workspace-id",
            "workspace-id-123",
            "--out",
            "-",
        ]
    )
    assert rc == 2
    assert "requires --api-key" in capsys.readouterr().err


def test_cli_data_connections_validate_and_delete(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def validate_data_connection(self, **kwargs):
            return {"valid": True, "name": kwargs.get("name", "")}

        def delete_data_connection(self, name, **kwargs):
            return {"deleted": name, "status": 204}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc_validate = mdeasm_cli.main(
        [
            "data-connections",
            "validate",
            "dc-adx",
            "--kind",
            "azureDataExplorer",
            "--cluster-name",
            "clusterA",
            "--database-name",
            "dbA",
            "--region",
            "eastus",
            "--out",
            "-",
        ]
    )
    assert rc_validate == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    rc_delete = mdeasm_cli.main(
        ["data-connections", "delete", "dc-adx", "--format", "text", "--out", "-"]
    )
    assert rc_delete == 0
    assert capsys.readouterr().out.splitlines() == ["deleted dc-adx"]


def test_cli_data_connections_delete_lines(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def delete_data_connection(self, name, **kwargs):
            assert name == "dc-adx"
            return {"deleted": name, "status": 204}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        ["data-connections", "delete", "dc-adx", "--format", "lines", "--out", "-"]
    )
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == ["dc-adx\t204"]
