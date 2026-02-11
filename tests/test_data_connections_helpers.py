import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm  # noqa: E402


class _DummyResp:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code

    def json(self):
        return self._payload


def _ws_stub():
    ws = mdeasm.Workspaces.__new__(mdeasm.Workspaces)
    ws._default_workspace_name = "w"
    ws._workspaces = {"w": ("dp", "cp")}
    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    return ws


def test_list_data_connections_get_all_paginates_and_redacts_api_key():
    ws = _ws_stub()
    captured = []

    responses = [
        _DummyResp(
            {
                "totalElements": 3,
                "value": [
                    {"name": "dc1", "kind": "logAnalytics", "properties": {"apiKey": "secret-1"}},
                    {"name": "dc2", "kind": "logAnalytics", "properties": {"apiKey": "secret-2"}},
                ],
            }
        ),
        _DummyResp(
            {
                "totalElements": 3,
                "value": [
                    {"name": "dc3", "kind": "azureDataExplorer"},
                ],
            }
        ),
    ]

    def qh(calling_func, method, endpoint, **kwargs):
        captured.append((calling_func, method, endpoint, kwargs.get("params")))
        return responses[len(captured) - 1]

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]
    out = ws.list_data_connections(get_all=True, max_page_size=2, noprint=True)

    assert [x["name"] for x in out["value"]] == ["dc1", "dc2", "dc3"]
    assert out["value"][0]["properties"]["apiKey"] == "[REDACTED]"
    assert captured[0][3]["skip"] == 0
    assert captured[1][3]["skip"] == 2


def test_create_or_replace_data_connection_puts_expected_payload_and_redacts():
    ws = _ws_stub()
    captured = {}

    def qh(calling_func, method, endpoint, **kwargs):
        captured["calling_func"] = calling_func
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["payload"] = kwargs.get("payload")
        return _DummyResp(
            {
                "name": "dc-la",
                "kind": "logAnalytics",
                "properties": {"workspaceId": "abc", "apiKey": "really-secret"},
            }
        )

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]

    out = ws.create_or_replace_data_connection(
        "dc-la",
        kind="logAnalytics",
        properties={"workspaceId": "abc", "apiKey": "really-secret"},
        content="assets",
        frequency="weekly",
        frequency_offset=1,
        workspace_name="w",
        noprint=True,
    )

    assert captured["calling_func"] == "create_or_replace_data_connection"
    assert captured["method"] == "put"
    assert captured["endpoint"] == "dataConnections/dc-la"
    assert captured["payload"]["kind"] == "logAnalytics"
    assert captured["payload"]["properties"]["apiKey"] == "really-secret"
    assert out["properties"]["apiKey"] == "[REDACTED]"


def test_validate_data_connection_uses_validate_endpoint():
    ws = _ws_stub()
    captured = {}

    def qh(calling_func, method, endpoint, **kwargs):
        captured["calling_func"] = calling_func
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["payload"] = kwargs.get("payload")
        return _DummyResp({"ok": True})

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]

    out = ws.validate_data_connection(
        name="dc-adx",
        kind="azureDataExplorer",
        properties={"clusterName": "c1", "databaseName": "d1", "region": "eastus"},
        content="attackSurfaceInsights",
        frequency="daily",
        frequency_offset=0,
        workspace_name="w",
        noprint=True,
    )

    assert out == {"ok": True}
    assert captured["calling_func"] == "validate_data_connection"
    assert captured["method"] == "post"
    assert captured["endpoint"] == "dataConnections:validate"
    assert captured["payload"]["name"] == "dc-adx"
    assert captured["payload"]["kind"] == "azureDataExplorer"
    assert captured["payload"]["content"] == "attackSurfaceInsights"


def test_delete_data_connection_returns_deleted_payload():
    ws = _ws_stub()
    captured = {}

    def qh(calling_func, method, endpoint, **kwargs):
        captured["calling_func"] = calling_func
        captured["method"] = method
        captured["endpoint"] = endpoint
        return _DummyResp({}, status_code=204)

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]
    out = ws.delete_data_connection("dc1", workspace_name="w", noprint=True)

    assert captured["calling_func"] == "delete_data_connection"
    assert captured["method"] == "delete"
    assert captured["endpoint"] == "dataConnections/dc1"
    assert out == {"deleted": "dc1", "status": 204}

