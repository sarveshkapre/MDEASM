#!/usr/bin/python3
import argparse
import csv
import json
import math
import os
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version as pkg_version
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

    if not math.isfinite(connect_s) or not math.isfinite(read_s):
        raise ValueError("timeouts must be finite")
    if connect_s <= 0 or read_s <= 0:
        raise ValueError("timeouts must be > 0")
    return (connect_s, read_s)


def _cli_version() -> str:
    # Prefer the installed distribution version (CI installs `-e .`), but fall back to the
    # upstream helper's `_VERSION` when running directly from a checkout.
    try:
        return pkg_version("mdeasm")
    except PackageNotFoundError:
        try:
            import mdeasm  # type: ignore

            v = getattr(mdeasm, "_VERSION", None)
            if v is not None:
                return str(v)
        except Exception:
            pass
        return "unknown"


def _atomic_write_text(path: Path, data: str, *, encoding: str = "utf-8") -> None:
    """
    Best-effort atomic file write.

    Write to a temp file in the destination directory, then replace the final path. This avoids
    leaving partially-written output files if the process is interrupted mid-write.
    """
    tmp_fh = tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        newline="\n",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_fh.name)
    try:
        with tmp_fh:
            tmp_fh.write(data)
            tmp_fh.flush()
            try:
                os.fsync(tmp_fh.fileno())
            except OSError:
                # Some filesystems may not support fsync; atomic replace still helps.
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _atomic_open_text(path: Path, *, encoding: str = "utf-8", newline: str | None = None):
    """
    Open a temp file handle for atomic writes. Caller must write/close, then we replace `path`.
    """
    tmp_fh = tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        newline=newline,
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    return tmp_fh, Path(tmp_fh.name)


def _write_json(path: Path | None, payload, *, pretty: bool) -> None:
    if pretty:
        data = json.dumps(payload, indent=2, default=_json_default, sort_keys=True)
    else:
        # Compact JSON is friendlier for pipes and large payloads.
        data = json.dumps(payload, default=_json_default, sort_keys=True, separators=(",", ":"))
    if path is None:
        sys.stdout.write(data + "\n")
    else:
        _atomic_write_text(path, data + "\n", encoding="utf-8")


def _write_ndjson(path: Path | None, rows: list[dict]) -> None:
    if path is None:
        out_fh = sys.stdout
        for row in rows:
            out_fh.write(
                json.dumps(row, default=_json_default, sort_keys=True, separators=(",", ":")) + "\n"
            )
        return

    tmp_fh, tmp_path = _atomic_open_text(path, encoding="utf-8", newline="\n")
    try:
        with tmp_fh:
            for row in rows:
                tmp_fh.write(
                    json.dumps(row, default=_json_default, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
            tmp_fh.flush()
            try:
                os.fsync(tmp_fh.fileno())
            except OSError:
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _write_lines(path: Path | None, lines: list[str]) -> None:
    if path is None:
        out_fh = sys.stdout
        for line in lines:
            out_fh.write(str(line) + "\n")
        return
    data = "".join(f"{line}\n" for line in lines)
    _atomic_write_text(path, data, encoding="utf-8")


def _read_columns_file(path: Path) -> list[str]:
    cols: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cols.append(line)
    return cols


def _read_filter_text(text: str) -> str:
    """
    Normalize a filter read from disk/stdin:
    - strip leading/trailing whitespace
    - drop blank lines and full-line `#` comments
    - join remaining lines with spaces
    """
    parts: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts.append(line)
    return " ".join(parts).strip()


def _resolve_filter_arg(value: str) -> str:
    """
    Accept `--filter` as either a literal filter string or `@path` (or `@-` for stdin).
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("empty filter")

    if not raw.startswith("@"):
        return raw

    src = raw[1:].strip()
    if not src:
        raise ValueError("empty @filter source")

    if src == "-":
        text = sys.stdin.read()
        cooked = _read_filter_text(text)
        if not cooked:
            raise ValueError("empty filter read from stdin")
        return cooked

    text = Path(src).expanduser().read_text(encoding="utf-8")
    cooked = _read_filter_text(text)
    if not cooked:
        raise ValueError(f"empty filter read from file: {src}")
    return cooked


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


def _build_ws_kwargs(args) -> dict:
    ws_kwargs = {}
    if getattr(args, "workspace_name", ""):
        ws_kwargs["workspace_name"] = args.workspace_name
    if getattr(args, "api_version", None):
        ws_kwargs["api_version"] = args.api_version
    if getattr(args, "dp_api_version", None):
        ws_kwargs["dp_api_version"] = args.dp_api_version
    if getattr(args, "cp_api_version", None):
        ws_kwargs["cp_api_version"] = args.cp_api_version
    if getattr(args, "http_timeout", None) is not None:
        ws_kwargs["http_timeout"] = args.http_timeout
    if getattr(args, "no_retry", False):
        ws_kwargs["retry"] = False
    if getattr(args, "max_retry", None) is not None:
        ws_kwargs["max_retry"] = args.max_retry
    if getattr(args, "backoff_max_s", None) is not None:
        ws_kwargs["backoff_max_s"] = args.backoff_max_s
    return ws_kwargs


def _write_csv(path: Path | None, rows: list[dict], *, columns: list[str] | None = None) -> None:
    # Union-of-keys header to avoid silently dropping columns, unless columns are explicit.
    fieldnames: list[str] = columns or sorted({k for r in rows for k in r.keys()})

    def write_rows(out_fh) -> None:
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

    if path is None:
        write_rows(sys.stdout)
        return

    tmp_fh, tmp_path = _atomic_open_text(path, encoding="utf-8", newline="")
    try:
        with tmp_fh:
            write_rows(tmp_fh)
            tmp_fh.flush()
            try:
                os.fsync(tmp_fh.fileno())
            except OSError:
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Small CLI for MDEASM helper workflows (exports/automation).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {_cli_version()}")
    sub = p.add_subparsers(dest="cmd", required=True)

    assets = sub.add_parser("assets", help="Asset inventory operations")
    assets_sub = assets.add_subparsers(dest="assets_cmd", required=True)

    export = assets_sub.add_parser("export", help="Export assets matching a query filter")
    export.add_argument(
        "--filter",
        required=True,
        help="MDEASM query filter (string) or @path (or @- for stdin)",
    )
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
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    export.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
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
    export.add_argument(
        "--max-page-count", type=int, default=0, help="Max pages to fetch (0=unbounded)"
    )
    export.add_argument("--get-all", action="store_true", help="Fetch all pages until exhausted")
    export.add_argument(
        "--no-facet-filters",
        action="store_true",
        help="Do not auto-create facet filters (faster for exports)",
    )

    schema = assets_sub.add_parser(
        "schema", help="Print observed columns for a query (union-of-keys)"
    )
    schema.add_argument(
        "--filter",
        required=True,
        help="MDEASM query filter (string) or @path (or @- for stdin)",
    )
    schema.add_argument(
        "--format",
        choices=["lines", "json"],
        default="lines",
        help="Output format (default: lines suitable for --columns-from)",
    )
    schema.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase log verbosity (repeatable)"
    )
    schema.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    schema.add_argument("--out", default="", help="Output path (default: stdout)")
    schema.add_argument(
        "--max-assets",
        type=int,
        default=200,
        help="Sample at most N assets to infer columns (0=unbounded; default: 200)",
    )
    schema.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    schema.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    schema.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    schema.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    schema.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    schema.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable HTTP retry/backoff (default: enabled)",
    )
    schema.add_argument(
        "--max-retry",
        type=int,
        default=None,
        help="Max retry attempts when retry is enabled (default: helper default)",
    )
    schema.add_argument(
        "--backoff-max-s",
        type=float,
        default=None,
        help="Max backoff sleep seconds between retries (default: helper default)",
    )
    schema.add_argument("--page", type=int, default=0, help="Starting page (skip)")
    schema.add_argument("--max-page-size", type=int, default=25, help="Max page size (1-100)")
    schema.add_argument(
        "--max-page-count", type=int, default=0, help="Max pages to fetch (0=unbounded)"
    )
    schema.add_argument(
        "--get-all",
        action="store_true",
        help="Fetch pages until exhausted (bounded by --max-assets)",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "assets" and args.assets_cmd in ("export", "schema"):
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
        ws_kwargs = _build_ws_kwargs(args)

        try:
            query_filter = _resolve_filter_arg(args.filter)
        except Exception as e:
            sys.stderr.write(f"invalid --filter: {e}\n")
            return 2

        ws = mdeasm.Workspaces(**ws_kwargs)
        if args.assets_cmd == "export":
            get_kwargs = dict(
                query_filter=query_filter,
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

        if args.assets_cmd == "schema":
            get_kwargs = dict(
                query_filter=query_filter,
                asset_list_name="assetList",
                page=args.page,
                max_page_size=args.max_page_size,
                max_page_count=args.max_page_count,
                get_all=args.get_all,
                auto_create_facet_filters=False,
                workspace_name=args.workspace_name,
                status_to_stderr=True,
                max_assets=args.max_assets or 0,
                # Only emit the initial/final status lines by default.
                no_track_time=True,
            )
            ws.get_workspace_assets(**get_kwargs)

            asset_list = getattr(ws, "assetList", None)
            rows = asset_list.as_dicts() if asset_list and hasattr(asset_list, "as_dicts") else []

            cols = sorted({k for r in rows for k in r.keys()})
            out_path = None if (not args.out or args.out == "-") else Path(args.out)
            if args.format == "json":
                _write_json(out_path, cols, pretty=True)
            else:
                _write_lines(out_path, cols)
            return 0

    sys.stderr.write("unknown command\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
