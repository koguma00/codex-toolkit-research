# Platform notes

The workflow uses the OpenSSH configuration at `~/.ssh/config` on both
platforms. The Python helper normalizes Windows identity paths to forward
slashes before writing OpenSSH configuration.

The first successful reconnect stores non-secret connection metadata in the
local Codex home as `aica-reconnect.json`. Set up each computer independently;
do not copy private keys or this local profile through Git.

## macOS

- Required commands: `python3`, `ssh`, `scp`, `ssh-keygen`, `ssh-keyscan`.
- Private keys are stored with mode `0600`; `.ssh` is stored with mode `0700`.
- A supplied admin PEM is copied to `~/.ssh/aica-admin.pem`.

## Windows

- Install the Windows OpenSSH Client optional feature if `ssh.exe`, `scp.exe`,
  `ssh-keygen.exe`, or `ssh-keyscan.exe` is missing.
- Run the helper with `py -3`; use `python` if the Python launcher is absent.
- The default files are `%USERPROFILE%\.ssh\config`,
  `%USERPROFILE%\.ssh\known_hosts`, and
  `%USERPROFILE%\.ssh\aica-chatgpt-codex`.
- A supplied admin PEM is copied to `%USERPROFILE%\.ssh\aica-admin.pem`.
- The helper removes inherited ACLs from the private key and grants full
  access only to the current Windows account with `icacls`. If that command
  fails, stop and inspect the key's Security settings; do not make it readable
  by Everyone.

The remote commands always run on Ubuntu, so server paths and the forced SSH
entrypoint are identical regardless of the controlling computer.
