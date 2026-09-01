import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "research-toolkit-manager"
LOCK_PATH = PLUGIN / "registry" / "plugins.lock.json"


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    def test_manager_version(self):
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], "0.3.1")

    def test_first_party_repository_names_start_with_codex(self):
        owned = {
            "ai-paper-search@ai-paper-search",
            "siit-presentation@siit-presentation",
        }
        by_id = {
            item["plugin_id"]: item for item in self.lock["managed_plugins"]
        }
        self.assertTrue(owned <= by_id.keys())
        for plugin_id in owned:
            repository = by_id[plugin_id]["repository"]
            name = repository.removesuffix(".git").rsplit("/", 1)[-1]
            self.assertTrue(name.startswith("codex-"), repository)
            self.assertEqual(len(by_id[plugin_id]["commit"]), 40)

    def test_presentation_is_managed_as_external_plugin(self):
        self.assertFalse(
            (PLUGIN / "skills" / "ppt-making-siit").exists()
        )
        entries = [
            item for item in self.lock["managed_plugins"]
            if item["plugin_id"] == "siit-presentation@siit-presentation"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["version"], "0.1.0")


if __name__ == "__main__":
    unittest.main()
