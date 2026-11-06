"""Integration tests use real Git repositories; no GitHub credentials or network."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which('git')
BASH = shutil.which('bash')


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='static-export-tests-')
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name).resolve()
        self.workspace = self.base / 'workspace with spaces'
        self.workspace.mkdir()
        self.project = self.workspace / 'my app'
        shutil.copytree(ROOT / 'sample-site', self.project, ignore=shutil.ignore_patterns('build', 'node_modules'))
        self.build = self.project / 'build'
        self.build.mkdir()
        (self.build / 'index.html').write_text('first deployment\n')
        (self.build / '.nojekyll').touch()
        self.remote = self.base / 'destination.git'
        self.run_git('init', '--bare', '--initial-branch=main', str(self.remote))
        self.run_git('init', '--initial-branch=main', str(self.workspace))
        self.output = self.base / 'output'
        self.output.touch()
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.log = self.base / 'git-commands.jsonl'
        wrapper = self.bin / 'git'
        wrapper.write_text('''#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
with open(os.environ['TEST_GIT_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if args and args[0] in ('ls-remote', 'fetch', 'push'):
    if os.environ.get('TEST_AUTH_FAIL') == 'true':
        print('fatal: Authentication failed', file=sys.stderr)
        sys.exit(128)
    askpass = os.environ['GIT_ASKPASS']
    username = subprocess.check_output([askpass, 'Username for HTTPS:'], text=True).strip()
    password = subprocess.check_output([askpass, 'Password for HTTPS:'], text=True).strip()
    if username != 'x-access-token' or password != os.environ['TEST_EXPECTED_TOKEN']:
        print('fatal: Wrong credentials', file=sys.stderr)
        sys.exit(128)
if args and args[0] == 'push' and os.environ.get('TEST_RACE') == 'true':
    git = os.environ['TEST_REAL_GIT']
    remote = os.environ['TEST_REMOTE']
    ref = 'refs/heads/build'
    parent = subprocess.check_output([git, '--git-dir', remote, 'rev-parse', ref], text=True).strip()
    tree = subprocess.check_output([git, '--git-dir', remote, 'rev-parse', parent + '^{tree}'], text=True).strip()
    commit = subprocess.check_output([git, '--git-dir', remote, 'commit-tree', tree, '-p', parent, '-m', 'Concurrent deployment'], text=True).strip()
    subprocess.check_call([git, '--git-dir', remote, 'update-ref', ref, commit])
rewrite = 'url.file://' + os.environ['TEST_REMOTE'] + '.insteadOf=https://github.com/owner/site.git'
os.execv(os.environ['TEST_REAL_GIT'], [os.environ['TEST_REAL_GIT'], '-c', rewrite] + args)
''')
        wrapper.chmod(0o755)
        self.env = {
            **os.environ,
            'PATH': str(self.bin) + os.pathsep + os.environ['PATH'],
            'GITHUB_WORKSPACE': str(self.workspace),
            'GITHUB_OUTPUT': str(self.output),
            'GITHUB_REPOSITORY': 'owner/site',
            'GITHUB_REF': 'refs/heads/main',
            'GITHUB_SERVER_URL': 'https://github.com',
            'ACTION_DEFAULT_BRANCH': 'main',
            'RUNNER_OS': 'Linux',
            'RUNNER_TEMP': str(self.base),
            'INPUT_PROJECT_DIR': 'my app',
            'ACTION_PROJECT_DIR': str(self.project),
            'ACTION_BUILD_DIR': str(self.build),
            'ACTION_BRANCH': 'build',
            'ACTION_REPOSITORY': 'owner/site',
            'ACTION_SERVER_URL': 'https://github.com',
            'ACTION_TOKEN': 'test-automatic-token',
            'TEST_EXPECTED_TOKEN': 'test-automatic-token',
            'TEST_GIT_LOG': str(self.log),
            'TEST_REAL_GIT': GIT,
            'TEST_REMOTE': str(self.remote),
            'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_AUTHOR_NAME': 'Test',
            'GIT_AUTHOR_EMAIL': 'test@example.invalid',
            'GIT_COMMITTER_NAME': 'Test',
            'GIT_COMMITTER_EMAIL': 'test@example.invalid',
            'npm_config_cache': str(self.base / 'npm-cache'),
            'npm_config_offline': 'true',
            'npm_config_audit': 'false',
            'npm_config_fund': 'false',
        }
        for key in ('TOKEN', 'PROJECT_DIR', 'BUILD_DIR', 'BUILD_BRANCH', 'TARGET_REPOSITORY', 'GITHUB_HOSTNAME'):
            self.env.pop(key, None)

    def run_git(self, *args):
        return subprocess.check_output([GIT, *args], text=True, stderr=subprocess.PIPE).strip()

    def run_script(self, script, success=True, **env):
        self.output.write_text('')
        result = subprocess.run([BASH, str(ROOT / script)], env={**self.env, **env}, text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result, dict(line.split('=', 1) for line in self.output.read_text().splitlines())

    def remote_git(self, *args):
        return self.run_git('--git-dir', str(self.remote), *args)

    def test_new_branch_publishes_hidden_files_without_checkout_credentials(self):
        _, output = self.run_script('entrypoint.sh')
        self.assertEqual(output['changed'], 'true')
        self.assertEqual(self.remote_git('show', 'build:index.html'), 'first deployment')
        self.assertIn('.nojekyll', self.remote_git('ls-tree', '--name-only', 'build'))
        self.assertEqual(output['commit'], self.remote_git('rev-parse', 'build'))
        commands = self.log.read_text()
        self.assertNotIn('test-automatic-token', commands)
        self.assertIn('https://github.com/owner/site.git', commands)
        self.assertEqual(list(self.base.glob('static-build-export.*')), [])

    def test_updated_output_preserves_history_and_removes_old_files(self):
        (self.build / 'old.txt').write_text('old')
        _, first = self.run_script('entrypoint.sh')
        (self.build / 'old.txt').unlink()
        (self.build / 'index.html').write_text('second deployment')
        _, second = self.run_script('entrypoint.sh')
        self.assertEqual(self.remote_git('rev-parse', 'build^'), first['commit'])
        self.assertEqual(second['changed'], 'true')
        self.assertNotIn('old.txt', self.remote_git('ls-tree', '--name-only', 'build'))

    def test_unchanged_output_skips_commit_and_push(self):
        _, first = self.run_script('entrypoint.sh')
        self.log.write_text('')
        _, second = self.run_script('entrypoint.sh')
        self.assertEqual(second, {'commit': first['commit'], 'changed': 'false'})
        self.assertFalse(any(json.loads(line)[0] == 'push' for line in self.log.read_text().splitlines()))

    def test_replace_history_is_explicit_and_unchanged_snapshots_are_skipped(self):
        _, first = self.run_script('entrypoint.sh')
        (self.build / 'index.html').write_text('snapshot')
        _, second = self.run_script('entrypoint.sh', ACTION_HISTORY='replace')
        self.assertNotEqual(first['commit'], second['commit'])
        self.assertEqual(self.remote_git('rev-list', '--count', 'build'), '1')
        _, third = self.run_script('entrypoint.sh', ACTION_HISTORY='replace')
        self.assertEqual(third['changed'], 'false')

    def test_concurrent_push_is_rejected_in_both_history_modes(self):
        self.run_script('entrypoint.sh')
        for mode in ('preserve', 'replace'):
            with self.subTest(mode=mode):
                (self.build / 'index.html').write_text(mode)
                self.run_script('entrypoint.sh', success=False, ACTION_HISTORY=mode, TEST_RACE='true')
                self.assertEqual(self.remote_git('log', '-1', '--format=%s', 'build'), 'Concurrent deployment')

    def test_legacy_token_override(self):
        self.run_script('entrypoint.sh', TOKEN='legacy-token', TEST_EXPECTED_TOKEN='legacy-token')

    def test_wrong_credentials_do_not_publish(self):
        self.run_script('entrypoint.sh', success=False, ACTION_TOKEN='wrong-token')
        self.assertEqual(self.remote_git('for-each-ref', '--format=%(refname)'), '')

    def test_authentication_failure_stops_without_a_deployment(self):
        _, output = self.run_script('entrypoint.sh', success=False, TEST_AUTH_FAIL='true')
        self.assertEqual(output, {})
        self.assertEqual(self.remote_git('for-each-ref', '--format=%(refname)'), '')
        self.assertEqual(list(self.base.glob('static-build-export.*')), [])

    def test_missing_credentials_stop_before_git_access(self):
        self.run_script('entrypoint.sh', success=False, ACTION_TOKEN='')
        self.assertFalse(self.log.exists())

    def test_invalid_build_directories_are_rejected(self):
        empty = self.project / 'empty'
        empty.mkdir()
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'index.html').write_text('outside')
        for directory in (self.project / 'missing', empty, self.workspace, self.project, outside):
            with self.subTest(directory=directory):
                self.run_script('entrypoint.sh', success=False, ACTION_BUILD_DIR=str(directory))
        self.assertFalse(self.log.exists())

    def test_git_metadata_and_symlinks_in_output_are_rejected(self):
        metadata = self.build / '.git'
        metadata.write_text('gitdir: elsewhere')
        self.run_script('entrypoint.sh', success=False)
        metadata.unlink()
        (self.build / 'linked').symlink_to(self.project / 'package.json')
        self.run_script('entrypoint.sh', success=False)
        self.assertFalse(self.log.exists())

    def test_prepare_detects_npm_and_legacy_environment(self):
        _, output = self.run_script('scripts/prepare.sh', INPUT_PROJECT_DIR='', PROJECT_DIR='my app', BUILD_BRANCH='site-output')
        self.assertEqual(output['package-manager'], 'npm')
        self.assertEqual(output['branch'], 'site-output')
        self.assertEqual(output['project-dir'], str(self.project))
        self.assertEqual(output['lockfile'], str(self.project / 'package-lock.json'))

    def test_inputs_take_precedence_over_legacy_environment(self):
        _, output = self.run_script('scripts/prepare.sh', INPUT_BRANCH='new-output', BUILD_BRANCH='old-output')
        self.assertEqual(output['branch'], 'new-output')

    def test_default_triggering_and_checked_out_branches_are_protected(self):
        for env in ({'INPUT_BRANCH': 'main'}, {'INPUT_BRANCH': 'feature', 'GITHUB_REF': 'refs/heads/feature'},
                    {'INPUT_BRANCH': 'main', 'GITHUB_REF': 'refs/pull/1/merge', 'ACTION_DEFAULT_BRANCH': ''},
                    {'INPUT_BRANCH': 'main', 'INPUT_REPOSITORY': 'OWNER/SITE'}):
            with self.subTest(env=env):
                self.run_script('scripts/prepare.sh', success=False, **env)

    def test_invalid_configuration_is_rejected(self):
        invalid = [
            {'INPUT_BRANCH': 'bad branch'}, {'INPUT_BRANCH': '-bad'},
            {'INPUT_REPOSITORY': 'https://example.com/repo'},
            {'INPUT_REPOSITORY': '../site'}, {'INPUT_REPOSITORY': 'owner/..'},
            {'INPUT_SERVER_URL': 'http://github.com'},
            {'INPUT_SERVER_URL': 'https://secret@github.com'},
            {'INPUT_PROJECT_DIR': '..'}, {'INPUT_BUILD_DIR': '/tmp'},
            {'INPUT_BUILD_DIR': 'build\ninjected=value'},
            {'INPUT_SKIP_BUILD': 'yes'}, {'INPUT_HISTORY': 'force'},
            {'INPUT_PACKAGE_MANAGER': 'pnpm'}, {'RUNNER_OS': 'Windows'},
        ]
        for env in invalid:
            with self.subTest(env=env):
                self.run_script('scripts/prepare.sh', success=False, **env)

    def test_missing_and_ambiguous_lockfiles_are_rejected(self):
        lock = self.project / 'package-lock.json'
        lock.unlink()
        self.run_script('scripts/prepare.sh', success=False)
        lock.write_text('{}')
        (self.project / 'yarn.lock').touch()
        self.run_script('scripts/prepare.sh', success=False)
        self.run_script('scripts/prepare.sh', INPUT_PACKAGE_MANAGER='npm')

    def test_prebuilt_output_does_not_require_node_project_or_lockfile(self):
        (self.project / 'package.json').unlink()
        (self.project / 'package-lock.json').unlink()
        self.run_script('scripts/prepare.sh', INPUT_SKIP_BUILD='true')

    def test_yarn_classic_detection_and_modern_yarn_rejection(self):
        (self.project / 'package-lock.json').unlink()
        (self.project / 'yarn.lock').touch()
        yarn = self.bin / 'yarn'
        yarn.write_text('#!/bin/sh\necho 1.22.22\n')
        yarn.chmod(0o755)
        _, output = self.run_script('scripts/prepare.sh')
        self.assertEqual(output['package-manager'], 'yarn')
        self.assertEqual(output['lockfile'], str(self.project / 'yarn.lock'))
        yarn.write_text('#!/bin/sh\necho 4.0.0\n')
        self.run_script('scripts/prepare.sh', success=False)

    def test_symlinked_output_cannot_escape_the_workspace(self):
        outside = self.base / 'external-output'
        outside.mkdir()
        (outside / 'index.html').write_text('outside')
        linked = self.project / 'linked-output'
        linked.symlink_to(outside)
        self.run_script('entrypoint.sh', success=False, ACTION_BUILD_DIR=str(linked))

    def test_lockfile_mismatch_fails_installation_before_the_build(self):
        package = json.loads((self.project / 'package.json').read_text())
        package['dependencies'] = {'nonexistent-static-export-test-package': '1.0.0'}
        (self.project / 'package.json').write_text(json.dumps(package))
        self.run_script('scripts/build.sh', success=False, ACTION_PACKAGE_MANAGER='npm')
        self.assertEqual((self.build / 'index.html').read_text(), 'first deployment\n')

    def test_enterprise_server_defaults_and_legacy_host(self):
        _, output = self.run_script('scripts/prepare.sh', GITHUB_SERVER_URL='https://github.example.com')
        self.assertEqual(output['server-url'], 'https://github.example.com')
        _, output = self.run_script('scripts/prepare.sh', GITHUB_HOSTNAME='legacy.example.com')
        self.assertEqual(output['server-url'], 'https://legacy.example.com')

    def test_real_npm_install_and_build(self):
        self.run_script('scripts/build.sh', ACTION_PACKAGE_MANAGER='npm')
        self.assertIn('Static Build Export', (self.build / 'index.html').read_text())
        self.run_script('entrypoint.sh')
        self.assertIn('Static Build Export', self.remote_git('show', 'build:index.html'))

    def test_failed_build_stops_before_publication(self):
        package = json.loads((self.project / 'package.json').read_text())
        package['scripts']['build'] = 'node -e "process.exit(1)"'
        (self.project / 'package.json').write_text(json.dumps(package))
        self.run_script('scripts/build.sh', success=False, ACTION_PACKAGE_MANAGER='npm')
        self.assertEqual(self.remote_git('for-each-ref', '--format=%(refname)'), '')


if __name__ == '__main__':
    unittest.main()
