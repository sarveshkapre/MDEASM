#!/usr/bin/python3
import sys

def main(severity: str = "high") -> int:
    """Retrieve and print workspace risk observations.

    Kept as a tiny example entrypoint so other scripts (and tests) can reuse it
    without triggering network calls at import time.
    """

    # Easiest to import mdeasm.py if it is in the same directory as this script.
    # Requires mdeasm.py VERSION 1.4
    import mdeasm

    if mdeasm._VERSION < 1.4:
        sys.stderr.write(
            f"requires mdeasm.py VERSION 1.4; current version: {mdeasm._VERSION}\n"
        )
        return 2

    easm = mdeasm.Workspaces()

    # The get_workspace_risk_observations() function will print the names of all risk
    # observation details retrieved, and where to access the asset and facet filter attributes.
    #
    # Retrieve asset details for low severity observations:
    # easm.get_workspace_risk_observations("low")
    #
    # Retrieve asset details for medium severity observations:
    # easm.get_workspace_risk_observations("medium")
    #
    # Retrieve asset details for high severity observations:
    # easm.get_workspace_risk_observations("high")
    #
    # Retrieve asset details for ALL observations:
    # easm.get_workspace_risk_observations()

    easm.get_workspace_risk_observations(severity)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
