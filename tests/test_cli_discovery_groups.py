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


def test_cli_discovery_groups_create_template_lines(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def create_discovery_group(self, **kwargs):
            captured["create"] = dict(kwargs)
            return {
                "Contoso": [
                    {
                        "state": "complete",
                        "submittedDate": "2026-02-11T00:00:00Z",
                        "completedDate": "2026-02-11T00:10:00Z",
                        "totalAssetsFoundCount": 12,
                    }
                ]
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "discovery-groups",
            "create",
            "--template",
            "Contoso---tmpl-123",
            "--workspace-name",
            "ws1",
            "--format",
            "lines",
            "--disco-runs-max-retry",
            "5",
            "--disco-runs-backoff-max-s",
            "9",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert captured["create"] == {
        "disco_template": "Contoso---tmpl-123",
        "disco_custom": {},
        "workspace_name": "ws1",
        "disco_runs_max_retry": 5,
        "disco_runs_backoff_max_s": 9.0,
        "noprint": True,
    }
    assert (
        capsys.readouterr().out.strip()
        == "Contoso\tcomplete\t2026-02-11T00:00:00Z\t2026-02-11T00:10:00Z\t12"
    )


def test_cli_discovery_groups_create_custom_json_file(monkeypatch, capsys, tmp_path):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def create_discovery_group(self, **kwargs):
            captured["create"] = dict(kwargs)
            return {"Contoso seeds": []}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    payload_path = tmp_path / "discovery_custom.json"
    payload_path.write_text(
        json.dumps({"name": "Contoso", "seeds": {"domain": ["contoso.com"]}}),
        encoding="utf-8",
    )

    rc = mdeasm_cli.main(
        [
            "discovery-groups",
            "create",
            "--custom-json-file",
            str(payload_path),
            "--workspace-name",
            "ws1",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert captured["create"]["disco_template"] == ""
    assert captured["create"]["workspace_name"] == "ws1"
    assert captured["create"]["noprint"] is True
    assert captured["create"]["disco_custom"] == {
        "name": "Contoso",
        "seeds": {"domain": ["contoso.com"]},
    }
    assert json.loads(capsys.readouterr().out) == {"Contoso seeds": []}


def test_cli_discovery_groups_run_json(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def run_discovery_group(self, name, **kwargs):
            captured["run"] = {"name": name, **kwargs}
            return {"Contoso": [{"state": "running"}]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "discovery-groups",
            "run",
            "Contoso",
            "--workspace-name",
            "ws1",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert captured["run"] == {
        "name": "Contoso",
        "workspace_name": "ws1",
        "disco_runs_max_retry": 3,
        "disco_runs_backoff_max_s": 5.0,
        "noprint": True,
    }
    assert json.loads(capsys.readouterr().out) == {"Contoso": [{"state": "running"}]}


def test_cli_discovery_groups_create_rejects_invalid_custom_json(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "discovery-groups",
            "create",
            "--custom-json",
            "{broken",
            "--workspace-name",
            "ws1",
            "--out",
            "-",
        ]
    )
    assert rc == 2
    assert "invalid discovery group arguments" in capsys.readouterr().err


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
