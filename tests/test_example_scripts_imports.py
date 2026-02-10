import importlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))


def test_example_scripts_are_import_safe():
    # These scripts are meant to be runnable examples. Importing them should not immediately
    # create Workspaces(), perform network calls, or call sys.exit().
    modules = [
        "affected_cvss_validation",
        "bulk_asset_state_change",
        "cisa_known_exploited_vulns",
        "expired_certificates_validation",
        "extract_associated_certNames_from_query",
        "hosts_with_CNAME_no_IP_possible_subdomain_takeover",
    ]

    for name in modules:
        mod = importlib.import_module(name)
        assert hasattr(mod, "main")
