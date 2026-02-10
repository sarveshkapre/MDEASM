import json
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))

import mdeasm_cli  # noqa: E402


def test_cli_saved_filters_list_json(monkeypatch, capsys):
    captured = {"calls": 0}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_saved_filters(self, **kwargs):
            captured["calls"] += 1
            return {
                "totalElements": 2,
                "value": [
                    {"name": "sfA", "displayName": "A", "filter": 'kind = "domain"'},
                    {"name": "sfB", "displayName": "B", "filter": 'kind = "host"'},
                ],
            }

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["saved-filters", "list", "--format", "json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert [x["name"] for x in out] == ["sfA", "sfB"]
    assert captured["calls"] == 1


def test_cli_saved_filters_list_lines(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_saved_filters(self, **kwargs):
            return {"totalElements": 1, "value": [{"name": "sfA", "displayName": "A", "filter": "x"}]}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["saved-filters", "list", "--format", "lines"])
    assert rc == 0
    out_lines = capsys.readouterr().out.splitlines()
    assert out_lines == ["sfA\tA\tx"]


def test_cli_saved_filters_get(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def get_saved_filter(self, name, **kwargs):
            assert name == "sfA"
            return {"name": "sfA", "filter": "x", "description": "d"}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["saved-filters", "get", "sfA"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "sfA"


def test_cli_saved_filters_put_filter_at_file(tmp_path, monkeypatch, capsys):
    filter_path = tmp_path / "filter.txt"
    filter_path.write_text('state = "confirmed" AND\nkind = "domain"\n', encoding="utf-8")
    captured = {}

    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def create_or_replace_saved_filter(self, name, query_filter, description, **kwargs):
            captured["name"] = name
            captured["query_filter"] = query_filter
            captured["description"] = description
            return {"name": name, "filter": query_filter, "description": description}

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(
        [
            "saved-filters",
            "put",
            "owned_domains",
            "--filter",
            f"@{filter_path}",
            "--description",
            "Owned domains",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "owned_domains"
    assert captured["query_filter"] == 'state = "confirmed" AND kind = "domain"'


def test_cli_saved_filters_delete_json(monkeypatch, capsys):
    class DummyWS:
        def __init__(self, *args, **kwargs):
            pass

        def delete_saved_filter(self, name, **kwargs):
            assert name == "sfA"
            return None

    fake_mdeasm = types.SimpleNamespace(Workspaces=DummyWS)
    monkeypatch.setitem(sys.modules, "mdeasm", fake_mdeasm)

    rc = mdeasm_cli.main(["saved-filters", "delete", "sfA", "--format", "json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"deleted": "sfA"}


@pytest.mark.parametrize("cmd", [["saved-filters"], ["saved-filters", "put", "x", "--description", "d"]])
def test_cli_saved_filters_argparse_errors(cmd):
    # `argparse` exits on parse errors.
    with pytest.raises(SystemExit):
        mdeasm_cli.main(cmd)
