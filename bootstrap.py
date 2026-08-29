#!/usr/bin/env python3
"""Install the public Research Codex toolkit on a new device."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPOSITORY = "https://github.com/koguma00/research-codex-toolkit.git"
MARKETPLACE = "research-codex"
MANAGER_PLUGIN = "research-toolkit-manager@research-codex"
MANAGER_SCRIPT = (
    Path(__file__).resolve().parent
    / "plugins"
    / "research-toolkit-manager"
    / "scripts"
    / "manage.py"
)


class BootstrapError(RuntimeError):
    pass


def run(args: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = list(args)
    result = subprocess.run(command, text=True, capture_output=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise BootstrapError(f"Command failed ({result.returncode}): {' '.join(command)}")
    return result


def marketplace_source() -> str | None:
    result = run(["codex", "plugin", "marketplace", "list", "--json"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError("Codex returned invalid marketplace JSON") from exc
    for item in payload.get("marketplaces", []):
        if item.get("name") == MARKETPLACE:
            return item.get("marketplaceSource", {}).get("source")
    return None


def main() -> int:
    if shutil.which("codex") is None:
        raise BootstrapError("Codex CLI is not available on PATH")

    source = marketplace_source()
    if source and source.rstrip("/").removesuffix(".git") != REPOSITORY.removesuffix(".git"):
        run(["codex", "plugin", "remove", MANAGER_PLUGIN, "--json"], check=False)
        run(["codex", "plugin", "marketplace", "remove", MARKETPLACE, "--json"])
        source = None

    if source:
        run(["codex", "plugin", "marketplace", "upgrade", MARKETPLACE, "--json"])
    else:
        run(
            [
                "codex",
                "plugin",
                "marketplace",
                "add",
                REPOSITORY,
                "--ref",
                "main",
                "--json",
            ]
        )

    run(["codex", "plugin", "add", MANAGER_PLUGIN, "--json"])
    run([sys.executable, str(MANAGER_SCRIPT), "install"])
    print("Installed. Start a new Codex conversation to load the toolkit.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
