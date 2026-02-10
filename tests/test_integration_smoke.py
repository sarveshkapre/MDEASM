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

