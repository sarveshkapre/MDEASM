import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_cli_resource_tags_list_json(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)

        def list_resource_tags(self, **kwargs):
            captured["list_kwargs"] = dict(kwargs)
            return {"workspaceName": "ws1", "tags": {"Owner": "SecOps", "Environment": "Prod"}}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["resource-tags", "list", "--workspace-name", "ws1", "--out", "-"])
    assert rc == 0
    assert captured["init_kwargs"]["init_data_plane_token"] is False
    assert captured["list_kwargs"] == {"workspace_name": "ws1", "noprint": True}

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspaceName"] == "ws1"
    assert payload["tags"]["Owner"] == "SecOps"


def test_cli_resource_tags_list_lines(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def list_resource_tags(self, **kwargs):
            return {"workspaceName": "ws1", "tags": {"Environment": "Prod", "Owner": "SecOps"}}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        ["resource-tags", "list", "--workspace-name", "ws1", "--format", "lines", "--out", "-"]
    )
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["ws1\tEnvironment\tProd", "ws1\tOwner\tSecOps"]


def test_cli_resource_tags_get_lines(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_resource_tag(self, name, **kwargs):
            assert name == "Owner"
            return {"workspaceName": "ws1", "name": "Owner", "value": "SecOps"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "resource-tags",
            "get",
            "Owner",
            "--workspace-name",
            "ws1",
            "--format",
            "lines",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ws1\tOwner\tSecOps"


def test_cli_resource_tags_put_json(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def put_resource_tag(self, name, value, **kwargs):
            captured["put"] = {"name": name, "value": value, **kwargs}
            return {
                "workspaceName": "ws1",
                "name": "Environment",
                "value": "Prod",
                "tags": {"Owner": "SecOps", "Environment": "Prod"},
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "resource-tags",
            "put",
            "Environment",
            "--value",
            "Prod",
            "--workspace-name",
            "ws1",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert captured["put"] == {
        "name": "Environment",
        "value": "Prod",
        "workspace_name": "ws1",
        "noprint": True,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["value"] == "Prod"


def test_cli_resource_tags_delete_lines(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def delete_resource_tag(self, name, **kwargs):
            assert name == "Owner"
            return {"workspaceName": "ws1", "name": "Owner", "deleted": True, "tags": {}}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "resource-tags",
            "delete",
            "Owner",
            "--workspace-name",
            "ws1",
            "--format",
            "lines",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ws1\tOwner\tTrue"


def test_cli_resource_tags_get_surfaces_api_error_payload(monkeypatch, capsys):
    class ApiRequestError(Exception):
        pass

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_resource_tag(self, name, **kwargs):
            raise ApiRequestError(
                'called by: get_resource_tag -- last_status: 403 -- last_text: '
                '{"error":{"code":"AuthorizationFailed","message":"missing permissions"}}'
            )

    fake_mdeasm = types.SimpleNamespace(
        Workspaces=DummyWS,
        ApiRequestError=ApiRequestError,
        redact_sensitive_text=lambda s: s,
    )
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        ["resource-tags", "get", "Owner", "--workspace-name", "ws1", "--out", "-"]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "resource-tags get failed" in err
    assert "status=403" in err
    assert "code=AuthorizationFailed" in err
