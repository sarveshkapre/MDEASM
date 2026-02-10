import base64
import sys
import time
from pathlib import Path
from unittest import mock

import jwt


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm  # noqa: E402


def _new_ws():
    ws = mdeasm.Workspaces.__new__(mdeasm.Workspaces)
    ws._http_timeout = (1, 1)
    ws._dp_token = "dp0"
    ws._cp_token = "cp0"
    ws._default_workspace_name = ""
    ws._workspaces = {}
    return ws


def test_token_expiry_soon_and_not_soon():
    ws = _new_ws()
    token = jwt.encode({"exp": 100}, "x" * 32, algorithm="HS256")
    with mock.patch.object(time, "time", return_value=50):
        assert ws.__token_expiry__(token) is False
    with mock.patch.object(time, "time", return_value=80):
        assert ws.__token_expiry__(token) is True


def test_validate_asset_id_formats():
    ws = _new_ws()

    raw_id = "domain$$example.com"
    asset_id, verified = ws.__validate_asset_id__(raw_id)
    assert asset_id == raw_id
    assert verified == base64.b64encode(raw_id.encode()).decode()

    uuid_id = "123e4567-e89b-12d3-a456-426614174000"
    asset_id, verified = ws.__validate_asset_id__(uuid_id)
    assert asset_id == uuid_id
    assert verified == uuid_id

    b64 = base64.b64encode(b"hello").decode()
    asset_id, verified = ws.__validate_asset_id__(b64)
    assert asset_id == b64
    assert verified == b64

    with mock.patch.object(mdeasm.logging, "error"):
        with mock.patch.object(mdeasm.logging, "debug"):
            try:
                ws.__validate_asset_id__("not-a-uuid-or-base64")
                assert False, "expected exception"
            except Exception as e:
                assert "not-a-uuid-or-base64" in str(e)


def test_workspace_query_helper_retries_and_refreshes_token_on_401():
    ws = _new_ws()

    class Resp:
        def __init__(self, ok, status_code, text, headers=None):
            self.ok = ok
            self.status_code = status_code
            self.text = text
            self.headers = headers or {}

    calls = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return Resp(False, 401, "nope", headers={"Retry-After": "1"})
        return Resp(True, 200, "ok")

    with mock.patch.object(mdeasm.requests, "request", side_effect=fake_request):
        with mock.patch.object(ws, "__token_expiry__", return_value=False):
            with mock.patch.object(ws, "__bearer_token__", return_value="dp1"):
                with mock.patch.object(mdeasm.time, "sleep") as sleep_mock:
                    r = ws.__workspace_query_helper__(
                        "t",
                        method="get",
                        endpoint="assets/foo bar",
                        url="https://example.test",
                        data_plane=True,
                        retry=True,
                        max_retry=2,
                    )

    assert r.ok is True
    assert len(calls) == 2

    # First request used original token; second request used refreshed token.
    assert calls[0]["headers"]["Authorization"] == "Bearer dp0"
    assert calls[1]["headers"]["Authorization"] == "Bearer dp1"

    # Retry-After respected.
    sleep_mock.assert_called_once_with(1)

