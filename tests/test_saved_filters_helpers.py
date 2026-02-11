import sys
from pathlib import Path

import pytest


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
    return ws


def test_get_saved_filters_calls_helper_with_params():
    ws = _ws_stub()
    captured = {}

    def qh(calling_func, method, endpoint, **kwargs):
        captured["calling_func"] = calling_func
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["params"] = kwargs.get("params")
        return _DummyResp({"value": []})

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]

    out = ws.get_saved_filters(
        workspace_name="w", filter_expr="displayName eq 'x'", skip=50, max_page_size=10, noprint=True
    )
    assert out == {"value": []}
    assert captured["calling_func"] == "get_saved_filters"
    assert captured["method"] == "get"
    assert captured["endpoint"] == "savedFilters"
    assert captured["params"] == {"filter": "displayName eq 'x'", "skip": 50, "maxpagesize": 10}


def test_create_or_replace_saved_filter_puts_payload():
    ws = _ws_stub()
    captured = {}

    def qh(calling_func, method, endpoint, **kwargs):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["payload"] = kwargs.get("payload")
        return _DummyResp({"name": "sfA"})

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]

    out = ws.create_or_replace_saved_filter(
        "sfA", query_filter='kind = "domain"', description="d", workspace_name="w", noprint=True
    )
    assert out == {"name": "sfA"}
    assert captured["method"] == "put"
    assert captured["endpoint"] == "savedFilters/sfA"
    assert captured["payload"] == {"filter": 'kind = "domain"', "description": "d"}


def test_delete_saved_filter_uses_delete_method():
    ws = _ws_stub()
    captured = {}

    def qh(calling_func, method, endpoint, **kwargs):
        captured["method"] = method
        captured["endpoint"] = endpoint
        return _DummyResp({}, status_code=204)

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]

    ws.delete_saved_filter("sfA", workspace_name="w", noprint=True)
    assert captured["method"] == "delete"
    assert captured["endpoint"] == "savedFilters/sfA"


def test_saved_filter_methods_encode_name_for_path_segment():
    ws = _ws_stub()
    captured = {"endpoints": []}

    def qh(calling_func, method, endpoint, **kwargs):
        captured["endpoints"].append(endpoint)
        return _DummyResp({"name": "sf with space"})

    ws.__workspace_query_helper__ = qh  # type: ignore[attr-defined]

    ws.get_saved_filter("sf with space", workspace_name="w", noprint=True)
    ws.create_or_replace_saved_filter(
        "sf with space",
        query_filter='kind = "domain"',
        description="desc",
        workspace_name="w",
        noprint=True,
    )
    ws.delete_saved_filter("sf with space", workspace_name="w", noprint=True)

    assert captured["endpoints"] == [
        "savedFilters/sf%20with%20space",
        "savedFilters/sf%20with%20space",
        "savedFilters/sf%20with%20space",
    ]


def test_saved_filter_methods_raise_typed_workspace_and_validation_errors():
    ws = _ws_stub()
    ws.__verify_workspace__ = lambda _workspace_name: False  # type: ignore[attr-defined]
    with pytest.raises(mdeasm.WorkspaceNotFoundError):
        ws.get_saved_filters(workspace_name="missing", noprint=True)

    ws.__verify_workspace__ = lambda _workspace_name: True  # type: ignore[attr-defined]
    with pytest.raises(mdeasm.ValidationError):
        ws.get_saved_filter("", workspace_name="w", noprint=True)
    with pytest.raises(mdeasm.ValidationError):
        ws.create_or_replace_saved_filter(
            "sfA",
            query_filter="",
            description="desc",
            workspace_name="w",
            noprint=True,
        )
    with pytest.raises(mdeasm.ValidationError):
        ws.create_or_replace_saved_filter(
            "sfA",
            query_filter='kind = "domain"',
            description="",
            workspace_name="w",
            noprint=True,
        )
    with pytest.raises(mdeasm.ValidationError):
        ws.delete_saved_filter("bad/name", workspace_name="w", noprint=True)
