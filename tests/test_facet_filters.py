import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm  # noqa: E402


def _new_ws():
    # Bypass __init__ (requires env + real tokens) and build a minimal object for unit tests.
    ws = mdeasm.Workspaces.__new__(mdeasm.Workspaces)
    return ws


def test_facet_filters_headers_multi_facet_counts_across_assets():
    ws = _new_ws()
    ws.assetList = mdeasm.AssetList()

    a1 = mdeasm.Asset()
    a1.id = "host$$a.example"
    a1.kind = "host"
    a1.headers = [{"headerName": "Server", "headerValue": "nginx"}]

    a2 = mdeasm.Asset()
    a2.id = "host$$b.example"
    a2.kind = "host"
    a2.headers = [{"headerName": "Server", "headerValue": "nginx"}]

    ws.assetList.assets = [a1, a2]
    ws.__facet_filter_helper__(asset_list_name="assetList", attribute_name="headers")

    entry = ws.filters.headers[("Server", "nginx")]
    assert entry["count"] == 2
    assert set(entry["assets"]) == {a1.id, a2.id}


def test_facet_filters_special_cases_services_location_webcomponents_sslserverconfig_and_cves():
    ws = _new_ws()
    ws.assetList = mdeasm.AssetList()

    a = mdeasm.Asset()
    a.id = "host$$x.example"
    a.kind = "host"
    a.services = [{"port": 80, "scheme": "http", "portStates": [{"value": "open"}, {"value": "filtered"}]}]
    a.location = [
        {
            "value": {
                "countrycode": "US",
                "countryname": "United States",
                "latitude": 10.0,
                "longitude": 20.0,
            }
        }
    ]
    a.webComponents = [
        {"name": "Apache", "type": "server", "version": "2.4", "cve": [{"name": "CVE-2020-1", "cvssScore": 9.8}]}
    ]
    a.sslServerConfig = [{"cipherSuites": ["TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384"], "tlsVersions": ["1.2", "1.3"]}]

    ws.assetList.assets = [a]
    ws.__facet_filter_helper__(asset_list_name="assetList")

    assert ws.filters.services[(80, "http", "open")]["count"] == 1
    assert ws.filters.services[(80, "http", "filtered")]["count"] == 1

    assert ws.filters.location[("US", "United States", 10.0, 20.0)]["count"] == 1

    assert ws.filters.webComponents[("Apache", "server", "2.4")]["count"] == 1
    assert ws.filters.cveId[("Apache", "CVE-2020-1", 9.8)]["count"] == 1

    assert ws.filters.sslServerConfig[("TLS_AES_128_GCM_SHA256", "1.2")]["count"] == 1
    assert ws.filters.sslServerConfig[("TLS_AES_256_GCM_SHA384", "1.3")]["count"] == 1

