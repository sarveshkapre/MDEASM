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


def _write_json(path: Path | None, payload, *, pretty: bool) -> None:
    if pretty:
        data = json.dumps(payload, indent=2, default=_json_default, sort_keys=True)
    else:
        # Compact JSON is friendlier for pipes and large payloads.
        data = json.dumps(payload, default=_json_default, sort_keys=True, separators=(",", ":"))
    if path is None:
        sys.stdout.write(data + "\n")
    else:
        path.write_text(data + "\n", encoding="utf-8")


def _write_ndjson(path: Path | None, rows: list[dict]) -> None:
    out_fh = sys.stdout if path is None else path.open("w", encoding="utf-8", newline="\n")
    try:
        for row in rows:
            out_fh.write(json.dumps(row, default=_json_default, sort_keys=True, separators=(",", ":")) + "\n")
    finally:
        if path is not None:
            out_fh.close()


def _read_columns_file(path: Path) -> list[str]:
    cols: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cols.append(line)
    return cols


def _parse_columns_arg(values: list[str] | None) -> list[str]:
    """
    Accept columns as either:
      - repeated flags: --columns id --columns kind
      - comma-separated: --columns id,kind
    """
    if not values:
        return []
    out: list[str] = []
    for v in values:
        for part in (v or "").split(","):
            col = part.strip()
            if col:
                out.append(col)
    # Dedup while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for c in out:
        if c in seen:
            continue
        seen.add(c)
        deduped.append(c)
    return deduped


def _write_csv(path: Path | None, rows: list[dict], *, columns: list[str] | None = None) -> None:
    # Union-of-keys header to avoid silently dropping columns, unless columns are explicit.
    fieldnames: list[str] = columns or sorted({k for r in rows for k in r.keys()})

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
        choices=["json", "ndjson", "csv"],
        default="json",
        help="Output format",
    )
    export.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (repeatable; maps to INFO/DEBUG)",
    )
    export.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    export.add_argument(
        "--pretty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pretty-print JSON output (default: true; ignored for ndjson/csv)",
    )
    export.add_argument("--out", default="", help="Output path (default: stdout)")
    export.add_argument(
        "--columns",
        action="append",
        default=None,
        help="CSV only: column name(s) to include (repeatable or comma-separated)",
    )
    export.add_argument(
        "--columns-from",
        default="",
        help="CSV only: path to a newline-delimited columns file (blank lines and #comments ignored)",
    )
    export.add_argument(
        "--max-assets",
        type=int,
        default=0,
        help="Stop after exporting at most N assets (0=unbounded)",
    )
    export.add_argument(
        "--progress-every-pages",
        type=int,
        default=0,
        help="Emit progress estimate every N pages (0=default helper behavior)",
    )
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

        level = None
        if args.log_level:
            level = args.log_level
        elif args.verbose >= 2:
            level = "DEBUG"
        elif args.verbose == 1:
            level = "INFO"
        if level and hasattr(mdeasm, "configure_logging"):
            mdeasm.configure_logging(level)

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
        get_kwargs = dict(
            query_filter=args.filter,
            asset_list_name=args.asset_list_name,
            page=args.page,
            max_page_size=args.max_page_size,
            max_page_count=args.max_page_count,
            get_all=args.get_all,
            auto_create_facet_filters=not args.no_facet_filters,
            workspace_name=args.workspace_name,
            # Keep machine-readable stdout clean; status/progress goes to stderr.
            status_to_stderr=True,
            max_assets=args.max_assets or 0,
        )
        if args.progress_every_pages and args.progress_every_pages > 0:
            get_kwargs["track_every_N_pages"] = args.progress_every_pages
        else:
            # Only emit the initial/final status lines by default.
            get_kwargs["no_track_time"] = True

        ws.get_workspace_assets(**get_kwargs)

        asset_list = getattr(ws, args.asset_list_name)
        rows = asset_list.as_dicts() if hasattr(asset_list, "as_dicts") else []

        out_path = None if (not args.out or args.out == "-") else Path(args.out)
        if args.format == "json":
            _write_json(out_path, rows, pretty=bool(args.pretty))
        elif args.format == "ndjson":
            _write_ndjson(out_path, rows)
        else:
            columns = _parse_columns_arg(args.columns)
            if args.columns_from:
                columns = _read_columns_file(Path(args.columns_from)) + columns
                # Dedup while preserving file order first.
                columns = _parse_columns_arg(columns)
            _write_csv(out_path, rows, columns=(columns or None))
        return 0

    sys.stderr.write("unknown command\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
