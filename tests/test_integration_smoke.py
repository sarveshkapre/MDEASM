import os
import re
import sys
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm  # noqa: E402
import mdeasm_cli  # noqa: E402


def _extract_last_status(exc: Exception) -> int | None:
    status_match = re.search(r"last_status:\s*([0-9]{3})", str(exc), flags=re.IGNORECASE)
    if not status_match:
        return None
    return int(status_match.group(1))


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
        pytest.skip(
            "set WORKSPACE_NAME (or ensure only one workspace exists) to run data-plane smoke"
        )

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


def test_integration_smoke_cli_assets_export():
    """
    Opt-in "real export" integration smoke.

    This exercises the CLI wrapper (filter parsing + stdout/stderr separation + JSON encoding)
    with a tiny export capped at 1 asset.
    """
    if os.getenv("MDEASM_INTEGRATION_EXPORT") != "1":
        pytest.skip("set MDEASM_INTEGRATION_EXPORT=1 to enable CLI export integration smoke tests")

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    # This will call control-plane get_workspaces() on init.
    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip("set WORKSPACE_NAME (or ensure only one workspace exists) to run export smoke")

    # Run the CLI flow (writes JSON to stdout; status to stderr).
    rc = mdeasm_cli.main(
        [
            "assets",
            "export",
            "--filter",
            'kind = "domain"',
            "--format",
            "json",
            "--no-pretty",
            "--out",
            "-",
            "--no-facet-filters",
            "--max-assets",
            "1",
            "--max-page-size",
            "1",
            "--max-page-count",
            "1",
        ]
    )
    assert rc == 0


def test_integration_smoke_data_connections_list():
    """
    Optional data-connections API drift smoke.

    Preview data-connection endpoints can drift by api-version/tenant; this probes a tiny
    list call so maintainers can validate compatibility without changing data connections.
    """
    if os.getenv("MDEASM_INTEGRATION_DATA_CONNECTIONS") != "1":
        pytest.skip(
            "set MDEASM_INTEGRATION_DATA_CONNECTIONS=1 to enable data-connections integration smoke"
        )

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip(
            "set WORKSPACE_NAME (or ensure only one workspace exists) to run data-connections smoke"
        )

    payload = ws.list_data_connections(max_page_size=1, get_all=False, noprint=True)
    assert isinstance(payload, dict)
    assert "value" in payload or "content" in payload


def test_integration_smoke_data_connections_get():
    """
    Optional data-connections get smoke.

    Uses `MDEASM_INTEGRATION_DATA_CONNECTION_NAME` when provided; otherwise it attempts to
    discover one from a tiny list call and skips if none exist.
    """
    if os.getenv("MDEASM_INTEGRATION_DATA_CONNECTIONS") != "1":
        pytest.skip(
            "set MDEASM_INTEGRATION_DATA_CONNECTIONS=1 to enable data-connections integration smoke"
        )

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip(
            "set WORKSPACE_NAME (or ensure only one workspace exists) to run data-connections smoke"
        )

    name = str(os.getenv("MDEASM_INTEGRATION_DATA_CONNECTION_NAME", "")).strip()
    if not name:
        listed = ws.list_data_connections(max_page_size=1, get_all=False, noprint=True)
        rows = listed.get("value") if isinstance(listed, dict) else None
        if rows is None and isinstance(listed, dict):
            rows = listed.get("content")
        rows = rows if isinstance(rows, list) else []
        if not rows:
            pytest.skip(
                "no data connections available to run get smoke; set MDEASM_INTEGRATION_DATA_CONNECTION_NAME"
            )
        name = str((rows[0] or {}).get("name") or "").strip()
        if not name:
            pytest.skip(
                "unable to infer data connection name from list response; set MDEASM_INTEGRATION_DATA_CONNECTION_NAME"
            )

    payload = ws.get_data_connection(name, noprint=True)
    assert isinstance(payload, dict)
    returned_name = str(payload.get("name") or payload.get("id") or "").strip()
    assert returned_name


def test_integration_smoke_data_connections_validate():
    """
    Optional data-connections validate smoke.

    This probes endpoint reachability using non-destructive validation payloads. Validation
    rejections (for example 400/409/422) are treated as success because they still prove the
    endpoint shape is reachable and responsive.
    """
    if os.getenv("MDEASM_INTEGRATION_DATA_CONNECTIONS") != "1":
        pytest.skip(
            "set MDEASM_INTEGRATION_DATA_CONNECTIONS=1 to enable data-connections integration smoke"
        )

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip(
            "set WORKSPACE_NAME (or ensure only one workspace exists) to run data-connections smoke"
        )

    kind = str(os.getenv("MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_KIND", "logAnalytics")).strip()
    if kind == "logAnalytics":
        workspace_id = str(
            os.getenv(
                "MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_WORKSPACE_ID",
                f"/subscriptions/{os.getenv('SUBSCRIPTION_ID', '00000000-0000-0000-0000-000000000000')}/"
                "resourcegroups/placeholder/providers/microsoft.operationalinsights/workspaces/placeholder",
            )
        ).strip()
        api_key = str(
            os.getenv(
                "MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_API_KEY",
                "mdeasm-integration-smoke-placeholder-key",
            )
        ).strip()
        properties = {"workspaceId": workspace_id, "apiKey": api_key}
    elif kind == "azureDataExplorer":
        properties = {
            "clusterName": str(
                os.getenv("MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_CLUSTER_NAME", "placeholder-cluster")
            ).strip(),
            "databaseName": str(
                os.getenv("MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_DATABASE_NAME", "placeholder-db")
            ).strip(),
            "region": str(
                os.getenv("MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_REGION", "eastus")
            ).strip(),
        }
    else:
        pytest.skip(
            "unsupported MDEASM_INTEGRATION_DATA_CONNECTION_VALIDATE_KIND; use logAnalytics or azureDataExplorer"
        )

    try:
        payload = ws.validate_data_connection(kind=kind, properties=properties, noprint=True)
    except Exception as exc:
        status_match = re.search(r"last_status:\s*([0-9]{3})", str(exc), flags=re.IGNORECASE)
        status = int(status_match.group(1)) if status_match else None
        if status in {400, 409, 422}:
            return
        pytest.fail(f"unexpected validate_data_connection failure: {exc}")
    else:
        assert isinstance(payload, dict)


def test_integration_smoke_discovery_groups_list():
    """
    Optional discovery-groups API drift smoke.

    This is a non-destructive, tiny list probe for discovery group endpoint compatibility.
    """
    if os.getenv("MDEASM_INTEGRATION_DISCOVERY_GROUPS") != "1":
        pytest.skip(
            "set MDEASM_INTEGRATION_DISCOVERY_GROUPS=1 to enable discovery-groups integration smoke"
        )

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip(
            "set WORKSPACE_NAME (or ensure only one workspace exists) to run discovery-groups smoke"
        )

    payload = ws.get_discovery_groups(max_page_size=1, noprint=True)
    assert isinstance(payload, dict)
    assert "content" in payload or "value" in payload


def test_integration_smoke_discovery_groups_run():
    """
    Optional discovery-groups run smoke.

    This is opt-in because it triggers an actual discovery-group run. Use
    `MDEASM_INTEGRATION_DISCOVERY_GROUP_NAME` to target a known safe group.
    """
    if os.getenv("MDEASM_INTEGRATION_DISCOVERY_GROUPS") != "1":
        pytest.skip(
            "set MDEASM_INTEGRATION_DISCOVERY_GROUPS=1 to enable discovery-groups integration smoke"
        )

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip(
            "set WORKSPACE_NAME (or ensure only one workspace exists) to run discovery-groups smoke"
        )

    group_name = str(os.getenv("MDEASM_INTEGRATION_DISCOVERY_GROUP_NAME", "")).strip()
    if not group_name:
        listed = ws.get_discovery_groups(max_page_size=1, noprint=True)
        rows = listed.get("value") if isinstance(listed, dict) else None
        if rows is None and isinstance(listed, dict):
            rows = listed.get("content")
        rows = rows if isinstance(rows, list) else []
        if not rows:
            pytest.skip(
                "no discovery groups available to run smoke; set MDEASM_INTEGRATION_DISCOVERY_GROUP_NAME"
            )
        group_name = str((rows[0] or {}).get("name") or "").strip()
        if not group_name:
            pytest.skip(
                "unable to infer discovery group name from list response; set MDEASM_INTEGRATION_DISCOVERY_GROUP_NAME"
            )

    payload = ws.run_discovery_group(
        group_name,
        disco_runs_max_retry=2,
        disco_runs_backoff_max_s=3,
        noprint=True,
    )
    assert isinstance(payload, dict)
    assert group_name in payload


def test_integration_smoke_saved_filters_lifecycle():
    """
    Optional saved-filters lifecycle smoke.

    This validates put/get/list/delete behavior against the live tenant and always attempts
    cleanup of temporary filters created by the test.
    """
    if os.getenv("MDEASM_INTEGRATION_SAVED_FILTERS") != "1":
        pytest.skip("set MDEASM_INTEGRATION_SAVED_FILTERS=1 to enable saved-filters smoke")

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip("set WORKSPACE_NAME (or ensure only one workspace exists) to run saved-filters smoke")

    filter_name = f"mdeasm-smoke-sf-{int(time.time())}"
    deleted = False
    try:
        created = ws.create_or_replace_saved_filter(
            filter_name,
            query_filter='kind = "domain"',
            description="MDEASM integration smoke temporary saved filter",
            noprint=True,
        )
        created_name = str((created or {}).get("name") or (created or {}).get("id") or "").strip()
        assert created_name == filter_name

        fetched = ws.get_saved_filter(filter_name, noprint=True)
        fetched_name = str((fetched or {}).get("name") or (fetched or {}).get("id") or "").strip()
        assert fetched_name == filter_name

        listed = ws.get_saved_filters(max_page_size=100, noprint=True)
        rows = listed.get("value") if isinstance(listed, dict) else None
        if rows is None and isinstance(listed, dict):
            rows = listed.get("content")
        rows = rows if isinstance(rows, list) else []
        names = {str((row or {}).get("name") or (row or {}).get("id") or "").strip() for row in rows}
        assert filter_name in names

        ws.delete_saved_filter(filter_name, noprint=True)
        deleted = True

        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                ws.get_saved_filter(filter_name, noprint=True)
            except Exception as exc:
                if _extract_last_status(exc) == 404:
                    break
                raise
            time.sleep(2)
        else:
            pytest.fail(f"saved filter was not deleted within timeout: {filter_name}")
    finally:
        if not deleted:
            try:
                ws.delete_saved_filter(filter_name, noprint=True)
            except Exception:
                pass


def test_integration_smoke_resource_tags_lifecycle():
    """
    Optional workspace resource-tags lifecycle smoke.

    This validates list/get/put/delete behavior against the ARM tag endpoint at workspace scope.
    """
    if os.getenv("MDEASM_INTEGRATION_RESOURCE_TAGS") != "1":
        pytest.skip("set MDEASM_INTEGRATION_RESOURCE_TAGS=1 to enable resource-tags smoke")

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(
        http_timeout=(5, 30),
        retry=True,
        max_retry=2,
        backoff_max_s=5,
        init_data_plane_token=False,
    )
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip("set WORKSPACE_NAME (or ensure only one workspace exists) to run resource-tags smoke")

    tag_name = f"mdeasm-smoke-tag-{int(time.time())}"
    tag_value = f"cycle17-{int(time.time())}"
    deleted = False
    try:
        before = ws.list_resource_tags(noprint=True)
        assert isinstance(before, dict)

        put_payload = ws.put_resource_tag(tag_name, tag_value, noprint=True)
        assert str((put_payload or {}).get("name") or "").strip() == tag_name
        assert str((put_payload or {}).get("value") or "").strip() == tag_value

        get_payload = ws.get_resource_tag(tag_name, noprint=True)
        assert str((get_payload or {}).get("name") or "").strip() == tag_name
        assert str((get_payload or {}).get("value") or "").strip() == tag_value

        listed = ws.list_resource_tags(noprint=True)
        tags = (listed.get("tags") or {}) if isinstance(listed, dict) else {}
        assert str(tags.get(tag_name) or "").strip() == tag_value

        ws.delete_resource_tag(tag_name, noprint=True)
        deleted = True

        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                ws.get_resource_tag(tag_name, noprint=True)
            except Exception as exc:
                if _extract_last_status(exc) == 404:
                    break
                raise
            time.sleep(2)
        else:
            pytest.fail(f"resource tag was not deleted within timeout: {tag_name}")
    finally:
        if not deleted:
            try:
                ws.delete_resource_tag(tag_name, noprint=True)
            except Exception:
                pass


def test_integration_smoke_server_export_task():
    """
    Optional task-based server export smoke.

    This verifies the newer `assets:export` + task retrieval flow. It is skipped by default
    because it requires real credentials/workspace access and may depend on preview API versions.
    """
    if os.getenv("MDEASM_INTEGRATION_TASK_EXPORT") != "1":
        pytest.skip(
            "set MDEASM_INTEGRATION_TASK_EXPORT=1 to enable server export task integration smoke tests"
        )

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip("set WORKSPACE_NAME (or ensure only one workspace exists) to run task smoke")

    task = ws.create_assets_export_task(
        columns=["id", "kind"],
        query_filter='kind = "domain"',
        file_name="mdeasm-smoke-export.csv",
        noprint=True,
    )
    task_id = (task or {}).get("id")
    assert task_id

    task_details = ws.get_task(task_id, noprint=True)
    assert (task_details or {}).get("id") == task_id


def test_integration_smoke_server_export_task_artifact_fetch(tmp_path):
    """
    Optional full artifact lifecycle smoke.

    This covers `assets:export -> tasks get/poll -> tasks download -> tasks fetch` end-to-end.
    It is skipped by default because it requires real credentials/workspace access and may
    take longer than basic smoke tests.
    """
    if os.getenv("MDEASM_INTEGRATION_TASK_ARTIFACT") != "1":
        pytest.skip(
            "set MDEASM_INTEGRATION_TASK_ARTIFACT=1 to enable task artifact lifecycle smoke"
        )

    required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"missing required env vars: {', '.join(missing)}")

    ws = mdeasm.Workspaces(http_timeout=(5, 30), retry=True, max_retry=2, backoff_max_s=5)
    if not getattr(ws, "_default_workspace_name", ""):
        pytest.skip("set WORKSPACE_NAME (or ensure only one workspace exists) to run task smoke")

    task = ws.create_assets_export_task(
        columns=["id", "kind"],
        query_filter='kind = "domain"',
        file_name="mdeasm-smoke-export.csv",
        noprint=True,
    )
    task_id = str((task or {}).get("id") or "").strip()
    assert task_id

    deadline = time.time() + 300
    task_state = ""
    while time.time() < deadline:
        task_details = ws.get_task(task_id, noprint=True)
        task_state = str((task_details or {}).get("state") or "").strip().lower()
        if task_state in mdeasm_cli._TASK_TERMINAL_STATES:
            break
        time.sleep(5)
    else:
        pytest.skip(f"task did not reach terminal state within timeout: {task_id}")

    if task_state not in {"complete", "completed"}:
        pytest.skip(f"task ended in non-downloadable state: {task_state}")

    download_ref = ws.download_task(task_id, noprint=True)
    assert mdeasm_cli._extract_download_url(download_ref)

    artifact_path = tmp_path / "mdeasm-task-artifact-smoke.csv"
    rc = mdeasm_cli.main(
        [
            "tasks",
            "fetch",
            task_id,
            "--workspace-name",
            ws._default_workspace_name,
            "--artifact-out",
            str(artifact_path),
            "--overwrite",
            "--out",
            "-",
        ]
    )
    assert rc == 0
    assert artifact_path.exists()
    assert artifact_path.stat().st_size > 0
