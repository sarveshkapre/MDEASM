import json
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_cli_tasks_list_json(monkeypatch, capsys):
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            captured["init_kwargs"] = dict(kwargs)

        def list_tasks(self, **kwargs):
            captured["list_kwargs"] = dict(kwargs)
            return {"value": [{"id": "t1", "state": "running"}]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["tasks", "list", "--format", "json", "--get-all", "--out", "-"])
    assert rc == 0
    assert captured["list_kwargs"]["get_all"] is True
    payload = json.loads(capsys.readouterr().out)
    assert payload == [{"id": "t1", "state": "running"}]


def test_cli_tasks_get_cancel_run_download(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_task(self, task_id, **kwargs):
            return {"id": task_id, "state": "running"}

        def cancel_task(self, task_id, **kwargs):
            return {"id": task_id, "state": "cancelled"}

        def run_task(self, task_id, **kwargs):
            return {"id": task_id, "state": "running"}

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://example.test/file"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    assert mdeasm_cli.main(["tasks", "get", "abc", "--out", "-"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "abc"

    assert mdeasm_cli.main(["tasks", "cancel", "abc", "--out", "-"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "cancelled"

    assert mdeasm_cli.main(["tasks", "run", "abc", "--out", "-"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "running"

    assert mdeasm_cli.main(["tasks", "download", "abc", "--out", "-"]) == 0
    assert "downloadUrl" in json.loads(capsys.readouterr().out)


def test_cli_assets_export_server_mode_wait_download(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._get_calls = 0

        def create_assets_export_task(self, **kwargs):
            return {"id": "task-1", "state": "notStarted"}

        def get_task(self, task_id, **kwargs):
            self._get_calls += 1
            if self._get_calls == 1:
                return {"id": task_id, "state": "running"}
            return {"id": task_id, "state": "complete"}

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://example.test/file"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--mode",
            "server",
            "--filter",
            'kind = "domain"',
            "--columns",
            "id",
            "--columns",
            "kind",
            "--wait",
            "--poll-interval-s",
            "0.01",
            "--wait-timeout-s",
            "1",
            "--download-on-complete",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["task"]["state"] == "complete"
    assert "downloadUrl" in payload["download"]


def test_cli_assets_export_server_mode_requires_columns(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--mode",
            "server",
            "--filter",
            'kind = "domain"',
            "--out",
            "-",
        ]
    )
    assert rc == 2
    assert "requires --columns or --columns-from" in capsys.readouterr().err
