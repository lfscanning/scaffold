# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE

# If any of these exist in a project's directory - or in a parent directory, where workspace/monorepo
# lock files live - the project is already locked and npm doesn't need to generate anything.
# Trivy reads all of these formats.
NPM_LOCKFILES = ("package-lock.json", "npm-shrinkwrap.json")
OTHER_LOCKFILES = ("yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb")
ALL_LOCKFILES = NPM_LOCKFILES + OTHER_LOCKFILES

# Yarn and pnpm dependency syntax that npm cannot resolve (npm fails with 'Unsupported URL Type "workspace:"')
UNSUPPORTED_NPM_PROTOCOLS = ('"workspace:', '"catalog:')


def _is_locked_by_ancestor(directory, source_dir, locked_dirs):
    """True if directory, or any parent up to source_dir, has a lock file."""
    source_dir = os.path.normpath(source_dir)
    current = os.path.normpath(directory)
    while True:
        if current in locked_dirs:
            return True
        if current == source_dir:
            return False
        parent = os.path.dirname(current)
        if parent == current:  # reached the filesystem root
            return False
        current = parent


def _uses_unsupported_protocol(package_json_path):
    try:
        with open(package_json_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except OSError:
        return False
    return any(protocol in content for protocol in UNSUPPORTED_NPM_PROTOCOLS)


def find_npm_projects_without_lockfile(source_dir, log=print):
    """
    Return directories containing a package.json that npm can lock and that have no lock file.
    A project is skipped if a lock file exists in its directory or in any parent directory
    (workspace members are covered by the lock file at the workspace root), or if it uses
    Yarn/pnpm-only dependency syntax such as "workspace:*" that npm can't process.
    """
    npm_dirs = []
    locked_dirs = set()
    for (root, dirs, files) in os.walk(source_dir, topdown=True):
        if any(lockfile in files for lockfile in ALL_LOCKFILES):
            locked_dirs.add(os.path.normpath(root))
        if 'package.json' in files \
                and 'node_modules/' not in root \
                and 'node_modules' not in dirs \
                and not _is_locked_by_ancestor(root, source_dir, locked_dirs):
            if _uses_unsupported_protocol(os.path.join(root, 'package.json')):
                log(f"Skipping NPM lock file generation for {root}: package.json uses Yarn/pnpm workspace syntax that npm can't resolve and no Yarn/pnpm lock file was found")
            else:
                npm_dirs.append(root)
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
        if '.git' in dirs:
            dirs.remove('.git')
    return npm_dirs


def generate_npm_lockfiles(source_dir, npm_exe, cache_dir, log=print):
    """
    Create package-lock.json for NPM projects that don't have a lock file so that Trivy can
    see their resolved dependencies. Only the lock file is produced: nothing is installed into
    node_modules and no package scripts are run. Failures are reported (including npm's
    stderr) but never stop the run.

    Returns the number of projects for which lock file generation failed.
    """
    failed = 0
    for npm_dir in find_npm_projects_without_lockfile(source_dir, log=log):
        cmd = [npm_exe, "install",
               "--package-lock-only",
               "--ignore-scripts",
               "--omit=dev",
               "--no-audit",
               "--no-fund",
               "--cache", cache_dir]
        cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd=npm_dir)
        if cp.returncode != 0:
            failed += 1
            log(f"""NPM lock file generation failed for {npm_dir} with exit code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        elif not any(os.path.exists(os.path.join(npm_dir, name)) for name in NPM_LOCKFILES):
            failed += 1
            log(f"WARNING: NPM lock file generation succeeded for {npm_dir} but produced no lock file")
    return failed
