#!/usr/bin/env python3
"""Install the research and management plugins; optionally migrate old installs."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = 'https://github.com/koguma00/codex-toolkit.git'
MARKETPLACE = 'junwon'
SKILLS = {
    'research': {'ai-paper-search', 'siit-presentation', 'eli5', 'handoff'},
    'management': {'aica-reconnect', 'harness-review'},
}
LEGACY = ('ai-paper-search@ai-paper-search', 'siit-presentation@siit-presentation',
          'research-toolkit-manager@research-codex', 'research@research-codex')


def run(args):
    result = subprocess.run(['codex', *args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Codex command failed')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def verify_install(result, name):
    root = Path(result['installedPath'])
    manifest = json.loads((root / '.codex-plugin/plugin.json').read_text())
    if manifest['name'] != name:
        raise RuntimeError('Unexpected installed plugin')
    actual = {p.parent.name for p in (root / 'skills').glob('*/SKILL.md')}
    if actual != SKILLS[name]:
        raise RuntimeError(f'Incomplete skill set: {sorted(actual)}')
    if name == 'research':
        mcp = json.loads((root / '.mcp.json').read_text())
        if 'arxiv' not in mcp.get('mcpServers', {}):
            raise RuntimeError('Missing arXiv MCP connection')
        required = ('src/ai_paper_search/cli.py', 'skills/siit-presentation/assets/siit-reference-template.pptx')
    else:
        required = ('skills/aica-reconnect/scripts/aica_reconnect.py',)
    for path in required:
        if not (root / path).is_file():
            raise RuntimeError(f'Missing installed resource: {path}')
    return manifest['version']


def migrate(home):
    installed = run(['plugin', 'list', '--json'])
    ids = {p['pluginId'] for p in installed.get('installed', []) if p.get('installed', True)}
    for plugin in LEGACY:
        if plugin in ids:
            run(['plugin', 'remove', plugin, '--json'])
            print(f'Removed former plugin: {plugin}')
    marketplaces = run(['plugin', 'marketplace', 'list', '--json']).get('marketplaces', [])
    old = next((item for item in marketplaces if item['name'] == 'research-codex'), None)
    if old and old.get('marketplaceSource', {}).get('source', '').removesuffix('.git') in {
        REPOSITORY.removesuffix('.git'),
        'https://github.com/koguma00/codex-toolkit-research',
    }:
        run(['plugin', 'marketplace', 'remove', 'research-codex', '--json'])
        print('Removed former marketplace: research-codex')
    backup = home / 'research-plugin-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for name in ('eli5', 'handoff'):
        path = home / 'skills' / name
        if not path.exists():
            continue
        marker = path / '.research-toolkit-source.json'
        try:
            managed = json.loads(marker.read_text()).get('managed_by') == 'research-codex-toolkit'
        except (OSError, ValueError):
            managed = False
        if not managed or path.is_symlink():
            print(f'Preserved unmanaged skill; review duplicate manually: {path}')
            continue
        backup.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(backup / name))
        print(f'Backed up former standalone skill: {backup / name}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--migrate-legacy', action='store_true',
                        help='After both installs are verified, remove former plugins and back up toolkit-owned standalone skills')
    args = parser.parse_args(argv)
    if not shutil.which('codex'):
        raise RuntimeError('Install Codex CLI before running bootstrap')
    entries = run(['plugin', 'marketplace', 'list', '--json']).get('marketplaces', [])
    existing = next((x for x in entries if x['name'] == MARKETPLACE), None)
    if existing:
        source = existing.get('marketplaceSource', {}).get('source', '')
        if source.rstrip('/').removesuffix('.git') != REPOSITORY.removesuffix('.git'):
            raise RuntimeError('junwon points to another source; preserve it and resolve the naming conflict first')
        run(['plugin', 'marketplace', 'upgrade', MARKETPLACE, '--json'])
    else:
        run(['plugin', 'marketplace', 'add', REPOSITORY, '--ref', 'main', '--json'])
    installed = {}
    for name in SKILLS:
        plugin_id = f'{name}@{MARKETPLACE}'
        result = run(['plugin', 'add', plugin_id, '--json'])
        installed[plugin_id] = verify_install(result, name)
    if args.migrate_legacy:
        migrate(Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).expanduser())
    print('Installed ' + ', '.join(f'{plugin_id} {version}' for plugin_id, version in installed.items()) + '. Start a new Codex task.')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        raise SystemExit(1)
