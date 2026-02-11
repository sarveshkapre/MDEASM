import json
import hashlib
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


def test_cli_tasks_wait_returns_terminal_payload(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._calls = 0

        def get_task(self, task_id, **kwargs):
            self._calls += 1
            if self._calls == 1:
                return {"id": task_id, "state": "running"}
            return {"id": task_id, "state": "complete", "completedAt": "2026-01-01T00:00:00Z"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "tasks",
            "wait",
            "abc",
            "--poll-interval-s",
            "0.01",
            "--timeout-s",
            "1",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "abc"
    assert out["state"] == "complete"


def test_cli_tasks_wait_times_out(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_task(self, task_id, **kwargs):
            return {"id": task_id, "state": "running"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "tasks",
            "wait",
            "abc",
            "--poll-interval-s",
            "0.01",
            "--timeout-s",
            "0.01",
            "--out",
            "-",
        ]
    )
    assert rc == 1
    assert "timed out waiting for task abc" in capsys.readouterr().err


def test_cli_tasks_fetch_downloads_artifact(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._http_timeout = (1.0, 5.0)
            self._default_max_retry = 2
            self._backoff_max_s = 0.01
            self._dp_token = "token-abc"

        def download_task(self, task_id, **kwargs):
            return {
                "id": task_id,
                "result": {"downloadUrl": "https://files.example.test/export.csv?sig=secret"},
            }

    class FakeResp:
        status_code = 200
        text = ""

        def iter_content(self, chunk_size=65536):
            assert chunk_size == 65536
            yield b"col1,col2\n"
            yield b"a,b\n"

        def close(self):
            return None

    def fake_get(url, **kwargs):
        assert "files.example.test" in url
        assert kwargs["stream"] is True
        assert kwargs["allow_redirects"] is True
        return FakeResp()

    fake_mdeasm = types.SimpleNamespace(
        Workspaces=DummyWS,
        redact_sensitive_text=lambda s: str(s).replace("sig=secret", "sig=[REDACTED]"),
    )
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(mdeasm_cli.requests, "get", fake_get)

    rc = mdeasm_cli.main(
        [
            "tasks",
            "fetch",
            "abc",
            "--artifact-out",
            str(artifact),
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert artifact.read_bytes() == b"col1,col2\na,b\n"
    payload = json.loads(capsys.readouterr().out)
    assert payload["task_id"] == "abc"
    assert payload["bytes_written"] == len(b"col1,col2\na,b\n")
    assert payload["download_url"].endswith("sig=[REDACTED]")


def test_cli_tasks_fetch_verifies_sha256(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"
    expected_sha = hashlib.sha256(b"col1,col2\na,b\n").hexdigest()

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._http_timeout = (1.0, 5.0)
            self._default_max_retry = 2
            self._backoff_max_s = 0.01
            self._dp_token = ""

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://files.example.test/export.csv"}

    class FakeResp:
        status_code = 200
        text = ""

        def iter_content(self, chunk_size=65536):
            yield b"col1,col2\n"
            yield b"a,b\n"

        def close(self):
            return None

    def fake_get(url, **kwargs):
        return FakeResp()

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, redact_sensitive_text=lambda s: s)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(mdeasm_cli.requests, "get", fake_get)

    rc = mdeasm_cli.main(
        [
            "tasks",
            "fetch",
            "abc",
            "--artifact-out",
            str(artifact),
            "--sha256",
            expected_sha,
            "--out",
            "-",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sha256"] == expected_sha
    assert payload["sha256_verified"] is True


def test_cli_tasks_fetch_fails_when_sha256_mismatch(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._http_timeout = (1.0, 5.0)
            self._default_max_retry = 2
            self._backoff_max_s = 0.01
            self._dp_token = ""

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://files.example.test/export.csv"}

    class FakeResp:
        status_code = 200
        text = ""

        def iter_content(self, chunk_size=65536):
            yield b"col1,col2\n"
            yield b"a,b\n"

        def close(self):
            return None

    def fake_get(url, **kwargs):
        return FakeResp()

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, redact_sensitive_text=lambda s: s)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(mdeasm_cli.requests, "get", fake_get)

    rc = mdeasm_cli.main(
        [
            "tasks",
            "fetch",
            "abc",
            "--artifact-out",
            str(artifact),
            "--sha256",
            "0" * 64,
            "--out",
            "-",
        ]
    )
    assert rc == 1
    assert "sha256 mismatch" in capsys.readouterr().err
    assert not artifact.exists()


def test_cli_tasks_fetch_rejects_invalid_sha256_argument(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._http_timeout = (1.0, 5.0)
            self._default_max_retry = 2
            self._backoff_max_s = 0.01
            self._dp_token = ""

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://files.example.test/export.csv"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, redact_sensitive_text=lambda s: s)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "tasks",
            "fetch",
            "abc",
            "--artifact-out",
            str(artifact),
            "--sha256",
            "invalid",
            "--out",
            "-",
        ]
    )
    assert rc == 2
    assert "invalid --sha256" in capsys.readouterr().err
    assert not artifact.exists()


def test_cli_tasks_fetch_fails_when_download_url_missing(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "metadata": {"note": "no URL here"}}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "tasks",
            "fetch",
            "abc",
            "--artifact-out",
            str(artifact),
            "--out",
            "-",
        ]
    )
    assert rc == 1
    assert "did not contain a usable artifact URL" in capsys.readouterr().err


def test_cli_tasks_fetch_retries_on_transient_status(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"
    calls = {"count": 0}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._http_timeout = (1.0, 5.0)
            self._default_max_retry = 3
            self._backoff_max_s = 0.0
            self._dp_token = ""

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://files.example.test/export.csv"}

    class RetryResp:
        status_code = 503
        text = "busy"

        def iter_content(self, chunk_size=65536):
            return iter([])

        def close(self):
            return None

    class OkResp:
        status_code = 200
        text = ""

        def iter_content(self, chunk_size=65536):
            yield b"ok\n"

        def close(self):
            return None

    def fake_get(url, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return RetryResp()
        return OkResp()

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, redact_sensitive_text=lambda s: s)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(mdeasm_cli.requests, "get", fake_get)

    rc = mdeasm_cli.main(["tasks", "fetch", "abc", "--artifact-out", str(artifact), "--out", "-"])
    assert rc == 0
    assert calls["count"] == 2
    assert artifact.read_bytes() == b"ok\n"
    payload = json.loads(capsys.readouterr().out)
    assert payload["status_code"] == 200


def test_cli_tasks_fetch_does_not_retry_non_retryable_status(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"
    calls = {"count": 0}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._http_timeout = (1.0, 5.0)
            self._default_max_retry = 5
            self._backoff_max_s = 0.0
            self._dp_token = ""

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://files.example.test/export.csv"}

    class NotFoundResp:
        status_code = 404
        text = "missing"

        def iter_content(self, chunk_size=65536):
            return iter([])

        def close(self):
            return None

    def fake_get(url, **kwargs):
        calls["count"] += 1
        return NotFoundResp()

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, redact_sensitive_text=lambda s: s)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(mdeasm_cli.requests, "get", fake_get)

    rc = mdeasm_cli.main(["tasks", "fetch", "abc", "--artifact-out", str(artifact), "--out", "-"])
    assert rc == 1
    assert calls["count"] == 1
    assert "artifact fetch failed" in capsys.readouterr().err


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
