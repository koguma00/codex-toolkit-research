---
name: aica-reconnect
description: Restore the personal AICA Codex SSH host from macOS or Windows when its proxy port changes or the server is recreated, and issue an iPhone ChatGPT Remote pairing code. Use for AICA port-change, SSH recovery, remote-control status, or iOS pairing requests.
---

# AICA Reconnect

Run this skill on the controlling macOS or Windows computer, not from a Codex
session already running on AICA. The local computer must have OpenSSH and an
`aica-admin` private key; the helper creates a separate per-device
`aica-codex` key when needed.

Resolve `scripts/aica_reconnect.py` relative to this file. Use `python3` on
macOS. On Windows, use `py -3` when available and otherwise `python`.

Host, SSH user, persistent root and alias settings are device-local. On the
first reconnect, ask the user for any missing values and pass `--host HOST
--user USER --root PERSISTENT_ROOT`. The helper saves them without credentials
in `~/.codex/aica-reconnect.json` (under `%USERPROFILE%` on Windows). Never
commit or print that local profile. Later reconnects need only the new port.

## Modes

- Status only: run `aica_reconnect.py status`.
- Restore after a port change or server recreation: run
  `aica_reconnect.py reconnect --port PORT --pair`.
- Issue only a fresh iOS code: run `aica_reconnect.py pair`.

If `aica-admin` is not configured or its key is missing, ask for the admin PEM
path and add `--admin-key PATH`. Do not search arbitrary files or guess among
multiple keys.

The reconnect helper updates only the explicit `aica-admin` and `aica-codex`
blocks in the user's default OpenSSH config. It then:

1. scans the new endpoint and compares its host keys with the prior port;
2. stops before trusting an unseen or changed host key;
3. verifies the admin connection;
4. registers the local device's public Codex key in the persistent AICA key
   registry and restores all registered forced-command keys without replacing
   unrelated `authorized_keys` entries;
5. verifies the persistent HOME, CODEX_HOME, standalone Codex path and version;
6. starts the remote-control daemon and, with `--pair`, prints a short-lived
   manual iOS pairing code and expiration.

When the helper reports that host-key approval is required, show the reported
fingerprints to the user. Rerun with `--trust-new-host-key` only after the user
explicitly approves those fingerprints. Never bypass the comparison with
`StrictHostKeyChecking=no`.

The pairing command retries once after a managed daemon restart when the first
request times out. Do not repeatedly restart it. A successful result must keep
the expected persistent environment ID; report any change instead of claiming
the old iOS connection was restored.

## Boundaries

- Never print, upload, commit, or copy a private key except when the user
  explicitly supplies an admin key to copy into their local `.ssh` directory.
- Never commit the device-local AICA profile or copy it to another device.
- Public keys may be sent only to the named AICA host. They are persisted on
  AICA, not in this public plugin repository.
- Do not copy `auth.json`, change Codex accounts, reinstall Codex, alter Conda
  or Python environments, or touch project files.
- Do not delete host keys or `authorized_keys` entries. The helpers create
  timestamped backups before changing either SSH configuration file.
- The user must enter the manual pairing code in the iPhone ChatGPT app.

Read [platform notes](references/platforms.md) only for first-time Windows
setup or when an SSH executable, path, or private-key permission check fails.
