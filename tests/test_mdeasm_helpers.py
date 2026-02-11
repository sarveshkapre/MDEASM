import base64
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import jwt
import pytest


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


def test_redact_sensitive_text_masks_bearer_tokens_fields_and_query_params():
    raw = (
        "Authorization: Bearer abc.def.ghi "
        "client_secret=supersecret "
        '{"access_token":"tok123","refresh_token":"ref456"} '
        "https://example.test/download?sig=verysecret&sv=2023-01-01"
    )
    cooked = mdeasm.redact_sensitive_text(raw)
    assert "abc.def.ghi" not in cooked
    assert "supersecret" not in cooked
    assert "tok123" not in cooked
    assert "ref456" not in cooked
    assert "verysecret" not in cooked
    assert "[REDACTED]" in cooked


def test_parse_retry_after_seconds_supports_delay_and_http_date():
    now = datetime(2026, 2, 11, 0, 0, 0, tzinfo=timezone.utc)

    assert mdeasm._parse_retry_after_seconds("7", now=now) == 7
    assert mdeasm._parse_retry_after_seconds("Wed, 11 Feb 2026 00:00:03 GMT", now=now) == 3


def test_parse_retry_after_seconds_handles_invalid_and_past_values():
    now = datetime(2026, 2, 11, 0, 0, 0, tzinfo=timezone.utc)

    assert mdeasm._parse_retry_after_seconds("", now=now) is None
    assert mdeasm._parse_retry_after_seconds("not-a-date", now=now) is None
    assert mdeasm._parse_retry_after_seconds("Tue, 10 Feb 2026 23:59:59 GMT", now=now) == 0


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


def test_workspace_query_helper_redacts_failure_exception_text():
    ws = _new_ws()

    class Resp:
        def __init__(self):
            self.ok = False
            self.status_code = 500
            self.text = (
                "request failed: bearer bad.token.value "
                'access_token":"token-secret" '
                "client_secret=hunter2 "
                "https://blob.example.test/file.csv?sig=mysecret"
            )
            self.headers = {}

    def fake_request(**kwargs):
        return Resp()

    with mock.patch.object(mdeasm.requests, "request", side_effect=fake_request):
        with mock.patch.object(ws, "__token_expiry__", return_value=False):
            try:
                ws.__workspace_query_helper__(
                    "t",
                    method="get",
                    endpoint="assets",
                    url="https://example.test",
                    data_plane=True,
                    retry=False,
                    max_retry=1,
                )
                assert False, "expected exception"
            except Exception as e:
                msg = str(e)
                assert "token-secret" not in msg
                assert "hunter2" not in msg
                assert "mysecret" not in msg
                assert "[REDACTED]" in msg


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
        with mock.patch.object(
            mdeasm.requests,
            "request",
            side_effect=AssertionError("requests.request should not be used"),
        ):
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


def test_stream_workspace_assets_status_to_stderr_and_max_assets_cap(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    # Two pages of 3 assets each, but we cap to 4 total.
    responses = [
        Resp(
            {
                "totalElements": 6,
                "content": [
                    {"id": "a1", "kind": "domain"},
                    {"id": "a2", "kind": "domain"},
                    {"id": "a3", "kind": "domain"},
                ],
                "last": False,
                "number": 0,
            }
        ),
        Resp(
            {
                "totalElements": 6,
                "content": [
                    {"id": "b1", "kind": "domain"},
                    {"id": "b2", "kind": "domain"},
                    {"id": "b3", "kind": "domain"},
                ],
                "last": True,
                "number": 1,
            }
        ),
    ]
    calls = {"n": 0}

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **_kwargs):
        idx = calls["n"]
        calls["n"] += 1
        return responses[idx]

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    rows = list(
        ws.stream_workspace_assets(
            query_filter='kind = "domain"',
            get_all=True,
            max_page_size=3,
            max_assets=4,
            status_to_stderr=True,
            no_track_time=True,
        )
    )

    out = capsys.readouterr()
    assert out.out == ""
    assert "assets identified by query" in out.err
    assert "query complete" in out.err
    assert len(rows) == 4
    assert rows[0]["id"] == "a1"


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


def test_list_tasks_get_all_paginates_by_skip():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    calls = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    responses = [
        Resp(
            {
                "totalElements": 3,
                "value": [{"id": "t1"}, {"id": "t2"}],
            }
        ),
        Resp(
            {
                "totalElements": 3,
                "value": [{"id": "t3"}],
            }
        ),
    ]

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **kwargs):
        calls.append(kwargs)
        return responses[len(calls) - 1]

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.list_tasks(get_all=True, max_page_size=2, noprint=True)

    assert [t["id"] for t in payload["value"]] == ["t1", "t2", "t3"]
    assert calls[0]["params"]["skip"] == 0
    assert calls[1]["params"]["skip"] == 2


def test_create_assets_export_task_builds_expected_request():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    captured = {}

    class Resp:
        def json(self):
            return {"id": "task-123", "state": "notStarted"}

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **kwargs):
        captured.update(kwargs)
        return Resp()

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.create_assets_export_task(
        columns=["id", "kind"],
        query_filter='kind = "domain"',
        file_name="assets.csv",
        orderby="name asc",
        noprint=True,
    )

    assert payload["id"] == "task-123"
    assert captured["method"] == "post"
    assert captured["endpoint"] == "assets:export"
    assert captured["params"]["filter"] == 'kind = "domain"'
    assert captured["params"]["orderby"] == "name asc"
    assert captured["payload"] == {"columns": ["id", "kind"], "fileName": "assets.csv"}


def test_task_endpoints_use_expected_routes():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    seen = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **kwargs):
        seen.append((kwargs["method"], kwargs["endpoint"]))
        return Resp({"id": "task-123"})

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    assert ws.get_task("task-123", noprint=True)["id"] == "task-123"
    assert ws.cancel_task("task-123", noprint=True)["id"] == "task-123"
    assert ws.run_task("task-123", noprint=True)["id"] == "task-123"
    assert ws.download_task("task-123", noprint=True)["id"] == "task-123"

    assert seen == [
        ("get", "tasks/task-123"),
        ("post", "tasks/task-123:cancel"),
        ("post", "tasks/task-123:run"),
        ("post", "tasks/task-123:download"),
    ]


def test_task_helpers_raise_workspace_not_found():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws.__verify_workspace__ = lambda _workspace_name: False  # type: ignore[attr-defined]

    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.list_tasks(workspace_name="missing", noprint=True)
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.get_task("task-123", workspace_name="missing", noprint=True)
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.cancel_task("task-123", workspace_name="missing", noprint=True)
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.run_task("task-123", workspace_name="missing", noprint=True)
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.download_task("task-123", workspace_name="missing", noprint=True)


def test_create_assets_export_task_raises_typed_validation_errors():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    with pytest.raises(mdeasm.ValidationError):
        ws.create_assets_export_task(columns="id", noprint=True)
    with pytest.raises(mdeasm.ValidationError):
        ws.create_assets_export_task(columns=[], noprint=True)


def test_get_workspace_assets_supports_value_payload_orderby_mark_and_progress():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    calls = []
    progress = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **kwargs):
        calls.append(kwargs)
        return Resp(
            {
                "totalElements": 1,
                "value": [{"id": "domain$$example.com", "kind": "domain"}],
                "last": True,
                "number": 0,
            }
        )

    def fake_parse_asset(self, asset, **_kwargs):
        parsed = mdeasm.Asset()
        parsed.id = asset.get("id")
        parsed.kind = asset.get("kind")
        return parsed

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    with mock.patch.object(mdeasm.Asset, "__parse_workspace_assets__", fake_parse_asset):
        ws.get_workspace_assets(
            query_filter='kind = "domain"',
            asset_list_name="assetList",
            get_all=True,
            auto_create_facet_filters=False,
            no_track_time=True,
            status_to_stderr=True,
            orderby="id asc",
            mark="*",
            progress_callback=lambda state: progress.append(state),
        )

    assert len(ws.assetList.assets) == 1
    assert calls[0]["params"]["orderby"] == "id asc"
    assert calls[0]["params"]["mark"] == "*"
    assert "skip" not in calls[0]["params"]
    assert progress[-1]["last"] is True
    assert progress[-1]["assets_emitted"] == 1


def test_create_workspace_uses_default_region_when_argument_missing():
    ws = _new_ws()
    ws._subscription_id = "sub0"
    ws._resource_group = "rg0"
    ws._region = "eastus"
    ws._default_workspace_name = "ws0"
    ws._workspaces = mdeasm.requests.structures.CaseInsensitiveDict()
    captured = {}

    class Resp:
        def json(self):
            return {
                "name": "ws0",
                "properties": {"dataPlaneEndpoint": "https://dp.example/"},
                "id": "/subscriptions/sub0/resourceGroups/rg0/providers/Microsoft.Easm/workspaces/ws0",
            }

    def fake_verify_workspace(_workspace_name):
        return False

    def fake_query_helper(*_args, **kwargs):
        captured.update(kwargs)
        return Resp()

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    out = ws.create_workspace(resource_group_name="rg0", region=None, workspace_name="ws0")
    assert "ws0" in out
    assert captured["payload"]["location"] == "eastus"


def test_create_workspace_raises_typed_validation_errors():
    ws = _new_ws()
    ws._subscription_id = "sub0"
    ws._resource_group = ""
    ws._region = ""
    ws._easm_regions = ["eastus", "westus2"]
    ws._default_workspace_name = ""

    with pytest.raises(mdeasm.ValidationError):
        ws.create_workspace(resource_group_name=None, region=None, workspace_name="ws0")

    ws._resource_group = "rg0"
    ws._region = "northpole"
    with pytest.raises(mdeasm.ValidationError):
        ws.create_workspace(resource_group_name=None, region=None, workspace_name="ws0")

    ws._region = "eastus"
    with pytest.raises(mdeasm.ValidationError):
        ws.create_workspace(resource_group_name=None, region=None, workspace_name="")


def test_delete_workspace_uses_workspace_resource_group_metadata_and_clears_default():
    ws = _new_ws()
    ws._subscription_id = "sub0"
    ws._default_workspace_name = "ws0"
    ws._workspaces = mdeasm.requests.structures.CaseInsensitiveDict(
        {
            "ws0": (
                "https://dp.example/subscriptions/sub0/resourceGroups/rg0/workspaces/ws0",
                "management.azure.com/subscriptions/sub0/resourceGroups/rg0/providers/Microsoft.Easm/workspaces/ws0",
            )
        }
    )
    captured = {}

    class Resp:
        status_code = 204

        def json(self):
            return {}

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **kwargs):
        captured.update(kwargs)
        return Resp()

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.delete_workspace(workspace_name="ws0", noprint=True)
    assert payload["deleted"] == "ws0"
    assert payload["resourceGroup"] == "rg0"
    assert payload["statusCode"] == 204
    assert captured["method"] == "delete"
    assert captured["endpoint"] == "workspaces/ws0"
    assert "/resourceGroups/rg0/providers/Microsoft.Easm" in captured["url"]
    assert ws._default_workspace_name == ""


def test_delete_workspace_requires_workspace_name():
    ws = _new_ws()
    ws._default_workspace_name = ""
    with pytest.raises(mdeasm.ValidationError):
        ws.delete_workspace(workspace_name="", noprint=True)


def test_list_resource_tags_returns_workspace_tags_and_uses_arm_api_version():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    captured = {}

    class Resp:
        def json(self):
            return {"properties": {"tags": {"Owner": "SecOps"}}}

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    def fake_query_helper(*_args, **kwargs):
        captured.update(kwargs)
        return Resp()

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.list_resource_tags(workspace_name="ws1", noprint=True)
    assert payload == {"workspaceName": "ws1", "tags": {"Owner": "SecOps"}}
    assert captured["data_plane"] is False
    assert captured["endpoint"] == "providers/Microsoft.Resources/tags/default"
    assert captured["api_version"] == "2021-04-01"


def test_get_resource_tag_requires_name():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    with pytest.raises(mdeasm.ValidationError):
        ws.get_resource_tag("", workspace_name="ws1", noprint=True)


def test_put_resource_tag_merges_existing_tags():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    calls = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    def fake_query_helper(*_args, **kwargs):
        calls.append(dict(kwargs))
        if kwargs["method"] == "get":
            return Resp({"properties": {"tags": {"Owner": "SecOps"}}})
        return Resp({"properties": {"tags": kwargs["payload"]["properties"]["tags"]}})

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.put_resource_tag("Environment", "Prod", workspace_name="ws1", noprint=True)
    assert payload["workspaceName"] == "ws1"
    assert payload["name"] == "Environment"
    assert payload["value"] == "Prod"
    assert payload["tags"] == {"Owner": "SecOps", "Environment": "Prod"}
    assert calls[1]["method"] == "put"
    assert calls[1]["payload"]["properties"]["tags"]["Owner"] == "SecOps"
    assert calls[1]["payload"]["properties"]["tags"]["Environment"] == "Prod"


def test_delete_resource_tag_removes_existing_key():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    calls = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    def fake_query_helper(*_args, **kwargs):
        calls.append(dict(kwargs))
        if kwargs["method"] == "get":
            return Resp({"properties": {"tags": {"Owner": "SecOps", "Environment": "Prod"}}})
        return Resp({"properties": {"tags": kwargs["payload"]["properties"]["tags"]}})

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.delete_resource_tag("Owner", workspace_name="ws1", noprint=True)
    assert payload["workspaceName"] == "ws1"
    assert payload["name"] == "Owner"
    assert payload["deleted"] is True
    assert payload["tags"] == {"Environment": "Prod"}
    assert calls[1]["method"] == "put"
    assert "Owner" not in calls[1]["payload"]["properties"]["tags"]


def test_stream_workspace_assets_supports_value_payload_orderby_mark():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    calls = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_verify_workspace(_workspace_name):
        return True

    def fake_query_helper(*_args, **kwargs):
        calls.append(kwargs)
        return Resp(
            {
                "totalElements": 1,
                "value": [{"id": "domain$$example.com", "kind": "domain"}],
                "last": True,
                "number": 0,
            }
        )

    def fake_parse_asset(self, asset, **_kwargs):
        parsed = mdeasm.Asset()
        parsed.id = asset.get("id")
        parsed.kind = asset.get("kind")
        return parsed

    ws.__verify_workspace__ = fake_verify_workspace  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    with mock.patch.object(mdeasm.Asset, "__parse_workspace_assets__", fake_parse_asset):
        rows = list(
            ws.stream_workspace_assets(
                query_filter='kind = "domain"',
                get_all=True,
                no_track_time=True,
                status_to_stderr=True,
                orderby="id asc",
                mark="*",
            )
        )

    assert rows[0]["id"] == "domain$$example.com"
    assert calls[0]["params"]["orderby"] == "id asc"
    assert calls[0]["params"]["mark"] == "*"
    assert "skip" not in calls[0]["params"]


def test_create_facet_filter_accepts_asset_id_only():
    ws = _new_ws()
    asset_id = "domain$$example.com"
    setattr(ws, asset_id, mdeasm.Asset())
    captured = {}

    def fake_facet_helper(*_args, **kwargs):
        captured.update(kwargs)
        return None

    ws.__facet_filter_helper__ = fake_facet_helper  # type: ignore[attr-defined]

    ws.create_facet_filter(asset_id=asset_id)
    assert captured["asset_id"] == asset_id


def test_get_discovery_templates_supports_noprint_and_returns_rows(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"

    class Resp:
        def json(self):
            return {
                "content": [
                    {"name": "Contoso.", "id": "tmpl-1"},
                    {"name": "Fabrikam", "id": "tmpl-2"},
                ]
            }

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = lambda *_args, **_kwargs: Resp()  # type: ignore[attr-defined]

    rows = ws.get_discovery_templates("contoso", noprint=True)
    assert rows == ["Contoso---tmpl-1", "Fabrikam---tmpl-2"]
    assert capsys.readouterr().out == ""


def test_discovery_helpers_raise_typed_validation_and_workspace_errors():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    with pytest.raises(mdeasm.ValidationError):
        ws.create_discovery_group(disco_template="", disco_custom={}, workspace_name="ws1")
    with pytest.raises(mdeasm.ValidationError):
        ws.create_discovery_group(
            disco_template="Template---123",
            disco_custom={"name": "x", "seeds": {"domain": ["example.com"]}},
            workspace_name="ws1",
        )
    with pytest.raises(mdeasm.ValidationError):
        ws.create_discovery_group(disco_custom={"name": "x"}, workspace_name="ws1")

    ws.__verify_workspace__ = lambda _workspace_name: False  # type: ignore[attr-defined]
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.create_discovery_group(
            disco_template="Template---123",
            disco_custom={},
            workspace_name="missing",
        )


def test_create_discovery_group_template_requires_name_and_id_separator():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    with pytest.raises(mdeasm.ValidationError):
        ws.create_discovery_group(
            disco_template="TemplateOnly",
            disco_custom={},
            workspace_name="ws1",
        )

    with pytest.raises(mdeasm.ValidationError):
        ws.create_discovery_group(
            disco_template="---tmpl-123",
            disco_custom={},
            workspace_name="ws1",
        )


def test_create_discovery_group_template_calls_put_then_run_helper():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    captured = {}

    class Resp:
        status_code = 204

    def fake_query_helper(*_args, **kwargs):
        captured["put_kwargs"] = dict(kwargs)
        return Resp()

    def fake_run_discovery_group(name, **kwargs):
        captured["run_kwargs"] = {"name": name, **kwargs}
        return {name: [{"state": "complete"}]}

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]
    ws.run_discovery_group = fake_run_discovery_group  # type: ignore[attr-defined]

    payload = ws.create_discovery_group(
        disco_template="Contoso---tmpl-123",
        disco_custom={},
        workspace_name="ws1",
        disco_runs_max_retry=4,
        disco_runs_backoff_max_s=9,
        noprint=True,
    )

    assert captured["put_kwargs"]["method"] == "put"
    assert captured["put_kwargs"]["endpoint"] == "discoGroups/Contoso"
    assert captured["put_kwargs"]["payload"] == {"templateId": "tmpl-123"}
    assert captured["run_kwargs"] == {
        "name": "Contoso",
        "workspace_name": "ws1",
        "disco_runs_max_retry": 4,
        "disco_runs_backoff_max_s": 9,
        "noprint": True,
    }
    assert payload == {"Contoso": [{"state": "complete"}]}


def test_run_discovery_group_calls_run_endpoint_and_returns_runs(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    captured = {}

    class Resp:
        status_code = 204

    def fake_query_helper(*_args, **kwargs):
        captured["query_kwargs"] = dict(kwargs)
        return Resp()

    def fake_get_runs_with_retry(disco_name, workspace_name="", max_attempts=3, backoff_max_s=5):
        captured["runs_kwargs"] = {
            "disco_name": disco_name,
            "workspace_name": workspace_name,
            "max_attempts": max_attempts,
            "backoff_max_s": backoff_max_s,
        }
        return {disco_name: [{"state": "complete", "totalAssetsFoundCount": 10}]}

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]
    ws.__get_discovery_group_runs_with_retry__ = fake_get_runs_with_retry  # type: ignore[attr-defined]

    payload = ws.run_discovery_group(
        "Contoso Group",
        workspace_name="ws1",
        disco_runs_max_retry=4,
        disco_runs_backoff_max_s=7,
        noprint=True,
    )
    assert payload == {"Contoso Group": [{"state": "complete", "totalAssetsFoundCount": 10}]}
    assert captured["query_kwargs"]["method"] == "post"
    assert captured["query_kwargs"]["endpoint"] == "discoGroups/Contoso Group:run"
    assert captured["query_kwargs"]["payload"] == {}
    assert captured["runs_kwargs"] == {
        "disco_name": "Contoso Group",
        "workspace_name": "ws1",
        "max_attempts": 4,
        "backoff_max_s": 7,
    }
    assert capsys.readouterr().out == ""


def test_get_discovery_groups_supports_filter_and_paging_params():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    captured = {}

    class Resp:
        def json(self):
            return {"content": []}

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    def fake_query_helper(*_args, **kwargs):
        captured["kwargs"] = dict(kwargs)
        return Resp()

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.get_discovery_groups(
        workspace_name="ws1",
        filter_expr='name eq "Contoso"',
        skip=5,
        max_page_size=10,
        noprint=True,
    )
    assert payload == {"content": []}
    assert captured["kwargs"]["params"] == {
        "filter": 'name eq "Contoso"',
        "skip": 5,
        "maxpagesize": 10,
    }


def test_discovery_group_runs_retry_retries_transient_statuses():
    ws = _new_ws()
    calls = {"count": 0}

    def fake_get_runs(disco_name="", workspace_name=""):
        calls["count"] += 1
        if calls["count"] < 3:
            raise mdeasm.ApiRequestError(
                "called by: __get_discovery_group_runs__ -- last_status: 404 -- last_text: not yet"
            )
        return {disco_name: [{"state": "complete"}]}

    ws.__get_discovery_group_runs__ = fake_get_runs  # type: ignore[attr-defined]

    with mock.patch.object(mdeasm.time, "sleep") as sleep_mock:
        payload = ws.__get_discovery_group_runs_with_retry__(
            "contoso",
            workspace_name="ws1",
            max_attempts=3,
            backoff_max_s=5,
        )

    assert payload == {"contoso": [{"state": "complete"}]}
    assert calls["count"] == 3
    assert sleep_mock.call_args_list == [mock.call(1), mock.call(2)]


def test_discovery_group_runs_retry_stops_on_non_retryable_status():
    ws = _new_ws()
    calls = {"count": 0}

    def fake_get_runs(*_args, **_kwargs):
        calls["count"] += 1
        raise mdeasm.ApiRequestError(
            "called by: __get_discovery_group_runs__ -- last_status: 400 -- last_text: bad request"
        )

    ws.__get_discovery_group_runs__ = fake_get_runs  # type: ignore[attr-defined]

    with mock.patch.object(mdeasm.time, "sleep") as sleep_mock:
        with pytest.raises(mdeasm.ApiRequestError):
            ws.__get_discovery_group_runs_with_retry__(
                "contoso",
                workspace_name="ws1",
                max_attempts=3,
                backoff_max_s=5,
            )

    assert calls["count"] == 1
    sleep_mock.assert_not_called()


def test_delete_discovery_group_supports_optional_verification(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    captured = {"delete_calls": 0, "list_calls": 0}

    class Resp:
        status_code = 204

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]

    def fake_query_helper(*_args, **kwargs):
        assert kwargs["method"] == "delete"
        assert kwargs["endpoint"] == "discoGroups/Contoso Group"
        captured["delete_calls"] += 1
        return Resp()

    def fake_get_discovery_groups(*_args, **_kwargs):
        captured["list_calls"] += 1
        if captured["list_calls"] == 1:
            return {"content": [{"name": "Contoso Group"}]}
        return {"content": []}

    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]
    ws.get_discovery_groups = fake_get_discovery_groups  # type: ignore[attr-defined]

    with mock.patch.object(mdeasm.time, "sleep") as sleep_mock:
        payload = ws.delete_discovery_group(
            "Contoso Group",
            workspace_name="ws1",
            verify_deleted=True,
            verify_max_retry=3,
            verify_backoff_max_s=5,
            noprint=True,
        )

    assert payload == {
        "workspaceName": "ws1",
        "name": "Contoso Group",
        "deleted": True,
        "status": 204,
        "verifiedDeleted": True,
    }
    assert captured["delete_calls"] == 1
    assert captured["list_calls"] == 2
    sleep_mock.assert_called_once_with(1)
    assert capsys.readouterr().out == ""


def test_label_helpers_support_noprint_and_consistent_returns(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    calls = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_query_helper(*_args, **kwargs):
        calls.append((kwargs["method"], kwargs["endpoint"], kwargs.get("payload")))
        if kwargs["endpoint"] == "/labels/owned":
            return Resp({"properties": {"color": "green", "displayName": "Owned"}})
        if kwargs["endpoint"] == "/labels":
            return Resp(
                {
                    "value": [
                        {
                            "name": "owned",
                            "properties": {"color": "green", "displayName": "Owned"},
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected endpoint: {kwargs['endpoint']}")

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    created = ws.create_or_update_label(
        "owned", color="green", display_name="Owned", workspace_name="ws1", noprint=True
    )
    labels = ws.get_labels(workspace_name="ws1", noprint=True)

    assert created == {"color": "green", "displayName": "Owned"}
    assert labels == {"owned": {"color": "green", "displayName": "Owned"}}
    assert calls == [
        (
            "put",
            "/labels/owned",
            {"properties": {"color": "green", "displayName": "Owned"}},
        ),
        ("get", "/labels", None),
    ]
    assert capsys.readouterr().out == ""


def test_label_helpers_print_mode_still_returns_payload(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_query_helper(*_args, **kwargs):
        if kwargs["endpoint"] == "/labels/owned":
            return Resp({"properties": {"color": "blue", "displayName": "Owned"}})
        if kwargs["endpoint"] == "/labels":
            return Resp({"value": []})
        raise AssertionError(f"unexpected endpoint: {kwargs['endpoint']}")

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    created = ws.create_or_update_label("owned", workspace_name="ws1")
    labels = ws.get_labels(workspace_name="ws1")

    out = capsys.readouterr().out
    assert created == {"color": "blue", "displayName": "Owned"}
    assert labels == {}
    assert "created new label 'owned' in ws1" in out
    assert "no labels exist for ws1" in out


def test_label_helpers_raise_workspace_not_found():
    ws = _new_ws()
    ws.__verify_workspace__ = lambda _workspace_name: False  # type: ignore[attr-defined]

    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.create_or_update_label("owned", workspace_name="missing", noprint=True)
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.get_labels(workspace_name="missing", noprint=True)


def test_get_workspace_risk_observations_handles_empty_findings_with_noprint(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    calls = []

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_query_helper(*_args, **kwargs):
        calls.append(kwargs["endpoint"])
        if kwargs["endpoint"] == "reports/assets:summarize":
            return Resp({"assetSummaries": [{"displayName": "High", "count": 0, "children": []}]})
        raise AssertionError(f"unexpected endpoint: {kwargs['endpoint']}")

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    payload = ws.get_workspace_risk_observations("high", noprint=True)
    assert payload["metrics"] == {}
    assert payload["snapshot_assets"] == {}
    assert calls == ["reports/assets:summarize"]
    assert capsys.readouterr().out == ""


def test_workspace_data_helpers_raise_workspace_not_found():
    ws = _new_ws()
    ws.__verify_workspace__ = lambda _workspace_name: False  # type: ignore[attr-defined]

    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.get_workspace_assets(
            query_filter='kind = "domain"',
            asset_list_name="assetList",
            workspace_name="missing",
            auto_create_facet_filters=False,
        )
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.get_workspace_asset_by_id("domain$$example.com", workspace_name="missing")
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.get_workspace_risk_observations(workspace_name="missing", noprint=True)


def test_update_assets_and_poll_task_support_noprint(capsys):
    ws = _new_ws()
    ws._default_workspace_name = "ws1"

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    task_payload = {
        "totalElements": 1,
        "content": [
            {
                "id": "task-123",
                "state": "running",
                "startedAt": "2026-01-01T00:00:00Z",
                "metadata": {
                    "filter": 'kind = "domain"',
                    "assetUpdateRequest": {"state": "confirmed"},
                    "estimated": 1,
                    "progress": 50,
                },
            }
        ],
    }

    def fake_query_helper(*_args, **kwargs):
        if kwargs["endpoint"] == "reports/assets:summarize":
            return Resp({"assetSummaries": [{"count": 1}]})
        if kwargs["endpoint"] == "assets":
            return Resp({"id": "task-123"})
        if kwargs["endpoint"] == "tasks":
            return Resp(task_payload)
        raise AssertionError(f"unexpected endpoint: {kwargs['endpoint']}")

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    task_id = ws.update_assets(
        query_filter='kind = "domain"',
        new_state="Approved",
        noprint=True,
    )
    assert task_id == "task-123"
    assert ws.task_ids == ["task-123"]

    polled = ws.poll_asset_state_change(task_id="task-123", noprint=True)
    assert [task["id"] for task in polled] == ["task-123"]
    assert capsys.readouterr().out == ""


def test_asset_lists_and_facet_filters_support_noprint(capsys):
    ws = _new_ws()
    ws.some_assets = mdeasm.AssetList()
    ws.filters = mdeasm.FacetFilter()
    ws.filters.headers = {}

    assert ws.asset_lists(noprint=True) == ["some_assets"]
    assert ws.facet_filters(noprint=True) == ["headers"]
    assert capsys.readouterr().out == ""


def test_update_assets_asset_count_guardrail_raises_validation_error():
    ws = _new_ws()
    ws._default_workspace_name = "ws1"
    ws._state_map = {"Approved": "confirmed"}

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_query_helper(*_args, **kwargs):
        if kwargs["endpoint"] == "reports/assets:summarize":
            return Resp({"assetSummaries": [{"count": 100000}]})
        raise AssertionError(f"unexpected endpoint: {kwargs['endpoint']}")

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    ws.__workspace_query_helper__ = fake_query_helper  # type: ignore[attr-defined]

    with pytest.raises(mdeasm.ValidationError):
        ws.update_assets(query_filter='kind = "domain"', new_state="Approved", noprint=True)


def test_query_facet_filter_supports_noprint_and_structured_return(capsys):
    ws = _new_ws()
    ws.filters = mdeasm.FacetFilter()
    ws.filters.headers = {
        ("Server", "nginx"): {"count": 2, "assets": ["host$$a.example", "host$$b.example"]},
        ("Server", "apache"): {"count": 1, "assets": ["host$$c.example"]},
    }

    out = ws.query_facet_filter("nginx", facet_filter="headers", noprint=True)
    assert "headers" in out
    assert out["headers"][("Server", "nginx")]["count"] == 2
    assert ("Server", "apache") not in out["headers"]
    assert capsys.readouterr().out == ""


def test_query_facet_filter_csv_json_outputs_and_return_payload(tmp_path, capsys):
    ws = _new_ws()
    ws.filters = mdeasm.FacetFilter()
    ws.filters.headers = {
        ("Server", "nginx"): {"count": 2, "assets": ["host$$a.example", "host$$b.example"]},
    }

    out_csv = ws.query_facet_filter(
        "nginx",
        facet_filter="headers",
        out_format="csv",
        out_path=str(tmp_path),
        noprint=True,
    )
    csv_path = tmp_path / "headers_Server_nginx.csv"
    assert csv_path.exists()
    assert csv_path.read_text() == "host$$a.example,host$$b.example"
    assert out_csv["headers"][("Server", "nginx")]["count"] == 2

    out_json = ws.query_facet_filter(
        "nginx",
        facet_filter="headers",
        out_format="json",
        out_path=str(tmp_path),
        noprint=True,
    )
    json_path = tmp_path / "headers_Server_nginx.json"
    assert json_path.exists()
    assert json.loads(json_path.read_text()) == {
        "count": 2,
        "assets": ["host$$a.example", "host$$b.example"],
    }
    assert out_json["headers"][("Server", "nginx")]["count"] == 2
    assert capsys.readouterr().out == ""


def test_query_facet_filter_requires_precomputed_filters():
    ws = _new_ws()
    with pytest.raises(mdeasm.ValidationError):
        ws.query_facet_filter("nginx")


def test_create_facet_filter_and_asset_summary_raise_typed_validation_errors():
    ws = _new_ws()

    with pytest.raises(mdeasm.ValidationError):
        ws.create_facet_filter()

    ws._metric_categories = ["mc1"]
    ws._metrics = ["m1"]
    with pytest.raises(mdeasm.ValidationError):
        ws.get_workspace_asset_summaries(query_filters=[], metric_categories=[], metrics=[])


def test_asset_parser_raises_validation_error_for_inverted_date_range():
    asset = mdeasm.Asset()
    with pytest.raises(mdeasm.ValidationError):
        asset.__parse_workspace_assets__(
            {"id": "domain$$example.com", "kind": "domain"},
            date_range_start="2026-02-12",
            date_range_end="2026-02-11",
        )
