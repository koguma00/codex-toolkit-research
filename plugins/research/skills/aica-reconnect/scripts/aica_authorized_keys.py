#!/usr/bin/env python3
"""Persist and restore forced-command AICA Codex SSH public keys."""

from __future__ import annotations

import argparse
import base64
import binascii
import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


KEY_RE = re.compile(
    r"(?P<type>ssh-ed25519|ssh-rsa|ecdsa-sha2-[^ ]+) "
    r"(?P<blob>[A-Za-z0-9+/]+={0,3})(?: (?P<comment>.*))?$"
)
OPTIONS = "no-agent-forwarding,no-port-forwarding,no-X11-forwarding,no-user-rc"


class KeyRegistryError(RuntimeError):
    pass


def reject_broad_root(root: Path) -> None:
    if not root.is_absolute() or len(root.parts) < 4:
        raise KeyRegistryError(f"refusing persistent root: {root}")


def managed_prefix(entrypoint: Path) -> str:
    return f'command="{entrypoint} --ssh-entrypoint",{OPTIONS}'


def parse_key(line: str) -> tuple[str, str, str]:
    match = KEY_RE.search(line.strip())
    if not match:
        raise KeyRegistryError("malformed SSH public key line")
    blob = match.group("blob")
    try:
        base64.b64decode(blob, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise KeyRegistryError("invalid SSH public key encoding") from exc
    return match.group("type"), blob, match.group("comment") or ""


def identity(line: str) -> tuple[str, str]:
    key_type, blob, _ = parse_key(line)
    return key_type, blob


def registry_name(line: str) -> str:
    key_type, blob, comment = parse_key(line)
    label = re.sub(r"[^A-Za-z0-9_.-]+", "-", comment).strip("-") or key_type
    digest = hashlib.sha256(blob.encode("ascii")).hexdigest()[:16]
    return f"{label[:48]}-{digest}.pub"


def atomic_write(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument(
        "--authorized-keys",
        type=Path,
        default=Path.home() / ".ssh" / "authorized_keys",
    )
    parser.add_argument("--add-line-base64")
    parser.add_argument("--environment-id")
    parser.add_argument("--self-delete", action="store_true")
    args = parser.parse_args()
    lock_descriptor: int | None = None

    try:
        root = args.root.expanduser().resolve()
        reject_broad_root(root)
        entrypoint = root / "tools" / "bootstrap" / "persistent_env.sh"
        codex = root / ".local" / "bin" / "codex"
        if not entrypoint.is_file() or not os.access(entrypoint, os.X_OK):
            raise KeyRegistryError(f"missing executable entrypoint: {entrypoint}")
        if not codex.exists():
            raise KeyRegistryError(f"missing standalone Codex launcher: {codex}")

        prefix = managed_prefix(entrypoint)
        authorized_path = args.authorized_keys
        authorized_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = authorized_path.with_name(".aica-codex-authorized-keys.lock")
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
        existing_text = (
            authorized_path.read_text(encoding="utf-8")
            if authorized_path.exists()
            else ""
        )
        existing_lines = [
            line.rstrip() for line in existing_text.splitlines() if line.strip()
        ]

        registry = root / "tools" / "bootstrap" / "authorized_keys.d"
        registry.mkdir(parents=True, exist_ok=True)
        os.chmod(registry, 0o700)

        candidates = [
            line for line in existing_lines if line.startswith(prefix + " ")
        ]
        if args.add_line_base64:
            try:
                added_line = base64.b64decode(
                    args.add_line_base64, validate=True
                ).decode("utf-8").strip()
            except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
                raise KeyRegistryError("invalid --add-line-base64 value") from exc
            if not added_line.startswith(prefix + " "):
                raise KeyRegistryError("new key does not use the required forced command")
            parse_key(added_line)
            candidates.append(added_line)

        seeded = 0
        by_identity: dict[tuple[str, str], str] = {}
        for line in candidates:
            key_identity = identity(line)
            by_identity[key_identity] = line
        for line in by_identity.values():
            destination = registry / registry_name(line)
            desired = line + "\n"
            if not destination.exists() or destination.read_text(encoding="utf-8") != desired:
                atomic_write(destination, desired)
                seeded += 1

        registered: dict[tuple[str, str], str] = {}
        for key_file in sorted(registry.glob("*.pub")):
            line = key_file.read_text(encoding="utf-8").strip()
            if not line.startswith(prefix + " "):
                raise KeyRegistryError(f"invalid registry entry: {key_file}")
            registered[identity(line)] = line

        current_by_identity: dict[tuple[str, str], str] = {}
        for line in existing_lines:
            try:
                current_by_identity[identity(line)] = line
            except KeyRegistryError:
                continue

        appended: list[str] = []
        for key_identity, line in registered.items():
            current = current_by_identity.get(key_identity)
            if current is None:
                existing_lines.append(line)
                appended.append(line)
            elif not current.startswith(prefix + " "):
                raise KeyRegistryError(
                    "a registered Codex key already exists with different or unrestricted options"
                )

        backup_path = None
        if appended:
            backup_dir = root / "tools" / "bootstrap" / "authorized_keys-backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(backup_dir, 0o700)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = backup_dir / f"authorized_keys-{timestamp}-{os.getpid()}"
            if authorized_path.exists():
                shutil.copy2(authorized_path, backup_path)
            else:
                atomic_write(backup_path, "")
            atomic_write(authorized_path, "\n".join(existing_lines) + "\n")
        elif authorized_path.exists():
            os.chmod(authorized_path, 0o600)

        environment_path = root / "tools" / "bootstrap" / "remote-control-environment-id"
        expected_environment = None
        if environment_path.exists():
            expected_environment = environment_path.read_text(encoding="utf-8").strip()
        if args.environment_id:
            if expected_environment and expected_environment != args.environment_id:
                raise KeyRegistryError(
                    "remote-control environment ID changed: "
                    f"expected {expected_environment}, got {args.environment_id}"
                )
            if not expected_environment:
                atomic_write(environment_path, args.environment_id + "\n")
                expected_environment = args.environment_id

        print(
            json.dumps(
                {
                    "status": "ok",
                    "registry": str(registry),
                    "registeredKeys": len(registered),
                    "seededKeys": seeded,
                    "restoredKeys": len(appended),
                    "backup": str(backup_path) if backup_path else None,
                    "expectedEnvironmentId": expected_environment,
                },
                separators=(",", ":"),
            )
        )
        return 0
    finally:
        if lock_descriptor is not None:
            os.close(lock_descriptor)
        if args.self_delete:
            try:
                Path(__file__).unlink()
            except OSError:
                pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyRegistryError as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
