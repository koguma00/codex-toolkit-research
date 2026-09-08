import base64
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "research" / "skills" / "aica-reconnect"
RECONNECT_PATH = SKILL / "scripts" / "aica_reconnect.py"
KEY_HELPER_PATH = SKILL / "scripts" / "aica_authorized_keys.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reconnect = load_module("aica_reconnect", RECONNECT_PATH)
key_helper = load_module("aica_authorized_keys", KEY_HELPER_PATH)


class AicaReconnectTests(unittest.TestCase):
    def test_upsert_changes_only_exact_alias_and_preserves_extra_settings(self):
        original = """Host *
  AddKeysToAgent yes

Host aica-admin
  HostName old.example
  Port 1234
  Compression yes

Host aica-admin other-name
  Port 9999
"""
        updated = reconnect.upsert_host(
            original,
            "aica-admin",
            [("HostName", "new.example"), ("Port", "31001")],
        )
        settings = reconnect.block_settings(updated, "aica-admin")
        self.assertEqual(settings["hostname"], "new.example")
        self.assertEqual(settings["port"], "31001")
        self.assertEqual(settings["compression"], "yes")
        self.assertIn("Host aica-admin other-name\n  Port 9999", updated)
        self.assertIn("Host *\n  AddKeysToAgent yes", updated)

    def test_unknown_host_key_requires_explicit_approval(self):
        scanned = {"ssh-ed25519": base64.b64encode(b"new-key").decode("ascii")}
        with (
            mock.patch.object(reconnect, "scan_host_keys", return_value=scanned),
            mock.patch.object(reconnect, "known_keys", return_value={}),
        ):
            with self.assertRaisesRegex(reconnect.ReconnectError, "explicit approval"):
                reconnect.inspect_endpoint(
                    host="example.test",
                    port=31001,
                    prior_port=31000,
                    known_hosts=Path("known_hosts"),
                    trust_new=False,
                )

    def test_matching_prior_host_key_can_move_to_a_new_port(self):
        scanned = {"ssh-ed25519": base64.b64encode(b"same-key").decode("ascii")}

        def fake_known(_path, _host, port):
            return {} if port == 31001 else scanned

        with (
            mock.patch.object(reconnect, "scan_host_keys", return_value=scanned),
            mock.patch.object(reconnect, "known_keys", side_effect=fake_known),
        ):
            fingerprints, remove_current, accept_new = reconnect.inspect_endpoint(
                host="example.test",
                port=31001,
                prior_port=31000,
                known_hosts=Path("known_hosts"),
                trust_new=False,
            )
        self.assertTrue(fingerprints[0].startswith("ssh-ed25519 SHA256:"))
        self.assertFalse(remove_current)
        self.assertTrue(accept_new)

    def test_persistent_codex_environment_is_strictly_validated(self):
        root = "/srv/users/example"
        output = (
            f"HOME={root}\n"
            f"CODEX_HOME={root}/.codex\n"
            f"CODEX={root}/.local/bin/codex\n"
            "codex-cli 0.152.1\n"
        )
        details = reconnect.verify_codex_environment(output, root)
        self.assertEqual(details["VERSION"], "codex-cli 0.152.1")
        with self.assertRaisesRegex(reconnect.ReconnectError, "persistent"):
            reconnect.verify_codex_environment(
                output.replace(f"HOME={root}", "HOME=/srv/shared"), root
            )

    def test_remote_root_rejects_traversal_and_shared_directories(self):
        reconnect.validate_remote_root("/srv/users/example.user")
        for unsafe in (
            "/home",
            "/srv/users",
            "/srv/users/example/..",
            "/srv/users/example user",
        ):
            with self.subTest(root=unsafe):
                with self.assertRaises(reconnect.ReconnectError):
                    reconnect.validate_remote_root(unsafe)

    def test_windows_private_key_acl_is_limited_to_current_account(self):
        calls = []
        key_path = Path("C:/Users/alice/.ssh/aica-admin.pem")

        def fake_run(arguments, **_kwargs):
            calls.append(arguments)
            stdout = "workstation\\alice\n" if arguments[0] == "whoami" else ""
            return subprocess.CompletedProcess(arguments, 0, stdout=stdout, stderr="")

        with (
            mock.patch.object(reconnect.os, "name", "nt"),
            mock.patch.object(reconnect.shutil, "which", return_value="available"),
            mock.patch.object(reconnect, "run", side_effect=fake_run),
        ):
            reconnect.secure_private_key(key_path)

        self.assertEqual(calls[0], ["whoami"])
        self.assertEqual(calls[1][-1], "/inheritance:r")
        self.assertEqual(calls[2][-2:], ["/grant:r", "workstation\\alice:F"])

    def test_local_profile_round_trip_is_device_local_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile_path = Path(temporary) / "aica-reconnect.json"
            expected = {
                "host": "example.test",
                "user": "remote-user",
                "root": "/srv/users/example",
                "lastPort": 31001,
            }
            reconnect.save_local_profile(profile_path, expected)
            self.assertEqual(reconnect.load_local_profile(profile_path), expected)

    def test_remote_helper_persists_and_restores_only_managed_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = (Path(temporary) / "users" / "example").resolve()
            bootstrap = root / "tools" / "bootstrap"
            bootstrap.mkdir(parents=True)
            entrypoint = bootstrap / "persistent_env.sh"
            entrypoint.write_text("#!/bin/sh\n", encoding="utf-8")
            entrypoint.chmod(0o700)
            codex = root / ".local" / "bin" / "codex"
            codex.parent.mkdir(parents=True)
            codex.write_text("#!/bin/sh\n", encoding="utf-8")

            authorized = Path(temporary) / "authorized_keys"
            admin = "ssh-ed25519 YWRtaW4= administrator"
            prefix = key_helper.managed_prefix(entrypoint)
            mac = f"{prefix} ssh-ed25519 bWFjLWtleQ== aica-mac"
            windows = f"{prefix} ssh-ed25519 d2luZG93cy1rZXk= aica-windows"
            authorized.write_text(f"{admin}\n{mac}\n", encoding="utf-8")

            first = subprocess.run(
                [
                    sys.executable,
                    str(KEY_HELPER_PATH),
                    "--root",
                    str(root),
                    "--authorized-keys",
                    str(authorized),
                    "--add-line-base64",
                    base64.b64encode(windows.encode("utf-8")).decode("ascii"),
                    "--environment-id",
                    "env_test",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            first_payload = json.loads(first.stdout)
            self.assertEqual(first_payload["registeredKeys"], 2)
            self.assertIn(admin, authorized.read_text(encoding="utf-8"))

            authorized.write_text(f"{admin}\n", encoding="utf-8")
            second = subprocess.run(
                [
                    sys.executable,
                    str(KEY_HELPER_PATH),
                    "--root",
                    str(root),
                    "--authorized-keys",
                    str(authorized),
                    "--environment-id",
                    "env_test",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            second_payload = json.loads(second.stdout)
            restored = authorized.read_text(encoding="utf-8")
            self.assertEqual(second_payload["restoredKeys"], 2)
            self.assertIn(admin, restored)
            self.assertIn(mac, restored)
            self.assertIn(windows, restored)

            # Comments are labels, not authorization semantics. Keep an
            # equivalently restricted key even when its device label changed.
            renamed_mac = mac.rsplit(" ", 1)[0] + " renamed-device"
            authorized.write_text(
                f"{admin}\n{renamed_mac}\n{windows}\n", encoding="utf-8"
            )
            renamed = subprocess.run(
                [
                    sys.executable,
                    str(KEY_HELPER_PATH),
                    "--root",
                    str(root),
                    "--authorized-keys",
                    str(authorized),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(json.loads(renamed.stdout)["restoredKeys"], 0)

            # The same registered identity without the forced-command options
            # must still fail closed.
            unrestricted_mac = "ssh-ed25519 bWFjLWtleQ== unrestricted"
            authorized.write_text(
                f"{admin}\n{unrestricted_mac}\n{windows}\n", encoding="utf-8"
            )
            unsafe = subprocess.run(
                [
                    sys.executable,
                    str(KEY_HELPER_PATH),
                    "--root",
                    str(root),
                    "--authorized-keys",
                    str(authorized),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(unsafe.returncode, 0)
            self.assertIn("unrestricted options", unsafe.stderr)

    def test_skill_contains_no_embedded_credentials_or_live_state(self):
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL.rglob("*")
            if path.is_file() and path.suffix in {".md", ".py", ".yaml"}
        )
        self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", text)
        self.assertNotIn("proxy." + "aica", text)
        self.assertNotIn("junwon" + ".ko", text)
        self.assertNotRegex(text, r"env_e_[0-9a-f]{16,}")
        self.assertNotRegex(text, r"ssh-ed25519 [A-Za-z0-9+/]{40,}={0,3}")


if __name__ == "__main__":
    unittest.main()
