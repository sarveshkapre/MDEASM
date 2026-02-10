#!/usr/bin/python3
import argparse
import csv
import json
import sys
from pathlib import Path


def _json_default(obj):
    # Best-effort serialization for nested structures returned by the API.
    try:
        return obj.as_dict()
    except Exception:
        try:
            return dict(vars(obj))
        except Exception:
            return str(obj)


def _parse_http_timeout(value: str) -> tuple[float, float]:
    """
    Parse `--http-timeout` as either:
      - "read" (seconds) -> (10, read)
      - "connect,read" (seconds) -> (connect, read)
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("empty timeout")

    if "," in raw:
        parts = [p.strip() for p in raw.split(",", 1)]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"invalid timeout format: {value!r}")
        connect_s = float(parts[0])
        read_s = float(parts[1])
    else:
        connect_s = 10.0
        read_s = float(raw)

    if connect_s <= 0 or read_s <= 0:
        raise ValueError("timeouts must be > 0")
    return (connect_s, read_s)


def _write_json(path: Path | None, payload) -> None:
    data = json.dumps(payload, indent=2, default=_json_default, sort_keys=True)
    if path is None:
        sys.stdout.write(data + "\n")
    else:
        path.write_text(data + "\n", encoding="utf-8")


def _write_csv(path: Path | None, rows: list[dict]) -> None:
    # Union-of-keys header to avoid silently dropping columns.
    fieldnames: list[str] = sorted({k for r in rows for k in r.keys()})

    out_fh = sys.stdout if path is None else path.open("w", encoding="utf-8", newline="")
    try:
        writer = csv.DictWriter(out_fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cooked = {}
            for k in fieldnames:
                v = row.get(k)
                if isinstance(v, (dict, list)):
                    cooked[k] = json.dumps(v, default=_json_default, sort_keys=True)
                else:
                    cooked[k] = v
            writer.writerow(cooked)
    finally:
        if path is not None:
            out_fh.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mdeasm_cli",
        description="Small CLI for MDEASM helper workflows (exports/automation).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    assets = sub.add_parser("assets", help="Asset inventory operations")
    assets_sub = assets.add_subparsers(dest="assets_cmd", required=True)

    export = assets_sub.add_parser("export", help="Export assets matching a query filter")
    export.add_argument("--filter", required=True, help="MDEASM query filter (string)")
    export.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format",
    )
    export.add_argument("--out", default="", help="Output path (default: stdout)")
    export.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    export.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    export.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    export.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable HTTP retry/backoff (default: enabled)",
    )
    export.add_argument(
        "--max-retry",
        type=int,
        default=None,
        help="Max retry attempts when retry is enabled (default: helper default)",
    )
    export.add_argument(
        "--backoff-max-s",
        type=float,
        default=None,
        help="Max backoff sleep seconds between retries (default: helper default)",
    )
    export.add_argument(
        "--asset-list-name",
        default="assetList",
        help="Attribute name to store results on the Workspaces object",
    )
    export.add_argument("--page", type=int, default=0, help="Starting page (skip)")
    export.add_argument("--max-page-size", type=int, default=25, help="Max page size (1-100)")
    export.add_argument("--max-page-count", type=int, default=0, help="Max pages to fetch (0=unbounded)")
    export.add_argument("--get-all", action="store_true", help="Fetch all pages until exhausted")
    export.add_argument(
        "--no-facet-filters",
        action="store_true",
        help="Do not auto-create facet filters (faster for exports)",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "assets" and args.assets_cmd == "export":
        # Import inside the command so `--help` works without requiring env/config.
        import mdeasm

        ws_kwargs = {}
        if args.workspace_name:
            ws_kwargs["workspace_name"] = args.workspace_name
        if args.api_version:
            ws_kwargs["api_version"] = args.api_version
        if args.http_timeout is not None:
            ws_kwargs["http_timeout"] = args.http_timeout
        if args.no_retry:
            ws_kwargs["retry"] = False
        if args.max_retry is not None:
            ws_kwargs["max_retry"] = args.max_retry
        if args.backoff_max_s is not None:
            ws_kwargs["backoff_max_s"] = args.backoff_max_s

        ws = mdeasm.Workspaces(**ws_kwargs)
        ws.get_workspace_assets(
            query_filter=args.filter,
            asset_list_name=args.asset_list_name,
            page=args.page,
            max_page_size=args.max_page_size,
            max_page_count=args.max_page_count,
            get_all=args.get_all,
            auto_create_facet_filters=not args.no_facet_filters,
            workspace_name=args.workspace_name,
        )

        asset_list = getattr(ws, args.asset_list_name)
        rows = asset_list.as_dicts() if hasattr(asset_list, "as_dicts") else []

        out_path = Path(args.out) if args.out else None
        if args.format == "json":
            _write_json(out_path, rows)
        else:
            _write_csv(out_path, rows)
        return 0

    sys.stderr.write("unknown command\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
