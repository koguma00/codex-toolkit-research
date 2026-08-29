#!/usr/bin/env python3
"""Install and verify the pinned Research Codex plugin set."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = PLUGIN_ROOT / "registry" / "plugins.lock.json"


class ManageError(RuntimeError):
    pass


def run(args: Iterable[str], *, check: bool = True, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    command = list(args)
    result = subprocess.run(command, text=True, capture_output=True)
    if not quiet:
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise ManageError(f"Command failed ({result.returncode}): {' '.join(command)}")
    return result


def codex_json(args: Iterable[str]) -> Dict[str, Any]:
    result = run(["codex", *args], quiet=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ManageError(f"Codex returned invalid JSON for: {' '.join(args)}") from exc


def load_lock() -> Dict[str, Any]:
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManageError(f"Cannot read lock file: {LOCK_PATH}") from exc
    if data.get("schema_version") != 1 or not isinstance(data.get("managed_plugins"), list):
        raise ManageError("Unsupported or malformed plugins.lock.json")
    return data


def marketplaces() -> Dict[str, Dict[str, Any]]:
    payload = codex_json(["plugin", "marketplace", "list", "--json"])
    return {item["name"]: item for item in payload.get("marketplaces", [])}


def installed_plugins() -> Dict[str, Dict[str, Any]]:
    payload = codex_json(["plugin", "list", "--json"])
    return {item["pluginId"]: item for item in payload.get("installed", [])}


def add_marketplace(dep: Dict[str, Any]) -> None:
    run(
        [
            "codex",
            "plugin",
            "marketplace",
            "add",
            dep["repository"],
            "--ref",
            dep["ref"],
            "--json",
        ]
    )


def reconcile(dep: Dict[str, Any]) -> None:
    """Replace only the named managed plugin and marketplace with the pinned ref."""
    run(["codex", "plugin", "remove", dep["plugin_id"], "--json"], check=False)
    run(
        ["codex", "plugin", "marketplace", "remove", dep["marketplace"], "--json"],
        check=False,
    )
    add_marketplace(dep)
    run(["codex", "plugin", "add", dep["plugin_id"], "--json"])


def install_one(dep: Dict[str, Any]) -> None:
    current_marketplaces = marketplaces()
    if dep["marketplace"] not in current_marketplaces:
        add_marketplace(dep)
    else:
        run(
            [
                "codex",
                "plugin",
                "marketplace",
                "upgrade",
                dep["marketplace"],
                "--json",
            ]
        )

    run(["codex", "plugin", "add", dep["plugin_id"], "--json"])
    installed = installed_plugins().get(dep["plugin_id"])
    if not installed or installed.get("version") != dep["version"]:
        print(f"Re-pinning {dep['name']} to {dep['ref']}...")
        reconcile(dep)

    installed = installed_plugins().get(dep["plugin_id"])
    if not installed:
        raise ManageError(f"{dep['plugin_id']} is not installed")
    if installed.get("version") != dep["version"]:
        raise ManageError(
            f"{dep['plugin_id']} version mismatch: expected {dep['version']}, "
            f"got {installed.get('version', 'unknown')}"
        )
    if not installed.get("enabled"):
        raise ManageError(f"{dep['plugin_id']} is installed but disabled")


def print_status(dependencies: List[Dict[str, Any]]) -> bool:
    installed = installed_plugins()
    all_ok = True
    print("NAME\tEXPECTED\tINSTALLED\tSTATUS")
    for dep in dependencies:
        item = installed.get(dep["plugin_id"])
        actual = item.get("version", "-") if item else "-"
        ok = bool(item and item.get("enabled") and actual == dep["version"])
        status = "ok" if ok else "missing-or-mismatch"
        all_ok = all_ok and ok
        print(f"{dep['name']}\t{dep['version']}\t{actual}\t{status}")
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "update", "status"))
    args = parser.parse_args()

    if shutil.which("codex") is None:
        raise ManageError("Codex CLI is not available on PATH")

    dependencies = load_lock()["managed_plugins"]
    if args.action in {"install", "update"}:
        for dep in dependencies:
            print(f"==> {dep['name']} {dep['version']}")
            install_one(dep)

    return 0 if print_status(dependencies) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ManageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
