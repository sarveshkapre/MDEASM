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


def test_asset_to_dict_returns_dict_and_can_suppress_print(capsys):
    a = mdeasm.Asset()
    a.id = "domain$$example.com"
    a.kind = "domain"

    d = a.to_dict(print_=False)
    assert d["id"] == "domain$$example.com"
    assert d["kind"] == "domain"
    assert capsys.readouterr().out == ""

    d2 = a.to_dict()
    out = capsys.readouterr().out
    assert d2 == d
    assert "domain$$example.com" in out


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


def test_workspace_query_helper_prefers_requests_session_when_present():
    ws = _new_ws()

    class Resp:
        def __init__(self, ok, status_code, text, headers=None):
            self.ok = ok
            self.status_code = status_code
            self.text = text
            self.headers = headers or {}

    class DummySession:
        def __init__(self):
            self.calls = []

        def request(self, **kwargs):
            self.calls.append(kwargs)
            return Resp(True, 200, "ok")

    ws._session = DummySession()

    with mock.patch.object(ws, "__token_expiry__", return_value=False):
        with mock.patch.object(mdeasm.requests, "request", side_effect=AssertionError("requests.request should not be used")):
            r = ws.__workspace_query_helper__(
                "t",
                method="get",
                endpoint="assets/foo",
                url="https://example.test",
                data_plane=True,
                retry=False,
                max_retry=1,
            )

    assert r.ok is True
    assert len(ws._session.calls) == 1


def test_workspace_query_helper_uses_plane_specific_api_versions():
    ws = _new_ws()
    ws._dp_api_version = "dp-v1"
    ws._cp_api_version = "cp-v1"

    class Resp:
        def __init__(self, ok, status_code, text, headers=None):
            self.ok = ok
            self.status_code = status_code
            self.text = text
            self.headers = headers or {}

    calls = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return Resp(True, 200, "ok")

    with mock.patch.object(mdeasm.requests, "request", side_effect=fake_request):
        with mock.patch.object(ws, "__token_expiry__", return_value=False):
            ws.__workspace_query_helper__(
                "t",
                method="get",
                endpoint="assets/foo",
                url="https://example.test",
                data_plane=True,
                retry=False,
                max_retry=1,
            )
            ws.__workspace_query_helper__(
                "t",
                method="get",
                endpoint="workspaces",
                url="https://example.test",
                data_plane=False,
                retry=False,
                max_retry=1,
            )

    assert calls[0]["params"]["api-version"] == "dp-v1"
    assert calls[1]["params"]["api-version"] == "cp-v1"


def test_get_workspace_assets_status_to_stderr_and_max_assets_cap(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    # Two pages of 3 assets each, but we cap to 4 total.
    responses = [
        Resp({"totalElements": 6, "content": [{}, {}, {}], "last": False, "number": 0}),
        Resp({"totalElements": 6, "content": [{}, {}, {}], "last": True, "number": 1}),
    ]
    calls = {"n": 0}

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **_kwargs):
        idx = calls["n"]
        calls["n"] += 1
        return responses[idx]

    def fake_asset_content_helper(response_object, asset_list_name="", **_kwargs):
        for _ in response_object.json()["content"]:
            getattr(ws, asset_list_name).assets.append(object())
        return ws

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]
    ws.__asset_content_helper__ = fake_asset_content_helper  # type: ignore[attr-defined]

    ws.get_workspace_assets(
        query_filter='kind = "domain"',
        asset_list_name="assetList",
        get_all=True,
        max_page_size=3,
        auto_create_facet_filters=False,
        max_assets=4,
        status_to_stderr=True,
        no_track_time=True,
    )

    out = capsys.readouterr()
    assert out.out == ""
    assert "assets identified by query" in out.err
    assert "query complete" in out.err
    assert len(ws.assetList.assets) == 4


def test_get_workspaces_missing_default_does_not_write_to_stdout(capsys):
    ws = _new_ws()
    ws._subscription_id = "sub0"
    ws._default_workspace_name = ""
    ws._workspaces = mdeasm.requests.structures.CaseInsensitiveDict()

    class Resp:
        def json(self):
            # Minimal control-plane payload shape.
            return {
                "value": [
                    {
                        "name": "wsA",
                        "properties": {"dataPlaneEndpoint": "https://dp.example/"},
                        "id": "/subscriptions/sub0/resourceGroups/rg/providers/Microsoft.Easm/workspaces/wsA",
                    },
                    {
                        "name": "wsB",
                        "properties": {"dataPlaneEndpoint": "https://dp.example/"},
                        "id": "/subscriptions/sub0/resourceGroups/rg/providers/Microsoft.Easm/workspaces/wsB",
                    },
                ]
            }

    def fake_query_helper(*_args, **_kwargs):
        return Resp()

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    ws.get_workspaces(workspace_name="")

    out = capsys.readouterr()
    assert out.out == ""
    assert "no WORKSPACE_NAME set" in out.err
    assert "\twsA" in out.err
    assert "\twsB" in out.err
