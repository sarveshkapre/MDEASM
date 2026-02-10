#!/usr/bin/python3
import sys

# Easiest to import mdeasm.py if it is in the same directory as this script.
# Requires mdeasm.py VERSION 1.4
import mdeasm

if mdeasm._VERSION < 1.4:
    sys.exit(f"requires mdeasm.py VERSION 1.4; current version: {mdeasm._VERSION}")

easm = mdeasm.Workspaces()

# The get_workspace_risk_observations() function will print the names of all risk
# observation details retrieved, and where to access the asset and facet filter attributes.

# Retrieve asset details for low severity observations:
# easm.get_workspace_risk_observations("low")

# Retrieve asset details for medium severity observations:
# easm.get_workspace_risk_observations("medium")

# Retrieve asset details for high severity observations:
easm.get_workspace_risk_observations("high")

# Retrieve asset details for ALL observations:
# easm.get_workspace_risk_observations()

