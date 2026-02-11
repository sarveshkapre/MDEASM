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
