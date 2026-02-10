import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm  # noqa: E402


def test_parse_workspace_assets_date_range_end_only_filters_without_nameerror():
    asset_object = {
        "kind": "host",
        "id": "host$$example.test",
        "asset": {
            "attributes": [
                {"lastSeen": "2025-12-31T00:00:00Z", "recent": False, "value": "a"},
                {"lastSeen": "2026-01-02T00:00:00Z", "recent": False, "value": "b"},
            ]
        },
    }

    asset = mdeasm.Asset().__parse_workspace_assets__(
        asset_object,
        get_recent=False,
        last_seen_days_back=0,
        date_range_end="2026-01-01",
    )

    assert hasattr(asset, "attributes")
    assert [x["value"] for x in asset.attributes] == ["a"]

