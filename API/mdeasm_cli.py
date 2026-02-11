#!/usr/bin/python3
import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import sys
import tempfile
import time
import urllib.parse
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path

import requests

_TASK_TERMINAL_STATES = {"complete", "completed", "failed", "incomplete", "cancelled", "canceled"}
_DOWNLOAD_URL_PRIORITY_KEYS = (
    "downloadurl",
    "downloaduri",
    "artifacturl",
    "sasurl",
    "bloburl",
    "url",
    "uri",
    "href",
    "link",
)
_DEFAULT_RETRY_ON_STATUSES = (408, 425, 429, 500, 502, 503, 504)
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _parse_retry_on_statuses(value: str) -> set[int]:
    raw = (value or "").strip()
    if not raw:
        return set(_DEFAULT_RETRY_ON_STATUSES)
    out: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        code = int(token)
        if code < 100 or code > 599:
            raise ValueError(f"invalid HTTP status code: {code}")
        out.add(code)
    if not out:
        raise ValueError("empty retry-on status list")
    return out


def _normalize_sha256_hex(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith("sha256:"):
        raw = raw.split(":", 1)[1].strip()
    if not _SHA256_HEX_RE.fullmatch(raw):
        raise ValueError("sha256 must be a 64-character hex string")
    return raw


def _find_dotenv_path(start: Path | None = None) -> Path | None:
    """
    Find a `.env` file by walking up from `start` (default: CWD).

    This mirrors `python-dotenv`'s common "search parents" behavior and is useful for
    producing actionable diagnostics in `mdeasm doctor`.
    """
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        cand = p / ".env"
        if cand.is_file():
            return cand
    return None


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


def _atomic_open_binary(path: Path):
    tmp_fh = tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    return tmp_fh, Path(tmp_fh.name)


def _extract_download_url(payload) -> str:
    """
    Best-effort URL extraction from `tasks/{id}:download` response shapes.
    """
    candidates: list[tuple[str, str]] = []

    def _walk(node, key_hint: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(v, key_hint=str(k).strip().lower())
            return
        if isinstance(node, list):
            for item in node:
                _walk(item, key_hint=key_hint)
            return
        if isinstance(node, str):
            url = node.strip()
            if url.startswith(("https://", "http://")):
                candidates.append((key_hint, url))

    _walk(payload)
    if not candidates:
        return ""

    for preferred_key in _DOWNLOAD_URL_PRIORITY_KEYS:
        for key, value in candidates:
            if key == preferred_key:
                return value
    return candidates[0][1]


def _download_url_to_file(
    *,
    url: str,
    out_path: Path,
    timeout: tuple[float, float],
    retry: bool,
    max_retry: int,
    backoff_max_s: float,
    retry_on_statuses: set[int] | None,
    chunk_size: int,
    overwrite: bool,
    session=None,
    auth_token: str = "",
    expected_sha256: str = "",
) -> dict:
    if out_path.exists() and not overwrite:
        raise FileExistsError(f"output file already exists: {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    get_fn = getattr(session, "get", None) if session is not None else None
    if not callable(get_fn):
        get_fn = requests.get

    attempts = max(int(max_retry or 1), 1) if retry else 1
    chunk_size = max(int(chunk_size or 65536), 1024)
    retry_on_statuses = set(retry_on_statuses or _DEFAULT_RETRY_ON_STATUSES)
    last_error = ""
    last_status = None

    for attempt in range(1, attempts + 1):
        should_retry_attempt = False
        # Most task downloads return signed URLs that don't need auth headers, but some
        # environments can return protected URLs. Try unsigned first, then bearer-auth fallback.
        auth_modes = [False, True] if auth_token else [False]
        for use_auth in auth_modes:
            resp = None
            try:
                headers = {"Authorization": f"Bearer {auth_token}"} if use_auth else None
                resp = get_fn(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=timeout,
                    allow_redirects=True,
                )
                last_status = int(getattr(resp, "status_code", 0) or 0)

                if last_status == 200:
                    tmp_fh, tmp_path = _atomic_open_binary(out_path)
                    bytes_written = 0
                    sha256_digest = hashlib.sha256() if expected_sha256 else None
                    try:
                        with tmp_fh:
                            for chunk in resp.iter_content(chunk_size=chunk_size):
                                if not chunk:
                                    continue
                                tmp_fh.write(chunk)
                                bytes_written += len(chunk)
                                if sha256_digest is not None:
                                    sha256_digest.update(chunk)
                            tmp_fh.flush()
                            try:
                                os.fsync(tmp_fh.fileno())
                            except OSError:
                                pass
                        digest_hex = (
                            sha256_digest.hexdigest() if sha256_digest is not None else ""
                        )
                        if expected_sha256 and digest_hex != expected_sha256:
                            raise RuntimeError(
                                "artifact sha256 mismatch "
                                f"(expected={expected_sha256}, actual={digest_hex})"
                            )
                        os.replace(tmp_path, out_path)
                    except Exception:
                        try:
                            tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        raise

                    return {
                        "status_code": 200,
                        "bytes_written": bytes_written,
                        "used_bearer_auth": bool(use_auth),
                        "sha256": digest_hex,
                        "sha256_verified": bool(expected_sha256),
                    }

                body_snippet = ""
                try:
                    body_snippet = str(getattr(resp, "text", "") or "")[:500]
                except Exception:
                    body_snippet = ""
                last_error = f"http {last_status}: {body_snippet}"
                should_retry_attempt = bool(last_status in retry_on_statuses)
                if last_status not in (401, 403) or use_auth:
                    break

            except Exception as e:
                last_error = str(e)
                should_retry_attempt = True
                # If network/IO failed there is no value in retrying auth mode inside same attempt.
                break
            finally:
                if resp is not None:
                    try:
                        resp.close()
                    except Exception:
                        pass

        if attempt < attempts and should_retry_attempt:
            sleep_s = min(2 ** (attempt - 1), float(backoff_max_s or 30))
            sleep_s += random.uniform(0, min(0.25, sleep_s / 4 if sleep_s else 0.0))
            time.sleep(sleep_s)
            continue
        if not should_retry_attempt:
            break

    raise RuntimeError(
        f"artifact download failed after {attempts} attempts; last_status={last_status}; error={last_error}"
    )


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


def _write_ndjson(path: Path | None, rows) -> None:
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


def _read_schema_baseline(path: Path) -> list[str]:
    """
    Read baseline columns from either:
      - newline-delimited text (`id`, `kind`, ...)
      - JSON list (`["id","kind",...]`)
    """
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    as_list: list[str] = []
    is_json_candidate = path.suffix.lower() == ".json" or raw.startswith("[")
    if is_json_candidate:
        try:
            payload = json.loads(raw)
            if isinstance(payload, list):
                as_list = [str(item).strip() for item in payload if str(item).strip()]
            else:
                raise ValueError("baseline json must be a list of column names")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid baseline json: {e}") from e
    else:
        as_list = _read_columns_file(path)

    # Dedup while preserving input order.
    return _parse_columns_arg(as_list)


def _schema_diff(observed: list[str], baseline: list[str]) -> dict:
    observed_set = set(observed)
    baseline_set = set(baseline)
    added = sorted(observed_set - baseline_set)
    removed = sorted(baseline_set - observed_set)
    unchanged = sorted(observed_set & baseline_set)
    return {
        "has_drift": bool(added or removed),
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "observed_count": len(observed_set),
        "baseline_count": len(baseline_set),
    }


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


def _parse_resume_from(value: str) -> dict:
    """
    Parse `--resume-from` for client export mode.

    Accepted forms:
    - integer page number (for `skip` paging): `25`
    - mark/cursor token: `mark:<token>` or `<token>`
    - checkpoint file: `@/path/to/checkpoint.json`
    """
    raw = (value or "").strip()
    if not raw:
        return {}

    if raw.startswith("@"):
        src = raw[1:].strip()
        if not src:
            raise ValueError("empty checkpoint source")
        text = Path(src).expanduser().read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"empty checkpoint file: {src}")
        raw = text

    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid checkpoint json: {e}") from e
        if not isinstance(payload, dict):
            raise ValueError("checkpoint json must be an object")
        out = {}
        if payload.get("next_page") is not None and str(payload.get("next_page")).strip() != "":
            out["page"] = max(int(payload["next_page"]), 0)
        if payload.get("next_mark") is not None and str(payload.get("next_mark")).strip() != "":
            out["mark"] = str(payload["next_mark"]).strip()
        if not out:
            raise ValueError("checkpoint did not contain next_page or next_mark")
        return out

    if raw.lower().startswith("mark:"):
        mark = raw.split(":", 1)[1].strip()
        if not mark:
            raise ValueError("empty mark token")
        return {"mark": mark}

    try:
        return {"page": max(int(raw), 0)}
    except ValueError:
        # Treat non-integer values as opaque mark/cursor tokens.
        return {"mark": raw}


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


def _build_data_connection_properties(args) -> dict:
    kind = str(getattr(args, "kind", "") or "")
    if kind == "logAnalytics":
        workspace_id = str(getattr(args, "workspace_id", "") or "").strip()
        api_key = str(getattr(args, "api_key", "") or "").strip()
        if not workspace_id:
            raise ValueError("logAnalytics requires --workspace-id")
        if not api_key:
            raise ValueError("logAnalytics requires --api-key")
        return {"workspaceId": workspace_id, "apiKey": api_key}

    if kind == "azureDataExplorer":
        cluster_name = str(getattr(args, "cluster_name", "") or "").strip()
        database_name = str(getattr(args, "database_name", "") or "").strip()
        region = str(getattr(args, "region", "") or "").strip()
        if not cluster_name:
            raise ValueError("azureDataExplorer requires --cluster-name")
        if not database_name:
            raise ValueError("azureDataExplorer requires --database-name")
        if not region:
            raise ValueError("azureDataExplorer requires --region")
        return {
            "clusterName": cluster_name,
            "databaseName": database_name,
            "region": region,
        }

    raise ValueError("unsupported --kind (expected logAnalytics or azureDataExplorer)")


def _wait_for_task_state(
    ws,
    *,
    task_id: str,
    workspace_name: str,
    poll_interval_s: float,
    timeout_s: float,
):
    started = time.monotonic()
    last = ws.get_task(task_id, workspace_name=workspace_name, noprint=True)
    while True:
        state = str((last or {}).get("state", "")).strip().lower()
        if state in _TASK_TERMINAL_STATES:
            return last
        if timeout_s > 0 and (time.monotonic() - started) >= timeout_s:
            raise TimeoutError(
                f"timed out waiting for task {task_id} after {timeout_s}s (last state={state or 'unknown'})"
            )
        time.sleep(max(poll_interval_s, 0.1))
        last = ws.get_task(task_id, workspace_name=workspace_name, noprint=True)


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


def _write_csv_stream(path: Path | None, rows, *, columns: list[str]) -> None:
    # Streaming CSV requires explicit columns because the header cannot be inferred without
    # buffering all rows.
    fieldnames: list[str] = list(columns)

    def write_rows(out_fh) -> None:
        writer = csv.DictWriter(out_fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cooked = {}
            for k in fieldnames:
                v = row.get(k) if isinstance(row, dict) else None
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

    doctor = sub.add_parser("doctor", help="Environment/auth sanity checks (non-destructive)")
    doctor.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    doctor.add_argument("--out", default="", help="Output path (default: stdout)")
    doctor.add_argument(
        "--probe",
        action="store_true",
        help="Attempt a tiny control-plane probe (list workspaces). Requires env credentials.",
    )
    doctor.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (repeatable; maps to INFO/DEBUG)",
    )
    doctor.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    doctor.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    doctor.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    doctor.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    doctor.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable HTTP retry/backoff (default: enabled)",
    )
    doctor.add_argument(
        "--max-retry",
        type=int,
        default=None,
        help="Max retry attempts when retry is enabled (default: helper default)",
    )
    doctor.add_argument(
        "--backoff-max-s",
        type=float,
        default=None,
        help="Max backoff sleep seconds between retries (default: helper default)",
    )

    workspaces = sub.add_parser("workspaces", help="Workspace operations")
    workspaces_sub = workspaces.add_subparsers(dest="workspaces_cmd", required=True)

    ws_list = workspaces_sub.add_parser(
        "list", help="List available workspaces (stdout-safe structured output)"
    )
    ws_list.add_argument(
        "--format",
        choices=["json", "lines"],
        default="json",
        help="Output format (default: json)",
    )
    ws_list.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (repeatable; maps to INFO/DEBUG)",
    )
    ws_list.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    ws_list.add_argument("--out", default="", help="Output path (default: stdout)")
    ws_list.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    ws_list.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    ws_list.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    ws_list.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable HTTP retry/backoff (default: enabled)",
    )
    ws_list.add_argument(
        "--max-retry",
        type=int,
        default=None,
        help="Max retry attempts when retry is enabled (default: helper default)",
    )
    ws_list.add_argument(
        "--backoff-max-s",
        type=float,
        default=None,
        help="Max backoff sleep seconds between retries (default: helper default)",
    )

    saved_filters = sub.add_parser("saved-filters", help="Saved filter operations (data plane)")
    sf_sub = saved_filters.add_subparsers(dest="saved_filters_cmd", required=True)

    sf_list = sf_sub.add_parser("list", help="List saved filters")
    sf_list.add_argument(
        "--format",
        choices=["json", "lines"],
        default="json",
        help="Output format (default: json)",
    )
    sf_list.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    sf_list.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    sf_list.add_argument("--out", default="", help="Output path (default: stdout)")
    sf_list.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    sf_list.add_argument(
        "--filter",
        default="",
        help="Optional server-side filter expression for listing",
    )
    sf_list.add_argument("--get-all", action="store_true", help="Fetch all pages")
    sf_list.add_argument("--page", type=int, default=0, help="Starting page (skip)")
    sf_list.add_argument("--max-page-size", type=int, default=25, help="Max page size (1-100)")
    sf_list.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    sf_list.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    sf_list.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    sf_list.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    sf_list.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    sf_list.add_argument(
        "--max-retry",
        type=int,
        default=None,
        help="Max retry attempts when retry is enabled (default: helper default)",
    )
    sf_list.add_argument(
        "--backoff-max-s",
        type=float,
        default=None,
        help="Max backoff sleep seconds between retries (default: helper default)",
    )

    sf_get = sf_sub.add_parser("get", help="Get a saved filter by name")
    sf_get.add_argument("name", help="Saved filter name")
    sf_get.add_argument("--out", default="", help="Output path (default: stdout)")
    sf_get.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    sf_get.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    sf_get.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    sf_get.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    sf_get.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    sf_get.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    sf_get.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    sf_get.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    sf_get.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    sf_get.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    sf_put = sf_sub.add_parser("put", help="Create or replace a saved filter")
    sf_put.add_argument("name", help="Saved filter name")
    sf_put.add_argument(
        "--filter",
        required=True,
        help="MDEASM query filter (string) or @path (or @- for stdin)",
    )
    sf_put.add_argument(
        "--description",
        required=True,
        help="Saved filter description",
    )
    sf_put.add_argument("--out", default="", help="Output path (default: stdout)")
    sf_put.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    sf_put.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    sf_put.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    sf_put.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    sf_put.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    sf_put.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    sf_put.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    sf_put.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    sf_put.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    sf_put.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    sf_delete = sf_sub.add_parser("delete", help="Delete a saved filter by name")
    sf_delete.add_argument("name", help="Saved filter name")
    sf_delete.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    sf_delete.add_argument("--out", default="", help="Output path (default: stdout)")
    sf_delete.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    sf_delete.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    sf_delete.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    sf_delete.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    sf_delete.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    sf_delete.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    sf_delete.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    sf_delete.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    sf_delete.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    sf_delete.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    data_connections = sub.add_parser(
        "data-connections", help="Data connection operations (Log Analytics / Azure Data Explorer)"
    )
    dc_sub = data_connections.add_subparsers(dest="data_connections_cmd", required=True)

    dc_list = dc_sub.add_parser("list", help="List data connections")
    dc_list.add_argument(
        "--format",
        choices=["json", "lines"],
        default="json",
        help="Output format (default: json)",
    )
    dc_list.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    dc_list.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    dc_list.add_argument("--out", default="", help="Output path (default: stdout)")
    dc_list.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    dc_list.add_argument("--get-all", action="store_true", help="Fetch all pages")
    dc_list.add_argument("--page", type=int, default=0, help="Starting page (skip)")
    dc_list.add_argument("--max-page-size", type=int, default=25, help="Max page size (1-100)")
    dc_list.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    dc_list.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    dc_list.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    dc_list.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    dc_list.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    dc_list.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    dc_list.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    dc_get = dc_sub.add_parser("get", help="Get a data connection by name")
    dc_get.add_argument("name", help="Data connection name")
    dc_get.add_argument("--out", default="", help="Output path (default: stdout)")
    dc_get.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    dc_get.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    dc_get.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    dc_get.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    dc_get.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    dc_get.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    dc_get.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    dc_get.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    dc_get.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    dc_get.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    dc_put = dc_sub.add_parser("put", help="Create or replace a data connection")
    dc_put.add_argument("name", help="Data connection name")
    dc_put.add_argument(
        "--kind",
        required=True,
        choices=["logAnalytics", "azureDataExplorer"],
        help="Data connection kind",
    )
    dc_put.add_argument(
        "--content",
        default="assets",
        choices=["assets", "attackSurfaceInsights"],
        help="Export content scope (default: assets)",
    )
    dc_put.add_argument(
        "--frequency",
        default="weekly",
        choices=["daily", "weekly", "monthly"],
        help="Export frequency (default: weekly)",
    )
    dc_put.add_argument(
        "--frequency-offset",
        type=int,
        default=1,
        help="Offset used by schedule cadence (default: 1)",
    )
    dc_put.add_argument("--workspace-id", default="", help="Log Analytics workspace id")
    dc_put.add_argument("--api-key", default="", help="Log Analytics API key")
    dc_put.add_argument("--cluster-name", default="", help="Azure Data Explorer cluster name")
    dc_put.add_argument("--database-name", default="", help="Azure Data Explorer database name")
    dc_put.add_argument("--region", default="", help="Azure Data Explorer region")
    dc_put.add_argument("--out", default="", help="Output path (default: stdout)")
    dc_put.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    dc_put.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    dc_put.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    dc_put.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    dc_put.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    dc_put.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    dc_put.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    dc_put.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    dc_put.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    dc_put.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    dc_validate = dc_sub.add_parser("validate", help="Validate a data connection payload")
    dc_validate.add_argument(
        "name",
        nargs="?",
        default="",
        help="Optional data connection name included in validation payload",
    )
    dc_validate.add_argument(
        "--kind",
        required=True,
        choices=["logAnalytics", "azureDataExplorer"],
        help="Data connection kind",
    )
    dc_validate.add_argument(
        "--content",
        default="assets",
        choices=["assets", "attackSurfaceInsights"],
        help="Export content scope (default: assets)",
    )
    dc_validate.add_argument(
        "--frequency",
        default="weekly",
        choices=["daily", "weekly", "monthly"],
        help="Export frequency (default: weekly)",
    )
    dc_validate.add_argument(
        "--frequency-offset",
        type=int,
        default=1,
        help="Offset used by schedule cadence (default: 1)",
    )
    dc_validate.add_argument("--workspace-id", default="", help="Log Analytics workspace id")
    dc_validate.add_argument("--api-key", default="", help="Log Analytics API key")
    dc_validate.add_argument("--cluster-name", default="", help="Azure Data Explorer cluster name")
    dc_validate.add_argument("--database-name", default="", help="Azure Data Explorer database name")
    dc_validate.add_argument("--region", default="", help="Azure Data Explorer region")
    dc_validate.add_argument("--out", default="", help="Output path (default: stdout)")
    dc_validate.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity"
    )
    dc_validate.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    dc_validate.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    dc_validate.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    dc_validate.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    dc_validate.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    dc_validate.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    dc_validate.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    dc_validate.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    dc_validate.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    dc_delete = dc_sub.add_parser("delete", help="Delete a data connection by name")
    dc_delete.add_argument("name", help="Data connection name")
    dc_delete.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    dc_delete.add_argument("--out", default="", help="Output path (default: stdout)")
    dc_delete.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity"
    )
    dc_delete.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    dc_delete.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    dc_delete.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    dc_delete.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    dc_delete.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    dc_delete.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    dc_delete.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    dc_delete.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    dc_delete.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    tasks = sub.add_parser("tasks", help="Data-plane task operations")
    tasks_sub = tasks.add_subparsers(dest="tasks_cmd", required=True)

    tasks_list = tasks_sub.add_parser("list", help="List tasks")
    tasks_list.add_argument(
        "--format",
        choices=["json", "lines"],
        default="json",
        help="Output format (default: json)",
    )
    tasks_list.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    tasks_list.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    tasks_list.add_argument("--out", default="", help="Output path (default: stdout)")
    tasks_list.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    tasks_list.add_argument("--filter", default="", help="Optional server-side filter expression")
    tasks_list.add_argument("--orderby", default="", help="Optional ordering expression")
    tasks_list.add_argument("--get-all", action="store_true", help="Fetch all pages")
    tasks_list.add_argument("--page", type=int, default=0, help="Starting page (skip)")
    tasks_list.add_argument("--max-page-size", type=int, default=25, help="Max page size (1-100)")
    tasks_list.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    tasks_list.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    tasks_list.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    tasks_list.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    tasks_list.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    tasks_list.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    tasks_list.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    tasks_get = tasks_sub.add_parser("get", help="Get task details")
    tasks_get.add_argument("task_id", help="Task id")
    tasks_get.add_argument("--out", default="", help="Output path (default: stdout)")
    tasks_get.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    tasks_get.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    tasks_get.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    tasks_get.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    tasks_get.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    tasks_get.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    tasks_get.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    tasks_get.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    tasks_get.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    tasks_get.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    tasks_wait = tasks_sub.add_parser("wait", help="Wait for a task to reach a terminal state")
    tasks_wait.add_argument("task_id", help="Task id")
    tasks_wait.add_argument(
        "--format",
        choices=["json", "lines"],
        default="json",
        help="Output format (default: json)",
    )
    tasks_wait.add_argument("--out", default="", help="Output path (default: stdout)")
    tasks_wait.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    tasks_wait.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    tasks_wait.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    tasks_wait.add_argument(
        "--poll-interval-s",
        type=float,
        default=5.0,
        help="Polling interval seconds (default: 5)",
    )
    tasks_wait.add_argument(
        "--timeout-s",
        type=float,
        default=900.0,
        help="Maximum wait seconds (default: 900)",
    )
    tasks_wait.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    tasks_wait.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    tasks_wait.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    tasks_wait.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    tasks_wait.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    tasks_wait.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    tasks_wait.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    tasks_cancel = tasks_sub.add_parser("cancel", help="Cancel a task")
    tasks_cancel.add_argument("task_id", help="Task id")
    tasks_cancel.add_argument("--out", default="", help="Output path (default: stdout)")
    tasks_cancel.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    tasks_cancel.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    tasks_cancel.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    tasks_cancel.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    tasks_cancel.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    tasks_cancel.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    tasks_cancel.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    tasks_cancel.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    tasks_cancel.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    tasks_cancel.add_argument(
        "--backoff-max-s", type=float, default=None, help="Max backoff seconds"
    )

    tasks_run = tasks_sub.add_parser("run", help="Run a paused task")
    tasks_run.add_argument("task_id", help="Task id")
    tasks_run.add_argument("--out", default="", help="Output path (default: stdout)")
    tasks_run.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    tasks_run.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    tasks_run.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    tasks_run.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    tasks_run.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    tasks_run.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    tasks_run.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    tasks_run.add_argument("--no-retry", action="store_true", help="Disable HTTP retry/backoff")
    tasks_run.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    tasks_run.add_argument("--backoff-max-s", type=float, default=None, help="Max backoff seconds")

    tasks_download = tasks_sub.add_parser("download", help="Get a task download artifact reference")
    tasks_download.add_argument("task_id", help="Task id")
    tasks_download.add_argument("--out", default="", help="Output path (default: stdout)")
    tasks_download.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    tasks_download.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    tasks_download.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    tasks_download.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    tasks_download.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    tasks_download.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    tasks_download.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    tasks_download.add_argument(
        "--no-retry", action="store_true", help="Disable HTTP retry/backoff"
    )
    tasks_download.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    tasks_download.add_argument(
        "--backoff-max-s", type=float, default=None, help="Max backoff seconds"
    )

    tasks_fetch = tasks_sub.add_parser(
        "fetch",
        help="Download task artifact bytes to a local file path",
    )
    tasks_fetch.add_argument("task_id", help="Task id")
    tasks_fetch.add_argument(
        "--artifact-out",
        required=True,
        help="Output file path for downloaded artifact bytes",
    )
    tasks_fetch.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite artifact output path if it already exists",
    )
    tasks_fetch.add_argument(
        "--chunk-size",
        type=int,
        default=65536,
        help="Streaming download chunk size in bytes (default: 65536)",
    )
    tasks_fetch.add_argument(
        "--reference-out",
        default="",
        help="Optional path (or '-') to also write raw tasks download reference payload",
    )
    tasks_fetch.add_argument(
        "--out",
        default="",
        help="Summary output path (default: stdout)",
    )
    tasks_fetch.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    tasks_fetch.add_argument(
        "--log-level",
        default="",
        help="Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). Overrides -v/--verbose.",
    )
    tasks_fetch.add_argument(
        "--workspace-name",
        default="",
        help="Workspace name override (default: env WORKSPACE_NAME / helper default)",
    )
    tasks_fetch.add_argument(
        "--api-version",
        default=None,
        help="Override EASM api-version query param (default: env EASM_API_VERSION or helper default)",
    )
    tasks_fetch.add_argument(
        "--dp-api-version",
        default=None,
        help="Override data-plane api-version (default: env EASM_DP_API_VERSION or --api-version)",
    )
    tasks_fetch.add_argument(
        "--cp-api-version",
        default=None,
        help="Override control-plane api-version (default: env EASM_CP_API_VERSION or --api-version)",
    )
    tasks_fetch.add_argument(
        "--http-timeout",
        type=_parse_http_timeout,
        default=None,
        help="HTTP timeouts in seconds: 'read' or 'connect,read' (default: helper default)",
    )
    tasks_fetch.add_argument(
        "--no-retry", action="store_true", help="Disable HTTP retry/backoff"
    )
    tasks_fetch.add_argument("--max-retry", type=int, default=None, help="Max retry attempts")
    tasks_fetch.add_argument(
        "--backoff-max-s", type=float, default=None, help="Max backoff seconds"
    )
    tasks_fetch.add_argument(
        "--retry-on-statuses",
        default="408,425,429,500,502,503,504",
        help=(
            "Comma-separated HTTP statuses treated as retryable for artifact download "
            "(default: 408,425,429,500,502,503,504)"
        ),
    )
    tasks_fetch.add_argument(
        "--sha256",
        default="",
        help=(
            "Optional expected SHA-256 checksum (64 hex chars, optionally prefixed with 'sha256:'); "
            "download fails if artifact digest does not match"
        ),
    )

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
        "--mode",
        choices=["client", "server"],
        default="client",
        help="Export mode: client-side paging (default) or server-side task export",
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
        "--server-file-name",
        default="",
        help="Server export mode: requested output file name for the generated export artifact",
    )
    export.add_argument(
        "--columns",
        action="append",
        default=None,
        help="CSV mode: output columns; server mode: export task columns (repeatable or comma-separated)",
    )
    export.add_argument(
        "--columns-from",
        default="",
        help="CSV mode: output columns file; server mode: export task columns file",
    )
    export.add_argument(
        "--server-orderby",
        default="",
        help="Server export mode: optional orderby expression",
    )
    export.add_argument(
        "--orderby",
        default="",
        help="Client export mode: optional orderby expression",
    )
    export.add_argument(
        "--resume-from",
        default="",
        help="Client export mode: resume value (`<page>`, `mark:<token>`, or `@checkpoint.json`)",
    )
    export.add_argument(
        "--checkpoint-out",
        default="",
        help="Client export mode: write checkpoint JSON after each fetched page",
    )
    export.add_argument(
        "--wait",
        action="store_true",
        help="Server export mode: poll task status until terminal state",
    )
    export.add_argument(
        "--poll-interval-s",
        type=float,
        default=5.0,
        help="Server export mode: polling interval seconds when --wait is set (default: 5)",
    )
    export.add_argument(
        "--wait-timeout-s",
        type=float,
        default=900.0,
        help="Server export mode: max wait seconds when --wait is set (default: 900)",
    )
    export.add_argument(
        "--download-on-complete",
        action="store_true",
        help="Server export mode: call tasks/{id}:download after a completed task and include response in output",
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
        "schema_action",
        nargs="?",
        choices=["diff"],
        help="Optional action: `diff` compares observed columns against a baseline file",
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
        "--baseline",
        default="",
        help="Schema diff mode: baseline file path (newline columns or JSON list)",
    )
    schema.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Schema diff mode: exit with status 3 when drift is detected",
    )
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

    if args.cmd == "doctor":
        # Avoid importing `mdeasm` unless the user asked for a network probe; this keeps
        # `mdeasm doctor` usable as a "what am I missing?" command even before install.
        required = ["TENANT_ID", "SUBSCRIPTION_ID", "CLIENT_ID", "CLIENT_SECRET"]
        recommended = ["WORKSPACE_NAME"]
        optional = ["EASM_API_VERSION", "EASM_CP_API_VERSION", "EASM_DP_API_VERSION"]

        env_state = {}
        missing_required: list[str] = []
        for k in required + recommended + optional:
            v = os.getenv(k)
            if k == "CLIENT_SECRET":
                env_state[k] = {"set": bool(v)}
            else:
                env_state[k] = {"set": bool(v), "value": (v if v else "")}
        for k in required:
            if not env_state[k]["set"]:
                missing_required.append(k)

        dotenv_path = _find_dotenv_path()
        payload = {
            "ok": len(missing_required) == 0,
            "cwd": str(Path.cwd()),
            "dotenv": str(dotenv_path) if dotenv_path else "",
            "checks": {
                "env": {
                    "missing_required": missing_required,
                    "required": required,
                    "recommended": recommended,
                    "optional": optional,
                    "values": env_state,
                }
            },
        }

        if args.probe and not missing_required:
            try:
                import mdeasm  # type: ignore

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
                # Control-plane-only probe; do not require data-plane scope.
                ws_kwargs["workspace_name"] = ""
                ws_kwargs["init_data_plane_token"] = False
                ws_kwargs["emit_workspace_guidance"] = False

                ws = mdeasm.Workspaces(**ws_kwargs)
                names = sorted(list((getattr(ws, "_workspaces", {}) or {}).keys()), key=str.lower)
                payload["checks"]["probe"] = {
                    "ok": True,
                    "workspaces": {"count": len(names), "names": names},
                }
            except Exception as e:
                payload["ok"] = False
                payload["checks"]["probe"] = {"ok": False, "error": str(e)}

        out_path = None if (not args.out or args.out == "-") else Path(args.out)
        if args.format == "json":
            _write_json(out_path, payload, pretty=True)
        else:
            lines: list[str] = []
            if payload["ok"]:
                lines.append("ok: true")
            else:
                lines.append("ok: false")
            if payload.get("dotenv"):
                lines.append(f"dotenv: {payload['dotenv']}")
            if missing_required:
                lines.append("missing required env vars: " + ", ".join(missing_required))
            if args.probe:
                probe = payload.get("checks", {}).get("probe") or {}
                if probe.get("ok"):
                    ws = probe.get("workspaces") or {}
                    lines.append(f"probe: ok (workspaces={ws.get('count')})")
                else:
                    lines.append(f"probe: failed ({probe.get('error', '')})")
            _write_lines(out_path, lines)

        return 0 if payload["ok"] else 1

    if args.cmd == "workspaces" and args.workspaces_cmd == "list":
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
        # For listing, we want *all* workspaces regardless of WORKSPACE_NAME in the env.
        ws_kwargs["workspace_name"] = ""
        # This is a control-plane-only command; don't require data-plane scope.
        ws_kwargs["init_data_plane_token"] = False
        # Suppress default-workspace guidance; the command output is the guidance.
        ws_kwargs["emit_workspace_guidance"] = False

        try:
            ws = mdeasm.Workspaces(**ws_kwargs)
        except Exception as e:
            sys.stderr.write(f"failed to list workspaces: {e}\n")
            return 1

        items = []
        for name, endpoints in (getattr(ws, "_workspaces", {}) or {}).items():
            dp = endpoints[0] if isinstance(endpoints, (list, tuple)) and len(endpoints) > 0 else ""
            cp = endpoints[1] if isinstance(endpoints, (list, tuple)) and len(endpoints) > 1 else ""
            items.append({"name": name, "dataPlane": dp, "controlPlane": cp})
        items.sort(key=lambda d: str(d.get("name", "")).lower())

        out_path = None if (not args.out or args.out == "-") else Path(args.out)
        if args.format == "json":
            _write_json(out_path, items, pretty=True)
        else:
            lines = [f"{d['name']}\t{d['dataPlane']}\t{d['controlPlane']}" for d in items]
            _write_lines(out_path, lines)
        return 0

    if args.cmd == "saved-filters":
        import mdeasm

        level = None
        if getattr(args, "log_level", ""):
            level = args.log_level
        elif getattr(args, "verbose", 0) >= 2:
            level = "DEBUG"
        elif getattr(args, "verbose", 0) == 1:
            level = "INFO"
        if level and hasattr(mdeasm, "configure_logging"):
            mdeasm.configure_logging(level)

        ws_kwargs = _build_ws_kwargs(args)
        ws = mdeasm.Workspaces(**ws_kwargs)

        out_path = None if (not getattr(args, "out", "") or args.out == "-") else Path(args.out)

        if args.saved_filters_cmd == "list":
            page = max(int(args.page or 0), 0)
            max_page_size = max(int(args.max_page_size or 25), 1)
            values: list[dict] = []
            while True:
                resp = ws.get_saved_filters(
                    workspace_name=args.workspace_name,
                    filter_expr=args.filter,
                    skip=page,
                    max_page_size=max_page_size,
                    noprint=True,
                )
                batch = resp.get("value") or []
                if isinstance(batch, list):
                    values.extend(batch)
                if not args.get_all:
                    break
                total = resp.get("totalElements")
                try:
                    if total is not None and (page + len(batch)) >= int(total):
                        break
                except Exception:
                    pass
                if not batch or len(batch) < max_page_size:
                    break
                page += len(batch)

            if args.format == "json":
                _write_json(out_path, values, pretty=True)
            else:
                lines = []
                for item in values:
                    name = item.get("name") or item.get("id") or ""
                    display = item.get("displayName") or ""
                    filt = item.get("filter") or ""
                    lines.append(f"{name}\t{display}\t{filt}")
                _write_lines(out_path, lines)
            return 0

        if args.saved_filters_cmd == "get":
            resp = ws.get_saved_filter(args.name, workspace_name=args.workspace_name, noprint=True)
            _write_json(out_path, resp, pretty=True)
            return 0

        if args.saved_filters_cmd == "put":
            try:
                query_filter = _resolve_filter_arg(args.filter)
            except Exception as e:
                sys.stderr.write(f"invalid --filter: {e}\n")
                return 2
            resp = ws.create_or_replace_saved_filter(
                args.name,
                query_filter=query_filter,
                description=args.description,
                workspace_name=args.workspace_name,
                noprint=True,
            )
            _write_json(out_path, resp, pretty=True)
            return 0

        if args.saved_filters_cmd == "delete":
            ws.delete_saved_filter(args.name, workspace_name=args.workspace_name, noprint=True)
            if args.format == "json":
                _write_json(out_path, {"deleted": args.name}, pretty=True)
            else:
                _write_lines(out_path, [f"deleted {args.name}"])
            return 0

        sys.stderr.write("unknown saved-filters command\n")
        return 2

    if args.cmd == "data-connections":
        import mdeasm

        level = None
        if getattr(args, "log_level", ""):
            level = args.log_level
        elif getattr(args, "verbose", 0) >= 2:
            level = "DEBUG"
        elif getattr(args, "verbose", 0) == 1:
            level = "INFO"
        if level and hasattr(mdeasm, "configure_logging"):
            mdeasm.configure_logging(level)

        ws_kwargs = _build_ws_kwargs(args)
        ws = mdeasm.Workspaces(**ws_kwargs)
        out_path = None if (not getattr(args, "out", "") or args.out == "-") else Path(args.out)

        if args.data_connections_cmd == "list":
            payload = ws.list_data_connections(
                workspace_name=args.workspace_name,
                skip=args.page,
                max_page_size=args.max_page_size,
                get_all=args.get_all,
                noprint=True,
            )
            values = payload.get("value") if isinstance(payload, dict) else None
            if values is None:
                values = payload.get("content") if isinstance(payload, dict) else []
            if not isinstance(values, list):
                values = []

            if args.format == "json":
                _write_json(out_path, values, pretty=True)
            else:
                lines = []
                for item in values:
                    lines.append(
                        "\t".join(
                            [
                                str(item.get("name", "")),
                                str(item.get("kind", "")),
                                str(item.get("content", "")),
                                str(item.get("frequency", "")),
                                str(item.get("frequencyOffset", "")),
                                str(item.get("provisioningState", "")),
                            ]
                        )
                    )
                _write_lines(out_path, lines)
            return 0

        if args.data_connections_cmd == "get":
            payload = ws.get_data_connection(args.name, workspace_name=args.workspace_name, noprint=True)
            _write_json(out_path, payload, pretty=True)
            return 0

        if args.data_connections_cmd == "put":
            try:
                properties = _build_data_connection_properties(args)
            except ValueError as e:
                sys.stderr.write(f"invalid data connection arguments: {e}\n")
                return 2
            payload = ws.create_or_replace_data_connection(
                args.name,
                kind=args.kind,
                properties=properties,
                content=args.content,
                frequency=args.frequency,
                frequency_offset=args.frequency_offset,
                workspace_name=args.workspace_name,
                noprint=True,
            )
            _write_json(out_path, payload, pretty=True)
            return 0

        if args.data_connections_cmd == "validate":
            try:
                properties = _build_data_connection_properties(args)
            except ValueError as e:
                sys.stderr.write(f"invalid data connection arguments: {e}\n")
                return 2
            payload = ws.validate_data_connection(
                kind=args.kind,
                properties=properties,
                name=args.name,
                content=args.content,
                frequency=args.frequency,
                frequency_offset=args.frequency_offset,
                workspace_name=args.workspace_name,
                noprint=True,
            )
            _write_json(out_path, payload, pretty=True)
            return 0

        if args.data_connections_cmd == "delete":
            payload = ws.delete_data_connection(
                args.name,
                workspace_name=args.workspace_name,
                noprint=True,
            )
            if args.format == "json":
                _write_json(out_path, payload, pretty=True)
            else:
                _write_lines(out_path, [f"deleted {args.name}"])
            return 0

        sys.stderr.write("unknown data-connections command\n")
        return 2

    if args.cmd == "tasks":
        import mdeasm

        level = None
        if getattr(args, "log_level", ""):
            level = args.log_level
        elif getattr(args, "verbose", 0) >= 2:
            level = "DEBUG"
        elif getattr(args, "verbose", 0) == 1:
            level = "INFO"
        if level and hasattr(mdeasm, "configure_logging"):
            mdeasm.configure_logging(level)

        ws_kwargs = _build_ws_kwargs(args)
        ws = mdeasm.Workspaces(**ws_kwargs)
        out_path = None if (not getattr(args, "out", "") or args.out == "-") else Path(args.out)

        if args.tasks_cmd == "list":
            payload = ws.list_tasks(
                workspace_name=args.workspace_name,
                filter_expr=args.filter,
                orderby=args.orderby,
                skip=args.page,
                max_page_size=args.max_page_size,
                get_all=args.get_all,
                noprint=True,
            )
            values = payload.get("value") if isinstance(payload, dict) else None
            if values is None:
                values = payload.get("content") if isinstance(payload, dict) else []
            if not isinstance(values, list):
                values = []

            if args.format == "json":
                _write_json(out_path, values, pretty=True)
            else:
                lines = []
                for item in values:
                    lines.append(
                        "\t".join(
                            [
                                str(item.get("id", "")),
                                str(item.get("state", "")),
                                str(item.get("startedAt", "")),
                                str(item.get("completedAt", "")),
                            ]
                        )
                    )
                _write_lines(out_path, lines)
            return 0

        if args.tasks_cmd == "get":
            payload = ws.get_task(args.task_id, workspace_name=args.workspace_name, noprint=True)
            _write_json(out_path, payload, pretty=True)
            return 0

        if args.tasks_cmd == "wait":
            try:
                payload = _wait_for_task_state(
                    ws,
                    task_id=args.task_id,
                    workspace_name=args.workspace_name,
                    poll_interval_s=args.poll_interval_s,
                    timeout_s=args.timeout_s,
                )
            except TimeoutError as e:
                sys.stderr.write(f"{e}\n")
                return 1
            if args.format == "json":
                _write_json(out_path, payload, pretty=True)
            else:
                line = "\t".join(
                    [
                        str(payload.get("id", "")),
                        str(payload.get("state", "")),
                        str(payload.get("startedAt", "")),
                        str(payload.get("completedAt", "")),
                    ]
                )
                _write_lines(out_path, [line])
            return 0

        if args.tasks_cmd == "cancel":
            payload = ws.cancel_task(args.task_id, workspace_name=args.workspace_name, noprint=True)
            _write_json(out_path, payload, pretty=True)
            return 0

        if args.tasks_cmd == "run":
            payload = ws.run_task(args.task_id, workspace_name=args.workspace_name, noprint=True)
            _write_json(out_path, payload, pretty=True)
            return 0

        if args.tasks_cmd == "download":
            payload = ws.download_task(args.task_id, workspace_name=args.workspace_name, noprint=True)
            _write_json(out_path, payload, pretty=True)
            return 0

        if args.tasks_cmd == "fetch":
            payload = ws.download_task(args.task_id, workspace_name=args.workspace_name, noprint=True)
            artifact_url = _extract_download_url(payload)
            if not artifact_url:
                sys.stderr.write(
                    "task download response did not contain a usable artifact URL\n"
                )
                return 1

            if args.reference_out:
                ref_out = None if args.reference_out == "-" else Path(args.reference_out)
                _write_json(ref_out, payload, pretty=True)

            summary_out = None if (not args.out or args.out == "-") else Path(args.out)
            artifact_path = Path(args.artifact_out)
            timeout = args.http_timeout or getattr(ws, "_http_timeout", (10.0, 60.0))
            retry = not bool(args.no_retry)
            max_retry = (
                int(args.max_retry)
                if args.max_retry is not None
                else int(getattr(ws, "_default_max_retry", 5))
            )
            backoff_max_s = (
                float(args.backoff_max_s)
                if args.backoff_max_s is not None
                else float(getattr(ws, "_backoff_max_s", 30))
            )
            try:
                retry_on_statuses = _parse_retry_on_statuses(args.retry_on_statuses)
            except Exception as e:
                sys.stderr.write(f"invalid --retry-on-statuses: {e}\n")
                return 2
            try:
                expected_sha256 = _normalize_sha256_hex(args.sha256)
            except Exception as e:
                sys.stderr.write(f"invalid --sha256: {e}\n")
                return 2
            session = getattr(ws, "_session", None)
            auth_token = str(getattr(ws, "_dp_token", "") or "")

            try:
                result = _download_url_to_file(
                    url=artifact_url,
                    out_path=artifact_path,
                    timeout=timeout,
                    retry=retry,
                    max_retry=max_retry,
                    backoff_max_s=backoff_max_s,
                    retry_on_statuses=retry_on_statuses,
                    chunk_size=args.chunk_size,
                    overwrite=bool(args.overwrite),
                    session=session,
                    auth_token=auth_token,
                    expected_sha256=expected_sha256,
                )
            except Exception as e:
                redactor = getattr(mdeasm, "redact_sensitive_text", None)
                if callable(redactor):
                    msg = redactor(str(e))
                else:
                    msg = str(e)
                sys.stderr.write(f"artifact fetch failed: {msg}\n")
                return 1

            parsed = urllib.parse.urlparse(artifact_url)
            redacted_url = artifact_url
            redactor = getattr(mdeasm, "redact_sensitive_text", None)
            if callable(redactor):
                redacted_url = redactor(artifact_url)
            summary = {
                "task_id": args.task_id,
                "artifact_out": str(artifact_path),
                "bytes_written": int(result.get("bytes_written", 0)),
                "status_code": int(result.get("status_code", 0)),
                "used_bearer_auth": bool(result.get("used_bearer_auth", False)),
                "download_host": parsed.netloc,
                "download_url": redacted_url,
            }
            if expected_sha256:
                summary["sha256"] = str(result.get("sha256", ""))
                summary["sha256_verified"] = bool(result.get("sha256_verified", False))
            _write_json(summary_out, summary, pretty=True)
            return 0

        sys.stderr.write("unknown tasks command\n")
        return 2

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
            out_path = None if (not args.out or args.out == "-") else Path(args.out)

            columns: list[str] = _parse_columns_arg(args.columns)
            if args.columns_from:
                columns = _read_columns_file(Path(args.columns_from)) + columns
                # Dedup while preserving file order first.
                columns = _parse_columns_arg(columns)

            if args.mode == "server":
                if args.format != "json":
                    sys.stderr.write("server export mode only supports --format json\n")
                    return 2
                if not columns:
                    sys.stderr.write(
                        "server export mode requires --columns or --columns-from\n"
                    )
                    return 2
                if args.download_on_complete and not args.wait:
                    sys.stderr.write("--download-on-complete requires --wait\n")
                    return 2

                task = ws.create_assets_export_task(
                    columns=columns,
                    query_filter=query_filter,
                    file_name=args.server_file_name,
                    orderby=args.server_orderby,
                    workspace_name=args.workspace_name,
                    noprint=True,
                )
                output_payload = task
                task_id = str((task or {}).get("id", "")).strip()
                if args.wait:
                    if not task_id:
                        sys.stderr.write("server export task response did not include an id\n")
                        return 1
                    try:
                        final_task = _wait_for_task_state(
                            ws,
                            task_id=task_id,
                            workspace_name=args.workspace_name,
                            poll_interval_s=args.poll_interval_s,
                            timeout_s=args.wait_timeout_s,
                        )
                    except TimeoutError as e:
                        sys.stderr.write(f"{e}\n")
                        return 1
                    output_payload = final_task
                    state = str((final_task or {}).get("state", "")).strip().lower()
                    if args.download_on_complete and state in {"complete", "completed"}:
                        dl = ws.download_task(
                            task_id,
                            workspace_name=args.workspace_name,
                            noprint=True,
                        )
                        output_payload = {"task": final_task, "download": dl}

                _write_json(out_path, output_payload, pretty=bool(args.pretty))
                return 0

            try:
                resume_state = _parse_resume_from(args.resume_from)
            except Exception as e:
                sys.stderr.write(f"invalid --resume-from: {e}\n")
                return 2
            resume_page = args.page
            if "page" in resume_state:
                resume_page = int(resume_state["page"])
            resume_mark = str(resume_state.get("mark") or "").strip()

            progress_callback = None
            if args.checkpoint_out:
                checkpoint_path = Path(args.checkpoint_out)

                def _checkpoint_cb(state):
                    payload = {
                        "next_page": state.get("next_page"),
                        "next_mark": state.get("next_mark"),
                        "pages_completed": state.get("pages_completed"),
                        "assets_emitted": state.get("assets_emitted"),
                        "total_elements": state.get("total_elements"),
                        "last": bool(state.get("last")),
                    }
                    _atomic_write_text(
                        checkpoint_path,
                        json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )

                progress_callback = _checkpoint_cb

            if args.format == "csv" and not columns:
                columns = []

            if (
                args.no_facet_filters
                and hasattr(ws, "stream_workspace_assets")
                and args.format in ("ndjson", "csv")
            ):
                stream_kwargs = dict(
                    query_filter=query_filter,
                    page=resume_page,
                    max_page_size=args.max_page_size,
                    max_page_count=args.max_page_count,
                    get_all=args.get_all,
                    workspace_name=args.workspace_name,
                    # Keep machine-readable stdout clean; status/progress goes to stderr.
                    status_to_stderr=True,
                    max_assets=args.max_assets or 0,
                    orderby=args.orderby,
                )
                if resume_mark:
                    stream_kwargs["mark"] = resume_mark
                if progress_callback is not None:
                    stream_kwargs["progress_callback"] = progress_callback
                if args.progress_every_pages and args.progress_every_pages > 0:
                    stream_kwargs["track_every_N_pages"] = args.progress_every_pages
                else:
                    # Only emit the initial/final status lines by default.
                    stream_kwargs["no_track_time"] = True

                if args.format == "ndjson":
                    _write_ndjson(out_path, ws.stream_workspace_assets(**stream_kwargs))
                    return 0
                if args.format == "csv" and columns:
                    _write_csv_stream(
                        out_path, ws.stream_workspace_assets(**stream_kwargs), columns=columns
                    )
                    return 0

            get_kwargs = dict(
                query_filter=query_filter,
                asset_list_name=args.asset_list_name,
                page=resume_page,
                max_page_size=args.max_page_size,
                max_page_count=args.max_page_count,
                get_all=args.get_all,
                auto_create_facet_filters=not args.no_facet_filters,
                workspace_name=args.workspace_name,
                # Keep machine-readable stdout clean; status/progress goes to stderr.
                status_to_stderr=True,
                max_assets=args.max_assets or 0,
                orderby=args.orderby,
            )
            if resume_mark:
                get_kwargs["mark"] = resume_mark
            if progress_callback is not None:
                get_kwargs["progress_callback"] = progress_callback
            if args.progress_every_pages and args.progress_every_pages > 0:
                get_kwargs["track_every_N_pages"] = args.progress_every_pages
            else:
                # Only emit the initial/final status lines by default.
                get_kwargs["no_track_time"] = True

            ws.get_workspace_assets(**get_kwargs)

            asset_list = getattr(ws, args.asset_list_name)
            rows = asset_list.as_dicts() if hasattr(asset_list, "as_dicts") else []
            if args.format == "json":
                _write_json(out_path, rows, pretty=bool(args.pretty))
            elif args.format == "ndjson":
                _write_ndjson(out_path, rows)
            else:
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
            if args.schema_action == "diff":
                if not args.baseline:
                    sys.stderr.write("schema diff mode requires --baseline <path>\n")
                    return 2
                try:
                    baseline_cols = _read_schema_baseline(Path(args.baseline).expanduser())
                except Exception as e:
                    sys.stderr.write(f"invalid --baseline: {e}\n")
                    return 2

                payload = _schema_diff(cols, baseline_cols)
                if args.format == "json":
                    _write_json(out_path, payload, pretty=True)
                else:
                    lines: list[str] = []
                    lines.append(f"drift={str(payload['has_drift']).lower()}")
                    lines.append(f"observed_count={payload['observed_count']}")
                    lines.append(f"baseline_count={payload['baseline_count']}")
                    for col in payload["added"]:
                        lines.append(f"+ {col}")
                    for col in payload["removed"]:
                        lines.append(f"- {col}")
                    _write_lines(out_path, lines)

                if args.fail_on_drift and payload["has_drift"]:
                    return 3
                return 0

            if args.format == "json":
                _write_json(out_path, cols, pretty=True)
            else:
                _write_lines(out_path, cols)
            return 0

    sys.stderr.write("unknown command\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
