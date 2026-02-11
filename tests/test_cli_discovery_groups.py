import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_cli_discovery_groups_list_json_get_all(monkeypatch, capsys):
    captured = {"calls": []}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)

        def get_discovery_groups(self, **kwargs):
            captured["calls"].append(dict(kwargs))
            skip = int(kwargs.get("skip") or 0)
            if skip == 0:
                return {
                    "content": [{"name": "GroupA", "tier": "basic", "state": "active", "seeds": []}],
                    "totalElements": 2,
                }
            return {
                "content": [
                    {"name": "GroupB", "tier": "advanced", "state": "active", "seeds": [{}]}
                ],
                "totalElements": 2,
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "discovery-groups",
            "list",
            "--workspace-name",
            "ws1",
            "--get-all",
            "--max-page-size",
            "1",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert captured["init_kwargs"]["workspace_name"] == "ws1"
    assert captured["calls"] == [
        {
            "workspace_name": "ws1",
            "filter_expr": "",
            "skip": 0,
            "max_page_size": 1,
            "noprint": True,
        },
        {
            "workspace_name": "ws1",
            "filter_expr": "",
            "skip": 1,
            "max_page_size": 1,
            "noprint": True,
        },
    ]
    payload = json.loads(capsys.readouterr().out)
    assert [row["name"] for row in payload] == ["GroupA", "GroupB"]


def test_cli_discovery_groups_list_lines(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_discovery_groups(self, **kwargs):
            return {
                "content": [
                    {
                        "name": "Contoso Seeds",
                        "tier": "advanced",
                        "state": "active",
                        "seeds": [{"kind": "domain", "name": "contoso.com"}],
                    }
                ]
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        ["discovery-groups", "list", "--workspace-name", "ws1", "--format", "lines", "--out", "-"]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "Contoso Seeds\tadvanced\tactive\t1"


def test_cli_discovery_groups_delete_lines(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def delete_discovery_group(self, name, **kwargs):
            captured["delete"] = {"name": name, **kwargs}
            return {
                "workspaceName": "ws1",
                "name": "Contoso Seeds",
                "deleted": True,
                "status": 204,
                "verifiedDeleted": False,
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "discovery-groups",
            "delete",
            "Contoso Seeds",
            "--workspace-name",
            "ws1",
            "--format",
            "lines",
            "--no-verify-delete",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert captured["delete"] == {
        "name": "Contoso Seeds",
        "workspace_name": "ws1",
        "verify_deleted": False,
        "verify_max_retry": 3,
        "verify_backoff_max_s": 5.0,
        "noprint": True,
    }
    assert capsys.readouterr().out.strip() == "ws1\tContoso Seeds\tTrue\tFalse\t204"


def test_cli_discovery_groups_list_surfaces_api_error_payload(monkeypatch, capsys):
    class ApiRequestError(Exception):
        pass

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_discovery_groups(self, **kwargs):
            raise ApiRequestError(
                'called by: get_discovery_groups -- last_status: 403 -- last_text: '
                '{"error":{"code":"AuthorizationFailed","message":"missing permissions"}}'
            )

    fake_mdeasm = types.SimpleNamespace(
        Workspaces=DummyWS,
        ApiRequestError=ApiRequestError,
        redact_sensitive_text=lambda s: s,
    )
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        ["discovery-groups", "list", "--workspace-name", "ws1", "--out", "-"]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "discovery-groups list failed" in err
    assert "status=403" in err
    assert "code=AuthorizationFailed" in err
