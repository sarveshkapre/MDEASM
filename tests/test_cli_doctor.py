import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_parse_doctor_probe_targets():
    assert mdeasm_cli._parse_doctor_probe_targets("workspaces") == ["workspaces"]
    assert mdeasm_cli._parse_doctor_probe_targets("assets,tasks") == ["assets", "tasks"]
    assert mdeasm_cli._parse_doctor_probe_targets("all") == [
        "workspaces",
        "assets",
        "tasks",
        "data-connections",
    ]


def test_cli_doctor_missing_required_env(monkeypatch, capsys):
    for k in ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]:
        monkeypatch.delenv(k, raising=False)

    rc = mdeasm_cli.main(["doctor", "--format", "json"])
    assert rc == 1

    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert set(out["checks"]["env"]["missing_required"]) == {
        "TENANT_ID",
        "SUBSCRIPTION_ID",
        "CLIENT_ID",
        "CLIENT_SECRET",
    }
    # Never echo the client secret in diagnostics.
    assert out["checks"]["env"]["values"]["CLIENT_SECRET"] == {"set": False}


def test_cli_doctor_probe_uses_control_plane_only(monkeypatch, capsys):
    # Provide dummy required env vars so doctor can attempt a probe.
    monkeypatch.setenv("TENANT_ID", "t")
    monkeypatch.setenv("SUBSCRIPTION_ID", "s")
    monkeypatch.setenv("CLIENT_ID", "c")
    monkeypatch.setenv("CLIENT_SECRET", "secret")

    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            # Match the real helper shape: mapping workspaceName -> (dp, cp).
            self._workspaces = {"wsA": ("dp", "cp"), "wsB": ("dp", "cp")}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["doctor", "--probe", "--format", "json"])
    assert rc == 0

    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["checks"]["probe"]["ok"] is True
    assert out["checks"]["probe"]["workspaces"]["count"] == 2
    assert out["checks"]["probe"]["workspaces"]["names"] == ["wsA", "wsB"]
    assert out["checks"]["probe"]["results"]["workspaces"]["elapsedMs"] >= 0
    assert out["checks"]["probe"]["summary"]["targetCount"] == 1
    assert out["checks"]["probe"]["summary"]["okCount"] == 1

    # Probe should not require data-plane token.
    assert captured["init_kwargs"]["init_data_plane_token"] is False
    assert captured["init_kwargs"]["emit_workspace_guidance"] is False
    assert captured["init_kwargs"]["workspace_name"] == ""


def test_cli_doctor_probe_matrix_all_targets(monkeypatch, capsys):
    monkeypatch.setenv("TENANT_ID", "t")
    monkeypatch.setenv("SUBSCRIPTION_ID", "s")
    monkeypatch.setenv("CLIENT_ID", "c")
    monkeypatch.setenv("CLIENT_SECRET", "secret")
    monkeypatch.setenv("WORKSPACE_NAME", "wsA")

    captured = {"assets_calls": []}

    class DummyAssetList:
        def __init__(self, count):
            self.assets = [{} for _ in range(count)]

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)
            self._workspaces = {"wsA": ("dp", "cp")}
            self._default_workspace_name = "wsA"

        def get_workspace_assets(self, **kwargs):
            captured["assets_calls"].append(kwargs)
            setattr(self, kwargs["asset_list_name"], DummyAssetList(1))

        def list_tasks(self, **kwargs):
            captured["tasks_kwargs"] = dict(kwargs)
            return {"value": [{"id": "task-1"}, {"id": "task-2"}]}

        def list_data_connections(self, **kwargs):
            captured["dc_kwargs"] = dict(kwargs)
            return {"value": [{"name": "dc-1"}]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "doctor",
            "--probe",
            "--probe-targets",
            "all",
            "--probe-max-page-size",
            "2",
            "--format",
            "json",
        ]
    )
    assert rc == 0

    out = json.loads(capsys.readouterr().out)
    probe = out["checks"]["probe"]
    assert probe["ok"] is True
    assert probe["targets"] == ["workspaces", "assets", "tasks", "data-connections"]
    assert probe["workspaces"]["count"] == 1
    assert probe["results"]["assets"]["count"] == 1
    assert probe["results"]["tasks"]["count"] == 2
    assert probe["results"]["data-connections"]["count"] == 1
    assert probe["results"]["workspaces"]["elapsedMs"] >= 0
    assert probe["results"]["assets"]["elapsedMs"] >= 0
    assert probe["results"]["tasks"]["elapsedMs"] >= 0
    assert probe["results"]["data-connections"]["elapsedMs"] >= 0
    assert probe["summary"]["targetCount"] == 4
    assert probe["summary"]["okCount"] == 4
    assert probe["summary"]["failedCount"] == 0
    assert probe["summary"]["totalElapsedMs"] >= 0
    assert probe["summary"]["slowestTarget"] in {
        "workspaces",
        "assets",
        "tasks",
        "data-connections",
    }

    assert captured["init_kwargs"]["emit_workspace_guidance"] is False
    assert captured["init_kwargs"].get("workspace_name", "") == ""
    assert "init_data_plane_token" not in captured["init_kwargs"]
    assert captured["assets_calls"][0]["workspace_name"] == "wsA"
    assert captured["tasks_kwargs"]["workspace_name"] == "wsA"
    assert captured["dc_kwargs"]["workspace_name"] == "wsA"


def test_cli_doctor_probe_invalid_target_returns_2(monkeypatch, capsys):
    monkeypatch.setenv("TENANT_ID", "t")
    monkeypatch.setenv("SUBSCRIPTION_ID", "s")
    monkeypatch.setenv("CLIENT_ID", "c")
    monkeypatch.setenv("CLIENT_SECRET", "secret")

    rc = mdeasm_cli.main(
        ["doctor", "--probe", "--probe-targets", "workspaces,unknown-target", "--format", "json"]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "invalid --probe-targets" in err
