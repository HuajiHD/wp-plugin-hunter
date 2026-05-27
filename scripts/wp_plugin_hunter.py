#!/usr/bin/env python3
"""Fetch WordPress.org plugins and prepare php-audit-pipeline handoff.

This tool intentionally does not audit, triage, rank, or confirm vulnerabilities.
It only searches/downloads/extracts public WordPress.org plugin packages and
emits structured handoff data for PHP-Code-Audit-Skill's `php-audit-pipeline`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path


API_URL = "https://api.wordpress.org/plugins/info/1.2/"
DOWNLOAD_HOST = "downloads.wordpress.org"
USER_AGENT = "wp-plugin-audit-hunter/0.5 (+local plugin fetch for php-audit-pipeline)"


@dataclass
class PluginMeta:
    slug: str
    name: str
    version: str
    download_link: str
    active_installs: int | str | None = None
    last_updated: str | None = None


@dataclass
class FetchReport:
    plugin: PluginMeta
    zip_path: str
    extracted_path: str
    handoff: dict[str, object]


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def slug_safe(value: str) -> str:
    import re

    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return safe or "plugin"


def request_json(params: dict[str, str | int]) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def plugin_meta_from_api(data: dict) -> PluginMeta:
    return PluginMeta(
        slug=str(data.get("slug") or slug_safe(str(data.get("name", "plugin")))),
        name=str(data.get("name") or data.get("slug") or "unknown"),
        version=str(data.get("version") or "unknown"),
        download_link=str(data.get("download_link") or ""),
        active_installs=data.get("active_installs"),
        last_updated=data.get("last_updated"),
    )


def search_plugins(query: str, page: int, per_page: int) -> list[PluginMeta]:
    data = request_json(
        {
            "action": "query_plugins",
            "request[search]": query,
            "request[page]": page,
            "request[per_page]": per_page,
            "request[fields][downloadlink]": 1,
            "request[fields][active_installs]": 1,
            "request[fields][last_updated]": 1,
            "request[fields][short_description]": 0,
            "format": "json",
        }
    )
    return [plugin_meta_from_api(item) for item in data.get("plugins", [])]


def get_plugin(slug: str) -> PluginMeta | None:
    data = request_json(
        {
            "action": "plugin_information",
            "request[slug]": slug,
            "request[fields][downloadlink]": 1,
            "request[fields][active_installs]": 1,
            "request[fields][last_updated]": 1,
            "format": "json",
        }
    )
    if not isinstance(data, dict) or "slug" not in data:
        return None
    return plugin_meta_from_api(data)


def validate_download_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != DOWNLOAD_HOST:
        raise ValueError(f"refusing non-WordPress.org download URL: {url}")
    if not parsed.path.startswith("/plugin/") or not parsed.path.endswith(".zip"):
        raise ValueError(f"unexpected plugin download path: {url}")


def download_plugin(meta: PluginMeta, workspace: Path, force: bool) -> Path:
    validate_download_url(meta.download_link)
    downloads = workspace / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    zip_path = downloads / f"{slug_safe(meta.slug)}.{slug_safe(meta.version)}.zip"
    if zip_path.exists() and not force:
        return zip_path

    request = urllib.request.Request(meta.download_link, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        with zip_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    return zip_path


def safe_extract(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    dest_root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            try:
                target.relative_to(dest_root)
            except ValueError as exc:
                raise ValueError(f"zip path traversal blocked: {member.filename}") from exc
        archive.extractall(destination)


def extract_plugin(zip_path: Path, workspace: Path, slug: str, force: bool) -> Path:
    extract_root = workspace / "plugins" / slug_safe(slug)
    if extract_root.exists() and force:
        shutil.rmtree(extract_root)
    if not extract_root.exists():
        safe_extract(zip_path, extract_root)

    children = [child for child in extract_root.iterdir() if child.is_dir()]
    if len(children) == 1:
        return children[0]
    return extract_root


def handoff_for(meta: PluginMeta, plugin_dir: Path, report_path: Path, workspace: Path) -> dict[str, object]:
    source_path = str(plugin_dir)
    output_path = workspace / "audit" / slug_safe(meta.slug)
    fetch_report = str(report_path)
    prompt = "\n".join(
        [
            "Use `php-audit-pipeline` for a deep PHP white-box audit.",
            f"source_path: {source_path}",
            f"output_path: {output_path}",
            f"fetch_report: {fetch_report}",
            "Treat the target as a WordPress plugin and invoke `php-wordpress-audit` during the framework-specific phase.",
            "Do not use wp-plugin-audit-hunter output as vulnerability evidence; it only proves fetch/extraction metadata.",
        ]
    )
    return {
        "skill": "php-audit-pipeline",
        "framework_skill": "php-wordpress-audit",
        "source_path": source_path,
        "output_path": str(output_path),
        "target": source_path,
        "plugin": asdict(meta),
        "fetch_report": fetch_report,
        "prompt": prompt,
        "note": "wp-plugin-audit-hunter only fetched and extracted the plugin. php-audit-pipeline must perform all auditing, triage, confirmation, severity, and reporting.",
    }


def write_fetch_report(meta: PluginMeta, zip_path: Path, plugin_dir: Path, workspace: Path) -> FetchReport:
    reports_dir = workspace / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{slug_safe(meta.slug)}.fetch.json"
    handoff = handoff_for(meta, plugin_dir, report_path, workspace)
    report = FetchReport(
        plugin=meta,
        zip_path=str(zip_path),
        extracted_path=str(plugin_dir),
        handoff=handoff,
    )
    report_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def process_plugins(args: argparse.Namespace, plugins: list[PluginMeta]) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    reports_dir = workspace / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    fetched: list[FetchReport] = []
    for index, meta in enumerate(plugins[: args.max_plugins], start=1):
        if not meta.download_link:
            eprint(f"[skip] {meta.slug}: missing download link")
            continue
        eprint(f"[{index}/{min(len(plugins), args.max_plugins)}] fetching {meta.slug} {meta.version}")
        try:
            zip_path = download_plugin(meta, workspace, force=args.force)
            plugin_dir = extract_plugin(zip_path, workspace, meta.slug, force=args.force)
            report = write_fetch_report(meta, zip_path, plugin_dir, workspace)
            fetched.append(report)
            print(json.dumps(asdict(report), ensure_ascii=False))
            if args.first:
                break
        except (OSError, ValueError, urllib.error.URLError, zipfile.BadZipFile) as exc:
            eprint(f"[error] {meta.slug}: {exc}")
        if args.sleep > 0:
            time.sleep(args.sleep)

    summary = {
        "workspace": str(workspace),
        "downloaded": len(fetched),
        "fetched": [asdict(item) for item in fetched],
        "audit_handoff": fetched[0].handoff if fetched else None,
        "audit_engine": "php-audit-pipeline",
        "framework_skill": "php-wordpress-audit",
        "note": "No vulnerability scanning was performed. Use the handoff with php-audit-pipeline.",
    }
    summary_path = reports_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["summary"] = str(summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if fetched else 2


def add_common_options(parser: argparse.ArgumentParser, *, defaults: bool) -> None:
    default = None if defaults else argparse.SUPPRESS
    parser.add_argument("--workspace", default="./wp-audit-runs" if defaults else default)
    parser.add_argument("--max-plugins", type=int, default=10 if defaults else default)
    parser.add_argument("--sleep", type=float, default=0.2 if defaults else default)
    parser.add_argument("--force", action="store_true", default=False if defaults else default)
    parser.add_argument("--first", action="store_true", default=False if defaults else default, help="Stop after the first successfully fetched plugin.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch WordPress.org plugins and emit php-audit-pipeline handoff. No audit or triage is performed.",
    )
    add_common_options(parser, defaults=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search WordPress.org plugins by keyword.")
    add_common_options(search, defaults=False)
    search.add_argument("--query", required=True)
    search.add_argument("--page", type=int, default=1)
    search.add_argument("--per-page", type=int, default=25)

    slugs = subparsers.add_parser("slugs", help="Fetch explicit WordPress.org plugin slugs.")
    add_common_options(slugs, defaults=False)
    slugs.add_argument("--slug", action="append", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_plugins < 1:
        parser.error("--max-plugins must be at least 1")

    try:
        if args.command == "search":
            per_page = min(max(args.per_page, 1), 100)
            plugins = search_plugins(args.query, args.page, per_page)
            if not plugins:
                eprint(f"[empty] no plugins found for query: {args.query}")
                return 1
            return process_plugins(args, plugins)

        if args.command == "slugs":
            plugins: list[PluginMeta] = []
            for slug in args.slug:
                meta = get_plugin(slug)
                if meta is None:
                    eprint(f"[skip] slug not found: {slug}")
                    continue
                plugins.append(meta)
            if not plugins:
                eprint("[empty] no valid slugs found")
                return 1
            return process_plugins(args, plugins)
    except KeyboardInterrupt:
        eprint("[interrupted]")
        return 130

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
