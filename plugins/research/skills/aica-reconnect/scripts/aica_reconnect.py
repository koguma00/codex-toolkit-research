#!/usr/bin/env python3
"""Restore cross-platform SSH access to a persistent personal AICA Codex host."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable


DEFAULT_ADMIN_ALIAS = "aica-admin"
DEFAULT_CODEX_ALIAS = "aica-codex"
PROFILE_NAME = "aica-reconnect.json"
KEY_OPTIONS = "no-agent-forwarding,no-port-forwarding,no-X11-forwarding,no-user-rc"


class ReconnectError(RuntimeError):
    pass


def run(
    args: Iterable[str],
    *,
    check: bool = True,
    input_text: str | None = None,
    timeout: int = 45,
) -> subprocess.CompletedProcess[str]:
    command = [str(item) for item in args]
    try:
        result = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReconnectError(f"cannot run {' '.join(command)}: {exc}") from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise ReconnectError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{detail}"
        )
    return result


def require_commands(names: Iterable[str]) -> None:
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise ReconnectError(
            "missing required OpenSSH command(s): " + ", ".join(missing)
        )


def expand_identity(value: str | None) -> Path | None:
    if not value:
        return None
    unquoted = value.strip().strip('"').replace("\\", "/")
    return Path(unquoted).expanduser()


def config_identity(path: Path) -> str:
    home = Path.home().resolve()
    resolved = path.expanduser().resolve()
    try:
        relative = resolved.relative_to(home)
        value = "~/" + relative.as_posix()
    except ValueError:
        value = str(resolved).replace("\\", "/")
    return f'"{value}"' if any(character.isspace() for character in value) else value


def exact_host_block(lines: list[str], alias: str) -> tuple[int, int] | None:
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.lower().startswith("host "):
            continue
        names = stripped.split()[1:]
        if names != [alias]:
            continue
        end = len(lines)
        for later in range(index + 1, len(lines)):
            marker = lines[later].strip().lower()
            if marker.startswith("host ") or marker.startswith("match "):
                end = later
                break
        return index, end
    return None


def block_settings(text: str, alias: str) -> dict[str, str]:
    lines = text.splitlines()
    bounds = exact_host_block(lines, alias)
    if not bounds:
        return {}
    start, end = bounds
    settings: dict[str, str] = {}
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            settings[parts[0].lower()] = parts[1].strip()
    return settings


def upsert_host(text: str, alias: str, settings: list[tuple[str, str]]) -> str:
    lines = text.splitlines()
    bounds = exact_host_block(lines, alias)
    desired_keys = {key.lower() for key, _ in settings}
    desired_lines = [f"  {key} {value}" for key, value in settings]

    if bounds:
        start, end = bounds
        preserved = []
        for line in lines[start + 1 : end]:
            stripped = line.strip()
            key = stripped.split(None, 1)[0].lower() if stripped else ""
            if key not in desired_keys:
                preserved.append(line)
        replacement = [f"Host {alias}", *desired_lines, *preserved]
        lines[start:end] = replacement
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([f"Host {alias}", *desired_lines])
    return "\n".join(lines).rstrip() + "\n"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_ssh_config(path: Path, content: str) -> str | None:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old == content:
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.before-aica-reconnect-{timestamp}-{os.getpid()}")
    if path.exists():
        shutil.copy2(path, backup)
    atomic_write(path, content)
    if os.name != "nt":
        os.chmod(path.parent, 0o700)
    return str(backup) if backup.exists() else None


def default_profile_path() -> Path:
    configured_home = os.environ.get("CODEX_HOME")
    codex_home = (
        Path(configured_home).expanduser()
        if configured_home
        else Path.home() / ".codex"
    )
    return codex_home / PROFILE_NAME


def load_local_profile(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconnectError(f"cannot read local AICA profile: {path}") from exc
    if not isinstance(payload, dict):
        raise ReconnectError(f"local AICA profile is not a JSON object: {path}")
    return payload


def save_local_profile(path: Path, payload: dict[str, object]) -> None:
    atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def hydrate_args(args: argparse.Namespace) -> tuple[Path, bool]:
    profile_path = (
        Path(args.profile).expanduser().resolve()
        if args.profile
        else default_profile_path()
    )
    profile = load_local_profile(profile_path)
    mappings = {
        "host": "host",
        "user": "user",
        "root": "root",
        "admin_alias": "adminAlias",
        "codex_alias": "codexAlias",
    }
    for attribute, profile_key in mappings.items():
        if getattr(args, attribute) is None:
            value = profile.get(profile_key)
            if value is not None and not isinstance(value, str):
                raise ReconnectError(
                    f"invalid {profile_key} in local AICA profile: {profile_path}"
                )
            setattr(args, attribute, value)
    args.admin_alias = args.admin_alias or DEFAULT_ADMIN_ALIAS
    args.codex_alias = args.codex_alias or DEFAULT_CODEX_ALIAS
    return profile_path, bool(profile)


def secure_private_key(path: Path) -> None:
    if os.name == "nt":
        if shutil.which("icacls") is None or shutil.which("whoami") is None:
            raise ReconnectError(
                "Windows private-key permissions require icacls.exe and whoami.exe"
            )
        account = run(["whoami"]).stdout.strip()
        if not account:
            raise ReconnectError("cannot determine the current Windows account")
        run(["icacls", str(path), "/inheritance:r"])
        run(["icacls", str(path), "/grant:r", f"{account}:F"])
    else:
        os.chmod(path, 0o600)


def prepare_admin_key(supplied: str | None, configured: str | None) -> Path:
    if supplied:
        source = Path(supplied).expanduser().resolve()
        if not source.is_file():
            raise ReconnectError(f"admin private key not found: {source}")
        destination = Path.home() / ".ssh" / "aica-admin.pem"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise ReconnectError(
                f"refusing to overwrite a different admin key: {destination}"
            )
        if not destination.exists():
            shutil.copy2(source, destination)
        secure_private_key(destination)
        return destination

    candidates = [expand_identity(configured), Path.home() / ".ssh" / "aica-admin.pem"]
    for candidate in candidates:
        if candidate and candidate.is_file():
            secure_private_key(candidate)
            return candidate
    raise ReconnectError("aica-admin key is missing; rerun with --admin-key PATH")


def prepare_codex_key(configured: str | None, supplied_path: str | None) -> Path:
    candidate = Path(supplied_path).expanduser() if supplied_path else expand_identity(configured)
    key_path = candidate or (Path.home() / ".ssh" / "aica-chatgpt-codex")
    key_path = key_path.resolve()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        comment = f"aica-chatgpt-codex-{platform.system().lower()}-{socket.gethostname()}"
        run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", comment, "-f", str(key_path)])
    if not key_path.is_file():
        raise ReconnectError(f"Codex private key is not a file: {key_path}")
    secure_private_key(key_path)
    return key_path


def public_key(key_path: Path) -> tuple[str, str]:
    result = run(["ssh-keygen", "-y", "-f", str(key_path)])
    fields = result.stdout.strip().split()
    if len(fields) < 2:
        raise ReconnectError(f"cannot derive public key from {key_path}")
    return fields[0], fields[1]


def key_map(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) >= 3 and fields[-2].startswith(("ssh-", "ecdsa-")):
            keys[fields[-2]] = fields[-1]
    return keys


def fingerprints(keys: dict[str, str]) -> list[str]:
    result = []
    for key_type, blob in sorted(keys.items()):
        try:
            digest = hashlib.sha256(base64.b64decode(blob, validate=True)).digest()
        except (ValueError, binascii.Error):
            continue
        encoded = base64.b64encode(digest).decode("ascii").rstrip("=")
        result.append(f"{key_type} SHA256:{encoded}")
    return result


def known_keys(known_hosts: Path, host: str, port: int) -> dict[str, str]:
    if not known_hosts.exists():
        return {}
    result = run(
        ["ssh-keygen", "-F", f"[{host}]:{port}", "-f", str(known_hosts)],
        check=False,
    )
    return key_map(result.stdout)


def compare_host_keys(reference: dict[str, str], scanned: dict[str, str]) -> bool:
    common = set(reference) & set(scanned)
    return bool(common) and all(reference[key_type] == scanned[key_type] for key_type in common)


def scan_host_keys(host: str, port: int) -> dict[str, str]:
    result = run(["ssh-keyscan", "-T", "10", "-p", str(port), host], timeout=20)
    scanned = key_map(result.stdout)
    if not scanned:
        raise ReconnectError(f"no SSH host keys returned by {host}:{port}")
    return scanned


def remove_known_endpoint(known_hosts: Path, host: str, port: int) -> None:
    if known_hosts.exists():
        run(
            ["ssh-keygen", "-R", f"[{host}]:{port}", "-f", str(known_hosts)],
            check=False,
        )


def inspect_endpoint(
    *,
    host: str,
    port: int,
    prior_port: int | None,
    known_hosts: Path,
    trust_new: bool,
) -> tuple[list[str], bool, bool]:
    scanned = scan_host_keys(host, port)
    current = known_keys(known_hosts, host, port)
    prior = known_keys(known_hosts, host, prior_port) if prior_port else {}
    reference = current or prior
    reported = fingerprints(scanned)

    mismatch = bool(reference) and not compare_host_keys(reference, scanned)
    if mismatch:
        if not trust_new:
            raise ReconnectError(
                "SSH host key changed; explicit approval required. New fingerprints:\n"
                + "\n".join(reported)
            )
    elif not reference and not trust_new:
        raise ReconnectError(
            "SSH host key is not known; explicit approval required. Fingerprints:\n"
            + "\n".join(reported)
        )

    remove_current = bool(current) and mismatch
    accept_new = not current or remove_current
    return reported, remove_current, accept_new


def accept_endpoint(
    *,
    host: str,
    port: int,
    known_hosts: Path,
    admin_alias: str,
    remove_current: bool,
    accept_new: bool,
) -> None:
    if remove_current:
        remove_known_endpoint(known_hosts, host, port)
    if accept_new:
        run(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                admin_alias,
                "true",
            ],
            timeout=20,
        )


def ssh_command(
    alias: str, remote_command: str, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            alias,
            remote_command,
        ],
        check=check,
        timeout=35,
    )


def parse_last_json(output: str) -> dict[str, object]:
    for line in reversed(output.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ReconnectError("command did not return a JSON object")


def remote_json(alias: str, remote_command: str) -> dict[str, object]:
    result = ssh_command(alias, remote_command, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise ReconnectError(detail)
    return parse_last_json(result.stdout)


def forced_public_line(root: str, key_path: Path) -> str:
    key_type, blob = public_key(key_path)
    comment = f"aica-chatgpt-codex-{platform.system().lower()}-{socket.gethostname()}"
    entrypoint = f"{root}/tools/bootstrap/persistent_env.sh"
    return f'command="{entrypoint} --ssh-entrypoint",{KEY_OPTIONS} {key_type} {blob} {comment}'


def remote_helper_command(
    helper_path: str,
    root: str,
    public_line: str | None,
    environment_id: str | None,
    self_delete: bool,
) -> str:
    arguments = [
        "python3",
        helper_path,
        "--root",
        root,
    ]
    if public_line:
        encoded = base64.b64encode(public_line.encode("utf-8")).decode("ascii")
        arguments.extend(["--add-line-base64", encoded])
    if environment_id:
        arguments.extend(["--environment-id", environment_id])
    if self_delete:
        arguments.append("--self-delete")
    return " ".join(shlex.quote(argument) for argument in arguments)


def upload_and_run_key_helper(
    *,
    admin_alias: str,
    root: str,
    public_line: str | None,
    environment_id: str | None = None,
    self_delete: bool = True,
) -> dict[str, object]:
    local_helper = Path(__file__).with_name("aica_authorized_keys.py")
    remote_helper = f"/tmp/aica-authorized-keys-{os.getpid()}.py"
    run(
        [
            "scp",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            str(local_helper),
            f"{admin_alias}:{remote_helper}",
        ],
        timeout=35,
    )
    command = remote_helper_command(
        remote_helper, root, public_line, environment_id, self_delete
    )
    result = ssh_command(admin_alias, command, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise ReconnectError(f"cannot restore Codex authorized keys: {detail}")
    return parse_last_json(result.stdout)


def start_daemon(codex_alias: str) -> dict[str, object]:
    payload = remote_json(codex_alias, "codex remote-control start --json")
    if payload.get("status") != "connected":
        raise ReconnectError(f"remote-control did not connect: {payload}")
    return payload


def issue_pairing(codex_alias: str, start_payload: dict[str, object]) -> dict[str, object]:
    try:
        pair = remote_json(codex_alias, "codex remote-control pair --json")
    except ReconnectError as first_error:
        if "timed out" not in str(first_error).lower():
            raise
        remote_json(codex_alias, "codex remote-control stop --json")
        start_payload = start_daemon(codex_alias)
        pair = remote_json(codex_alias, "codex remote-control pair --json")

    if pair.get("environmentId") != start_payload.get("environmentId"):
        raise ReconnectError("pairing response used a different environment ID")
    return pair


def codex_environment(codex_alias: str) -> str:
    command = (
        'printf "HOME=%s\\nCODEX_HOME=%s\\nCODEX=%s\\n" '
        '"$HOME" "$CODEX_HOME" "$(command -v codex)"; codex --version'
    )
    result = ssh_command(codex_alias, command)
    return result.stdout.strip()


def verify_codex_environment(output: str, root: str) -> dict[str, str]:
    values: dict[str, str] = {}
    version = ""
    for line in output.splitlines():
        if "=" in line and line.split("=", 1)[0] in {"HOME", "CODEX_HOME", "CODEX"}:
            key, value = line.split("=", 1)
            values[key] = value
        elif line.strip():
            version = line.strip()
    expected = {
        "HOME": root,
        "CODEX_HOME": f"{root}/.codex",
        "CODEX": f"{root}/.local/bin/codex",
    }
    mismatches = [
        f"{key}: expected {wanted}, got {values.get(key) or '<missing>'}"
        for key, wanted in expected.items()
        if values.get(key) != wanted
    ]
    if not version.startswith("codex-cli "):
        mismatches.append(f"Codex version output is invalid: {version or '<missing>'}")
    if mismatches:
        raise ReconnectError(
            "aica-codex did not enter the persistent personal environment:\n"
            + "\n".join(mismatches)
        )
    return {**values, "VERSION": version}


def read_expected_environment_id(codex_alias: str, root: str) -> str:
    environment_path = f"{root}/tools/bootstrap/remote-control-environment-id"
    quoted = shlex.quote(environment_path)
    result = ssh_command(
        codex_alias,
        f"if [ -f {quoted} ]; then cat {quoted}; fi",
    )
    return result.stdout.strip()


def verify_environment_id(actual: object, expected: str) -> str:
    environment_id = str(actual or "")
    if not environment_id:
        raise ReconnectError("remote-control did not return an environment ID")
    if expected and environment_id != expected:
        raise ReconnectError(
            "remote-control environment ID changed: "
            f"expected {expected}, got {environment_id}"
        )
    return environment_id


def validate_remote_root(root: str) -> None:
    path = PurePosixPath(root)
    if (
        not path.is_absolute()
        or str(path) != root
        or len(path.parts) < 4
        or any(part in {".", ".."} for part in path.parts)
        or not re.fullmatch(r"/[A-Za-z0-9._/-]+", root)
    ):
        raise ReconnectError(f"refusing unsafe persistent root: {root}")


def configure(args: argparse.Namespace) -> dict[str, object]:
    validate_remote_root(args.root)
    ssh_dir = Path.home() / ".ssh"
    config_path = ssh_dir / "config"
    known_hosts = ssh_dir / "known_hosts"
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    admin_settings = block_settings(original, args.admin_alias)
    codex_settings = block_settings(original, args.codex_alias)
    prior_port_text = admin_settings.get("port") or codex_settings.get("port")
    try:
        prior_port = int(prior_port_text) if prior_port_text else None
    except ValueError:
        prior_port = None

    host_fingerprints, remove_current, accept_new = inspect_endpoint(
        host=args.host,
        port=args.port,
        prior_port=prior_port,
        known_hosts=known_hosts,
        trust_new=args.trust_new_host_key,
    )

    admin_key = prepare_admin_key(args.admin_key, admin_settings.get("identityfile"))
    codex_key = prepare_codex_key(codex_settings.get("identityfile"), args.codex_key)
    common = [
        ("HostName", args.host),
        ("User", args.user),
        ("Port", str(args.port)),
        ("IdentitiesOnly", "yes"),
        ("PreferredAuthentications", "publickey"),
        ("ServerAliveInterval", "30"),
        ("ServerAliveCountMax", "6"),
        ("ControlMaster", "no"),
        ("ControlPersist", "no"),
        ("ControlPath", "none"),
    ]
    updated = upsert_host(
        original,
        args.admin_alias,
        common[:3] + [("IdentityFile", config_identity(admin_key)), *common[3:]],
    )
    updated = upsert_host(
        updated,
        args.codex_alias,
        common[:3] + [("IdentityFile", config_identity(codex_key)), *common[3:]],
    )
    config_backup = write_ssh_config(config_path, updated)

    accept_endpoint(
        host=args.host,
        port=args.port,
        known_hosts=known_hosts,
        admin_alias=args.admin_alias,
        remove_current=remove_current,
        accept_new=accept_new,
    )
    ssh_command(args.admin_alias, "true")

    public_line = forced_public_line(args.root, codex_key)
    key_result = upload_and_run_key_helper(
        admin_alias=args.admin_alias,
        root=args.root,
        public_line=public_line,
        self_delete=False,
    )
    environment = codex_environment(args.codex_alias)
    environment_details = verify_codex_environment(environment, args.root)
    start = start_daemon(args.codex_alias)
    expected_environment_id = str(key_result.get("expectedEnvironmentId") or "")
    environment_id = verify_environment_id(
        start.get("environmentId"), expected_environment_id
    )
    registry_result = upload_and_run_key_helper(
        admin_alias=args.admin_alias,
        root=args.root,
        public_line=public_line,
        environment_id=environment_id,
        self_delete=True,
    )

    result: dict[str, object] = {
        "status": "connected",
        "platform": platform.system(),
        "port": args.port,
        "sshConfig": str(config_path),
        "sshConfigBackup": config_backup,
        "hostFingerprints": host_fingerprints,
        "keyRegistry": key_result,
        "environment": environment,
        "environmentDetails": environment_details,
        "environmentId": environment_id,
        "environmentRegistry": registry_result,
        "daemon": start,
    }
    if args.pair:
        result["pairing"] = issue_pairing(args.codex_alias, start)
    return result


def status(args: argparse.Namespace) -> dict[str, object]:
    config_path = Path.home() / ".ssh" / "config"
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    result: dict[str, object] = {
        "sshConfig": str(config_path),
        "admin": block_settings(text, args.admin_alias),
        "codex": block_settings(text, args.codex_alias),
    }
    admin = ssh_command(args.admin_alias, "true", check=False)
    result["adminReachable"] = admin.returncode == 0
    codex = ssh_command(
        args.codex_alias,
        'printf "HOME=%s\\nCODEX_HOME=%s\\nCODEX=%s\\n" '
        '"$HOME" "$CODEX_HOME" "$(command -v codex)"; codex --version',
        check=False,
    )
    result["codexReachable"] = codex.returncode == 0
    result["environment"] = codex.stdout.strip()
    if codex.returncode == 0 and args.root:
        validate_remote_root(args.root)
        try:
            result["environmentDetails"] = verify_codex_environment(
                codex.stdout.strip(), args.root
            )
            result["persistentEnvironmentValid"] = True
        except ReconnectError as exc:
            result["persistentEnvironmentValid"] = False
            result["environmentError"] = str(exc)
    if admin.returncode != 0:
        result["adminError"] = admin.stderr.strip()
    if codex.returncode != 0:
        result["codexError"] = codex.stderr.strip()
    return result


def pair_only(args: argparse.Namespace) -> dict[str, object]:
    validate_remote_root(args.root)
    environment = codex_environment(args.codex_alias)
    environment_details = verify_codex_environment(environment, args.root)
    expected_environment_id = read_expected_environment_id(args.codex_alias, args.root)
    start = start_daemon(args.codex_alias)
    environment_id = verify_environment_id(
        start.get("environmentId"), expected_environment_id
    )
    pair = issue_pairing(args.codex_alias, start)
    return {
        "status": "connected",
        "environment": environment,
        "environmentDetails": environment_details,
        "environmentId": environment_id,
        "daemon": start,
        "pairing": pair,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "reconnect", "pair"))
    parser.add_argument("--port", type=int)
    parser.add_argument("--host")
    parser.add_argument("--user")
    parser.add_argument("--root")
    parser.add_argument("--admin-alias")
    parser.add_argument("--codex-alias")
    parser.add_argument("--admin-key")
    parser.add_argument("--codex-key")
    parser.add_argument("--profile")
    parser.add_argument("--trust-new-host-key", action="store_true")
    parser.add_argument("--pair", action="store_true")
    args = parser.parse_args()
    profile_path, profile_configured = hydrate_args(args)

    require_commands(("ssh", "scp", "ssh-keygen", "ssh-keyscan"))
    if args.action == "reconnect":
        if args.port is None or not (1 <= args.port <= 65535):
            raise ReconnectError("reconnect requires --port between 1 and 65535")
        missing = [
            option
            for option in ("host", "user", "root")
            if not getattr(args, option)
        ]
        if missing:
            raise ReconnectError(
                "first reconnect requires: "
                + " ".join(f"--{option} VALUE" for option in missing)
            )
        payload = configure(args)
        save_local_profile(
            profile_path,
            {
                "host": args.host,
                "user": args.user,
                "root": args.root,
                "adminAlias": args.admin_alias,
                "codexAlias": args.codex_alias,
                "lastPort": args.port,
            },
        )
        payload["localProfile"] = str(profile_path)
    elif args.action == "pair":
        if not args.root:
            raise ReconnectError(
                "pair requires --root PATH or a local profile from reconnect"
            )
        payload = pair_only(args)
    else:
        payload = status(args)
    payload.setdefault("localProfile", str(profile_path))
    payload["localProfileConfigured"] = profile_configured or args.action == "reconnect"
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconnectError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
