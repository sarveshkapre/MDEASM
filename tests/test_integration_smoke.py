import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm  # noqa: E402


def test_integration_smoke_get_workspaces():
    """
    Opt-in integration smoke test.

    This is intentionally skipped by default so CI and casual contributors
    don't need Azure credentials.
    """
    if os.getenv("MDEASM_INTEGRATION") != "1":
        pytest.skip("set MDEASM_INTEGRATION=1 to enable integration smoke tests")

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    # Workspaces.__init__ calls get_workspaces() automatically.
    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)

    # If we got here, auth + control-plane query succeeded.
    assert hasattr(ws, "_workspaces")
    assert ws._workspaces is not None


def test_integration_smoke_data_plane_assets():
    """
    Optional data-plane drift smoke test.

    This is a small "does the data-plane still respond with our current api-version + auth"
    probe without attempting to export large inventories.
    """
    if os.getenv("MDEASM_INTEGRATION_DP") != "1":
        pytest.skip("set MDEASM_INTEGRATION_DP=1 to enable data-plane integration smoke tests")

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)

    # If multiple workspaces exist and WORKSPACE_NAME isn't set, the helper doesn't pick a default.
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip("set WORKSPACE_NAME (or ensure only one workspace exists) to run data-plane smoke")

    ws.get_workspace_assets(
        query_filter='kind = "domain"',
        asset_list_name="smokeAssets",
        get_all=False,
        max_page_size=1,
        max_page_count=1,
        auto_create_facet_filters=False,
        status_to_stderr=True,
        no_track_time=True,
        max_assets=1,
    )

    assert hasattr(ws, "smokeAssets")
