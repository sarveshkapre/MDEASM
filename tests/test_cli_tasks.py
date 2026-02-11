import json
import hashlib
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_resolve_cli_log_level_prefers_explicit_over_verbose():
    args = types.SimpleNamespace(log_level="WARNING", verbose=2)
    assert mdeasm_cli._resolve_cli_log_level(args) == "WARNING"


def test_resolve_out_path_treats_dash_as_stdout():
    assert mdeasm_cli._resolve_out_path("-") is None
    assert mdeasm_cli._resolve_out_path("") is None
    assert mdeasm_cli._resolve_out_path("result.json") == Path("result.json")


def test_rows_to_tab_lines_normalizes_control_whitespace():
    lines = mdeasm_cli._rows_to_tab_lines(
        [{"id": "a\tb", "state": "line1\nline2", "detail": " c\r\nd "}],
        ["id", "state", "detail"],
    )
    assert lines == ["a b\tline1 line2\tc d"]


def test_parse_retry_after_seconds_supports_delay_and_http_date():
    now = datetime(2026, 2, 11, 0, 0, 0, tzinfo=timezone.utc)

    assert mdeasm_cli._parse_retry_after_seconds("5", now=now) == 5
    assert mdeasm_cli._parse_retry_after_seconds("Wed, 11 Feb 2026 00:00:03 GMT", now=now) == 3


def test_parse_retry_after_seconds_handles_invalid_and_past_values():
    now = datetime(2026, 2, 11, 0, 0, 0, tzinfo=timezone.utc)

    assert mdeasm_cli._parse_retry_after_seconds("", now=now) is None
    assert mdeasm_cli._parse_retry_after_seconds("invalid", now=now) is None
    assert mdeasm_cli._parse_retry_after_seconds("Tue, 10 Feb 2026 23:59:59 GMT", now=now) == 0


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


def test_cli_tasks_list_content_fallback(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def list_tasks(self, **kwargs):
            return {"content": [{"id": "t-content", "state": "queued"}]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["tasks", "list", "--format", "json", "--out", "-"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == [{"id": "t-content", "state": "queued"}]


def test_cli_tasks_list_surfaces_api_error_payload(monkeypatch, capsys):
    class ApiRequestError(Exception):
        pass

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def list_tasks(self, **kwargs):
            raise ApiRequestError(
                'called by: list_tasks -- last_status: 429 -- last_text: '
                '{"error":{"code":"TooManyRequests","message":"Bearer abc123 throttled"}}'
            )

    fake_mdeasm = types.SimpleNamespace(
        Workspaces=DummyWS,
        ApiRequestError=ApiRequestError,
        redact_sensitive_text=lambda s: str(s).replace("abc123", "[REDACTED]"),
    )
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["tasks", "list", "--format", "json", "--out", "-"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "tasks list failed" in err
    assert "status=429" in err
    assert "code=TooManyRequests" in err
    assert "message=Bearer [REDACTED] throttled" in err


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


def test_cli_tasks_wait_json_surfaces_terminal_failure_details(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_task(self, task_id, **kwargs):
            return {
                "id": task_id,
                "state": "failed",
                "error": {
                    "code": "ExportFailed",
                    "message": "artifact generation failed for workspace demo",
                },
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["tasks", "wait", "abc", "--format", "json", "--out", "-"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "failed"
    assert payload["terminalErrorCode"] == "ExportFailed"
    assert payload["terminalErrorMessage"] == "artifact generation failed for workspace demo"


def test_cli_tasks_wait_lines_surfaces_terminal_failure_details(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_task(self, task_id, **kwargs):
            return {
                "id": task_id,
                "state": "incomplete",
                "result": {
                    "error": {
                        "code": "DownloadUnavailable",
                        "message": "download URL not ready",
                    }
                },
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["tasks", "wait", "abc", "--format", "lines", "--out", "-"])
    assert rc == 0
    line = capsys.readouterr().out.strip()
    fields = line.split("\t")
    assert fields[0] == "abc"
    assert fields[1] == "incomplete"
    assert fields[4] == "DownloadUnavailable"
    assert fields[5] == "download URL not ready"


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


def test_cli_tasks_fetch_retries_with_bearer_for_protected_url(monkeypatch, capsys, tmp_path):
    artifact = tmp_path / "artifact.csv"
    calls = []

    class DummyWS:
        def __init__(self, *args, **kwargs):
            self._http_timeout = (1.0, 5.0)
            self._default_max_retry = 1
            self._backoff_max_s = 0.01
            self._dp_token = "token-abc"

        def download_task(self, task_id, **kwargs):
            return {"id": task_id, "downloadUrl": "https://files.example.test/protected.csv"}

    class ForbiddenResp:
        status_code = 403
        text = "forbidden"

        def iter_content(self, chunk_size=65536):
            return iter([])

        def close(self):
            return None

    class OkResp:
        status_code = 200
        text = ""

        def iter_content(self, chunk_size=65536):
            yield b"col1\n"
            yield b"ok\n"

        def close(self):
            return None

    def fake_get(url, **kwargs):
        calls.append(kwargs.get("headers"))
        if kwargs.get("headers") is None:
            return ForbiddenResp()
        assert kwargs["headers"]["Authorization"] == "Bearer token-abc"
        return OkResp()

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS, redact_sensitive_text=lambda s: s)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)
    monkeypatch.setattr(mdeasm_cli.requests, "get", fake_get)

    rc = mdeasm_cli.main(["tasks", "fetch", "abc", "--artifact-out", str(artifact), "--out", "-"])
    assert rc == 0
    assert calls == [None, {"Authorization": "Bearer token-abc"}]
    assert artifact.read_bytes() == b"col1\nok\n"
    payload = json.loads(capsys.readouterr().out)
    assert payload["used_bearer_auth"] is True


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
    err = capsys.readouterr().err
    assert "tasks fetch failed" in err
    assert "status=404" in err


def test_cli_tasks_fetch_respects_retry_after_header(monkeypatch, capsys, tmp_path):
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
        headers = {"Retry-After": "2"}

        def iter_content(self, chunk_size=65536):
            return iter([])

        def close(self):
            return None

    class OkResp:
        status_code = 200
        text = ""
        headers = {}

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

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(mdeasm_cli.time, "sleep", fake_sleep)

    rc = mdeasm_cli.main(["tasks", "fetch", "abc", "--artifact-out", str(artifact), "--out", "-"])
    assert rc == 0
    assert calls["count"] == 2
    assert sleep_calls == [2.0]
    assert artifact.read_bytes() == b"ok\n"
    payload = json.loads(capsys.readouterr().out)
    assert payload["status_code"] == 200


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
