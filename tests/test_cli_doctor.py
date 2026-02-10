import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


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

    # Probe should not require data-plane token.
    assert captured["init_kwargs"]["init_data_plane_token"] is False
    assert captured["init_kwargs"]["emit_workspace_guidance"] is False
    assert captured["init_kwargs"]["workspace_name"] == ""

