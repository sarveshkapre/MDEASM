#!/usr/bin/python3
"""
Legacy wrapper for backwards compatibility.

Use `API/retrieve_risk_observations.py` (correct spelling) going forward.
"""


def main() -> int:
    from retrieve_risk_observations import main as real_main

    return real_main()


if __name__ == "__main__":
    raise SystemExit(main())
