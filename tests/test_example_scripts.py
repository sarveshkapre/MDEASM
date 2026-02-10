import sys
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "API"))


def test_retrieve_risk_observations_main_calls_high_by_default():
    import mdeasm
    import retrieve_risk_observations

    calls = []

    class DummyWS:
        def get_workspace_risk_observations(self, severity=None):
            calls.append(severity)

    with mock.patch.object(mdeasm, "_VERSION", 1.4):
        with mock.patch.object(mdeasm, "Workspaces", return_value=DummyWS()):
            assert retrieve_risk_observations.main() == 0

    assert calls == ["high"]


def test_legacy_retreive_script_delegates_to_retrieve_main():
    import retreive_risk_observations

    with mock.patch("retrieve_risk_observations.main", autospec=True, return_value=0) as main_mock:
        assert retreive_risk_observations.main() == 0

    main_mock.assert_called_once_with()
