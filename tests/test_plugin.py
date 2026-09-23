import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'plugins/research'
MANAGEMENT = ROOT / 'plugins/management'
spec = importlib.util.spec_from_file_location('bootstrap', ROOT / 'bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)

class PluginTests(unittest.TestCase):
    def test_both_plugins_contain_their_skills_and_runtime(self):
        self.assertEqual(bootstrap.verify_install({'installedPath': str(RESEARCH)}, 'research'), '1.1.0')
        self.assertEqual(bootstrap.verify_install({'installedPath': str(MANAGEMENT)}, 'management'), '1.0.0')
        market = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual(market['name'], 'junwon')
        self.assertEqual([p['name'] for p in market['plugins']], ['research', 'management'])
        self.assertEqual([p['source']['path'] for p in market['plugins']],
                         ['./plugins/research', './plugins/management'])
        for name in ('eli5', 'handoff'):
            self.assertTrue((RESEARCH / 'skills' / name / 'LICENSE').is_file())

    def test_failed_install_never_removes_legacy(self):
        with patch.object(bootstrap.shutil, 'which', return_value='codex'), \
             patch.object(bootstrap, 'run', side_effect=[{'marketplaces': []}, {},
                      {'installedPath': str(RESEARCH)}, RuntimeError('install failed')]), \
             patch.object(bootstrap, 'migrate') as migrate:
            with self.assertRaises(RuntimeError):
                bootstrap.main(['--migrate-legacy'])
            migrate.assert_not_called()

    def test_incomplete_install_never_removes_legacy(self):
        with tempfile.TemporaryDirectory() as d, \
             patch.object(bootstrap.shutil, 'which', return_value='codex'), \
             patch.object(bootstrap, 'run', side_effect=[{'marketplaces': []}, {}, {'installedPath': d}]), \
             patch.object(bootstrap, 'migrate') as migrate:
            with self.assertRaises(OSError):
                bootstrap.main(['--migrate-legacy'])
            migrate.assert_not_called()

    def test_migration_preserves_unmanaged_and_backs_up_managed(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            for name in ('eli5', 'handoff'):
                path = home / 'skills' / name
                path.mkdir(parents=True)
                (path / 'SKILL.md').write_text('local content')
            (home / 'skills/eli5/.research-toolkit-source.json').write_text(json.dumps({'managed_by':'research-codex-toolkit'}))
            with patch.object(bootstrap, 'run', return_value={'installed': []}):
                bootstrap.migrate(home)
            self.assertEqual((home/'skills/handoff/SKILL.md').read_text(), 'local content')
            self.assertFalse((home/'skills/eli5').exists())
            backups=list((home/'research-plugin-backups').glob('*/eli5/SKILL.md'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), 'local content')

    def test_conflicting_marketplace_is_preserved(self):
        with patch.object(bootstrap.shutil, 'which', return_value='codex'), \
             patch.object(bootstrap, 'run', return_value={'marketplaces':[{'name':'junwon','marketplaceSource':{'source':'/different/repository'}}]}) as run:
            with self.assertRaises(RuntimeError):
                bootstrap.main([])
            self.assertEqual(run.call_count, 1)

if __name__ == '__main__': unittest.main()
