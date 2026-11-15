# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE

# If any of these exist next to a package.json, the project already has an NPM lock file
NPM_LOCKFILES = ("package-lock.json", "npm-shrinkwrap.json")


def find_npm_projects_without_lockfile(source_dir):
    """Return directories containing a package.json but no NPM lock file."""
    npm_dirs = []
    for (root, dirs, files) in os.walk(source_dir, topdown=True):
        if 'package.json' in files \
                and 'node_modules/' not in root \
                and 'node_modules' not in dirs \
                and not any(lockfile in files for lockfile in NPM_LOCKFILES):
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
    for npm_dir in find_npm_projects_without_lockfile(source_dir):
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
