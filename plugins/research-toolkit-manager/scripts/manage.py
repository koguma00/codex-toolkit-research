#!/usr/bin/env python3
"""Install and verify the pinned Research Codex plugin and skill set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Tuple


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = PLUGIN_ROOT / "registry" / "plugins.lock.json"
CODEX_ROOT = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
SKILLS_ROOT = CODEX_ROOT / "skills"
BACKUPS_ROOT = CODEX_ROOT / "research-toolkit-backups"
PROVENANCE_NAME = ".research-toolkit-source.json"


class ManageError(RuntimeError):
    pass


def run(
    args: Iterable[str], *, check: bool = True, quiet: bool = False
) -> subprocess.CompletedProcess[str]:
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
    if (
        data.get("schema_version") != 2
        or not isinstance(data.get("managed_plugins"), list)
        or not isinstance(data.get("managed_skills"), list)
        or not isinstance(data.get("superseded_plugins", []), list)
    ):
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


def reconcile_plugin(dep: Dict[str, Any]) -> None:
    """Replace only the named managed plugin and marketplace with the pinned ref."""
    run(["codex", "plugin", "remove", dep["plugin_id"], "--json"], check=False)
    run(
        ["codex", "plugin", "marketplace", "remove", dep["marketplace"], "--json"],
        check=False,
    )
    add_marketplace(dep)
    run(["codex", "plugin", "add", dep["plugin_id"], "--json"])


def remove_superseded_plugin(dep: Dict[str, Any]) -> None:
    installed = installed_plugins()
    if dep["plugin_id"] in installed:
        run(["codex", "plugin", "remove", dep["plugin_id"], "--json"])
    current_marketplaces = marketplaces()
    if dep["marketplace"] in current_marketplaces:
        run(
            [
                "codex",
                "plugin",
                "marketplace",
                "remove",
                dep["marketplace"],
                "--json",
            ]
        )


def install_plugin(dep: Dict[str, Any]) -> None:
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
        reconcile_plugin(dep)

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


def github_slug(repository: str) -> str:
    parsed = urllib.parse.urlparse(repository)
    parts = [part for part in parsed.path.removesuffix(".git").split("/") if part]
    if parsed.hostname != "github.com" or len(parts) != 2:
        raise ManageError(f"Unsupported skill repository: {repository}")
    return "/".join(parts)


def copy_skill_from_archive(dep: Dict[str, Any], staging: Path) -> None:
    slug = github_slug(dep["repository"])
    archive_url = f"https://codeload.github.com/{slug}/zip/{dep['commit']}"
    source_parts = PurePosixPath(dep["path"]).parts

    with tempfile.TemporaryDirectory(prefix="research-toolkit-download-") as temp_dir:
        archive_path = Path(temp_dir) / "source.zip"
        try:
            with urllib.request.urlopen(archive_url, timeout=60) as response:
                archive_path.write_bytes(response.read())
        except (OSError, TimeoutError) as exc:
            raise ManageError(
                f"Cannot download {dep['name']} from {archive_url}"
            ) from exc

        found_skill = False
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for info in archive.infolist():
                    parts = PurePosixPath(info.filename).parts
                    if len(parts) <= len(source_parts):
                        continue
                    if tuple(parts[1 : 1 + len(source_parts)]) != source_parts:
                        continue
                    relative = parts[1 + len(source_parts) :]
                    if not relative or info.is_dir():
                        continue
                    target = staging.joinpath(*relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    if relative == ("SKILL.md",):
                        found_skill = True
        except (OSError, zipfile.BadZipFile) as exc:
            raise ManageError(f"Cannot unpack {dep['name']}") from exc

    if not found_skill:
        raise ManageError(f"No SKILL.md found at {dep['path']} in {dep['repository']}")


def adapt_skill_for_codex(dep: Dict[str, Any], staging: Path) -> None:
    adapter = dep.get("codex_adapter")
    skill_path = staging / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    if adapter == "eli5-v1":
        original_description = (
            "description: Explain a topic like I'm a 5 year old. Use when the user types "
            "/eli5 <topic> or asks for a dead-simple picture explainer of how something works."
        )
        codex_description = (
            "description: Explain a topic in very simple language through an HTML artifact "
            "with large pictures and few words. Use when the user invokes /eli5 or $eli5, "
            "or asks for a simple visual explanation of how something works."
        )
        if original_description not in text or "Topic: $ARGUMENTS" not in text:
            raise ManageError("ELI5 upstream format changed; update codex_adapter")
        text = text.replace(original_description, codex_description, 1)
        text = text.replace(
            "Topic: $ARGUMENTS",
            "Use the topic supplied with the user's invocation or request.",
            1,
        )
        text += (
            "\n<!-- Modified for Codex compatibility by research-codex-toolkit: "
            "invocation metadata and argument handling. -->\n"
        )
    elif adapter == "handoff-v2":
        unsupported = (
            'argument-hint: "What will the next session be used for?"\n',
            "disable-model-invocation: true\n",
        )
        original_description = (
            "description: Compact the current conversation into a handoff document "
            "for another agent to pick up."
        )
        codex_description = (
            "description: Compact the current conversation into copyable Markdown "
            "for another agent to continue the work."
        )
        original_instruction = (
            "Write a handoff document summarising the current conversation so a fresh agent "
            "can continue the work. Save to the temporary directory of the user's OS - not "
            "the current workspace."
        )
        codex_instruction = (
            "Write a handoff document summarising the current conversation so a fresh agent "
            "can continue the work. Output it directly in the conversation inside one fenced "
            "Markdown code block so the user can copy and paste it. Do not save a file unless "
            "the user explicitly asks. Output no preamble or follow-up outside the block."
        )
        if (
            not all(line in text for line in unsupported)
            or original_description not in text
            or original_instruction not in text
        ):
            raise ManageError("Handoff upstream format changed; update codex_adapter")
        for line in unsupported:
            text = text.replace(line, "", 1)
        text = text.replace(original_description, codex_description, 1)
        text = text.replace(original_instruction, codex_instruction, 1)
    else:
        raise ManageError(f"Unknown Codex skill adapter: {adapter}")
    skill_path.write_text(text, encoding="utf-8")


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == PROVENANCE_NAME:
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def read_provenance(destination: Path) -> Dict[str, Any] | None:
    try:
        return json.loads((destination / PROVENANCE_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def install_skill(dep: Dict[str, Any]) -> None:
    SKILLS_ROOT.mkdir(parents=True, exist_ok=True)
    destination = SKILLS_ROOT / dep["skill_name"]
    staging = Path(
        tempfile.mkdtemp(prefix=f".{dep['skill_name']}.new-", dir=SKILLS_ROOT)
    )
    previous = None
    try:
        copy_skill_from_archive(dep, staging)
        adapt_skill_for_codex(dep, staging)
        provenance = {
            "managed_by": "research-codex-toolkit",
            "repository": dep["repository"],
            "ref": dep["ref"],
            "commit": dep["commit"],
            "path": dep["path"],
            "codex_adapter": dep["codex_adapter"],
            "content_sha256": tree_digest(staging),
        }
        (staging / PROVENANCE_NAME).write_text(
            json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
        )

        if destination.exists():
            installed_provenance = read_provenance(destination)
            if (
                installed_provenance
                and installed_provenance.get("managed_by") == "research-codex-toolkit"
            ):
                previous = SKILLS_ROOT / f".{dep['skill_name']}.old-{os.getpid()}"
            else:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)
                previous = BACKUPS_ROOT / f"{dep['skill_name']}-{timestamp}"
                print(f"Preserving existing {dep['skill_name']} at {previous}")
            destination.rename(previous)

        try:
            staging.rename(destination)
        except OSError:
            if previous and previous.exists() and not destination.exists():
                previous.rename(destination)
            raise

        if previous and previous.parent == SKILLS_ROOT:
            shutil.rmtree(previous)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def skill_status(dep: Dict[str, Any]) -> Tuple[str, str]:
    destination = SKILLS_ROOT / dep["skill_name"]
    if not (destination / "SKILL.md").is_file():
        return "-", "missing-or-mismatch"
    provenance = read_provenance(destination)
    if not provenance:
        return "unmanaged", "missing-or-mismatch"
    actual = str(provenance.get("commit", "unknown"))
    expected_fields = ("repository", "ref", "commit", "path", "codex_adapter")
    metadata_ok = all(provenance.get(key) == dep.get(key) for key in expected_fields)
    content_ok = provenance.get("content_sha256") == tree_digest(destination)
    return actual[:12], "ok" if metadata_ok and content_ok else "missing-or-mismatch"


def print_status(plugins: List[Dict[str, Any]], skills: List[Dict[str, Any]]) -> bool:
    installed = installed_plugins()
    all_ok = True
    print("TYPE\tNAME\tEXPECTED\tINSTALLED\tSTATUS")
    for dep in plugins:
        item = installed.get(dep["plugin_id"])
        actual = item.get("version", "-") if item else "-"
        ok = bool(item and item.get("enabled") and actual == dep["version"])
        status = "ok" if ok else "missing-or-mismatch"
        all_ok = all_ok and ok
        print(f"plugin\t{dep['name']}\t{dep['version']}\t{actual}\t{status}")
    for dep in skills:
        actual, status = skill_status(dep)
        all_ok = all_ok and status == "ok"
        print(f"skill\t{dep['name']}\t{dep['commit'][:12]}\t{actual}\t{status}")
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "update", "status"))
    args = parser.parse_args()

    if shutil.which("codex") is None:
        raise ManageError("Codex CLI is not available on PATH")

    lock = load_lock()
    plugins = lock["managed_plugins"]
    skills = lock["managed_skills"]
    superseded_plugins = lock.get("superseded_plugins", [])
    if args.action in {"install", "update"}:
        for dep in plugins:
            print(f"==> plugin: {dep['name']} {dep['version']}")
            install_plugin(dep)
        for dep in superseded_plugins:
            print(f"==> remove superseded plugin: {dep['name']}")
            remove_superseded_plugin(dep)
        for dep in skills:
            print(f"==> skill: {dep['name']} {dep['commit'][:12]}")
            install_skill(dep)

    return 0 if print_status(plugins, skills) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ManageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
