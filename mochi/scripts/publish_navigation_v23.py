"""Publish explicit Mochi paths without touching the active Git index."""
import argparse
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--message', required=True)
parser.add_argument('--push', action='store_true')
parser.add_argument('paths', nargs='+')
args = parser.parse_args()
assert all(p.startswith('mochi/') and not any(s in p for s in ['.cache/', '.env', 'private-checkpoint']) for p in args.paths)
root = Path(__file__).resolve().parents[2]
branch = 'mochi-navigation-v23'
head_path = Path(subprocess.check_output(['git', 'rev-parse', '--git-path', 'HEAD'], cwd=root, text=True).strip())
if not head_path.is_absolute():
    head_path = root / head_path
head = head_path.read_bytes()
normal_index = subprocess.check_output(['git', 'ls-files', '-s'], cwd=root)
(root / 'mochi/.cache/navigation-v23').mkdir(parents=True, exist_ok=True)
env = {**os.environ, 'GIT_INDEX_FILE': str(root / 'mochi/.cache/navigation-v23/delivery-index')}


def git(*arguments):
    return subprocess.check_output(['git', *arguments], cwd=root, env=env, text=True).strip()


try:
    parent = git('rev-parse', '--verify', 'refs/heads/' + branch)
    old = parent
except subprocess.CalledProcessError:
    parent = git('rev-parse', '--verify', 'refs/heads/mochi-visual-motion-v22')
    old = '0' * 40
git('read-tree', parent)
git('add', '--', *args.paths)
git('diff', '--cached', '--check', parent)
print(git('diff', '--cached', '--stat', parent), flush=True)
assert git('diff', '--cached', '--name-only', parent), 'No new delivery changes'
for path in git('diff', '--cached', '--name-only', parent).splitlines():
    assert path.startswith('mochi/') and not path.endswith('.pickle')
author = git('show', '-s', '--format=%an%n%ae', parent).splitlines()
for role in ['AUTHOR', 'COMMITTER']:
    env['GIT_' + role + '_NAME'], env['GIT_' + role + '_EMAIL'] = author
commit = subprocess.check_output(['git', 'commit-tree', git('write-tree'), '-p', parent],
    cwd=root, env=env, text=True, input=args.message + '\n').strip()
git('update-ref', 'refs/heads/' + branch, commit, old)
assert head_path.read_bytes() == head
assert subprocess.check_output(['git', 'ls-files', '-s'], cwd=root) == normal_index
print(commit, flush=True)
if args.push:
    print(git('push', 'origin', branch), flush=True)
