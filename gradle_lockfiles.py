#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

"""Find Gradle projects that are missing lock files and generate them.

A "project" is any directory under the scan root that contains a build.gradle
or build.gradle.kts. For each project without a gradle.lockfile, the script runs
Gradle from the owning build's root:

    ./gradlew :<project path>:dependencies --write-locks --init-script <temp>

(`dependencies` is a per-project task, so each project is targeted explicitly
with its project path.) With --buildscript it also generates
buildscript-gradle.lockfile using `buildEnvironment --write-locks`.

Gradle only writes lock files for configurations that have locking activated.
So that lock files are produced even when a build does not configure locking,
the script passes a temporary init script that activates dependency locking on
every configuration for that run only. The build files for the project are not modified, and
the build will keep ignoring the generated lock files until you enable locking
in it yourself (e.g. dependencyLocking { lockAllConfigurations() }).

Resolving dependencies can require the JDK a project's toolchain asks for. A
second temporary init script applies the Foojay toolchain resolver, so Gradle can
download a missing JDK into your Gradle user home (not the project). It is only
added when the build has no toolchain repository of its own. Pass
--no-toolchain-provisioning to turn this off. It needs network access to the
Gradle plugin portal (or Maven Central) and to the Foojay JDK service.

Limitations
- Project paths are derived from directory names (a/b -> :a:b). If settings.gradle
  remaps project directories, that mapping will be wrong for those projects.
- buildSrc/ is skipped during discovery because Gradle treats it as a special
  separate build.

Command line
    python gradle_lockfiles.py ~/code/myrepo
    python gradle_lockfiles.py . --dry-run          # report only, exit 1 if any missing
    python gradle_lockfiles.py . --buildscript --gradle-arg=--offline

From other Python code
    import gradle_lockfiles
    result = gradle_lockfiles.generate_lockfiles(Path("/some/dir"), log=print)
    if not result.ok: ...

NOTE: This file was generated from Claude.ai Sonnet 5.5 Medium based on prompts from @goneall,
reviewed and updated by @goneall
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

BUILD_FILES = ("build.gradle.kts", "build.gradle")
SETTINGS_FILES = ("settings.gradle.kts", "settings.gradle")
SKIP_DIRS = {".git", ".gradle", ".idea", ".svn", ".hg", "build", "node_modules", "out", "buildSrc"}

INIT_SCRIPT_PROJECT = """\
allprojects {
    configurations.all {
        resolutionStrategy.activateDependencyLocking()
    }
}
"""

INIT_SCRIPT_BUILDSCRIPT = """\
allprojects {
    buildscript.configurations.all {
        resolutionStrategy.activateDependencyLocking()
    }
}
"""

# Lets Gradle download missing JDKs (toolchains) without touching the build's own
# files. It applies the Foojay toolchain resolver to the settings, but only if the
# build has not already configured any toolchain repository of its own. The plugin
# class is looked up by name so a wrong class name fails with a clear message.
INIT_SCRIPT_TOOLCHAINS = """\
initscript {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
    dependencies {
        classpath 'org.gradle.toolchains:foojay-resolver:@FOOJAY_VERSION@'
    }
}

settingsEvaluated { settings ->
    settings.pluginManager.apply('jvm-toolchain-management')
    if (settings.toolchainManagement.jvm.javaRepositories.size() == 0) {
        def pluginClass = Class.forName(
            'org.gradle.toolchains.foojay.FoojayToolchainsConventionPlugin',
            true, getClass().classLoader)
        settings.pluginManager.apply(pluginClass)
    }
}
"""

DEFAULT_FOOJAY_VERSION = "1.0.0"


@dataclass
class Job:
    project: Path
    build_root: Path
    task: str
    lockfile: Path


@dataclass
class Result:
    projects: int = 0          # Gradle projects found
    already_present: int = 0   # lock files that already existed
    missing: int = 0           # lock files that were missing
    created: int = 0           # lock files generated
    no_lockfile: int = 0       # Gradle succeeded but wrote no file
    failed: int = 0            # Gradle runs that failed

    @property
    def ok(self) -> bool:
        """True when nothing is left missing because of a failure."""
        return self.failed == 0 and self.no_lockfile == 0


def find_projects(root: Path, excludes: Iterable[str] = ()) -> list[Path]:
    """Return every directory under root that has a Gradle build file."""
    excludes = list(excludes)
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not any(fnmatch.fnmatch(d, pat) for pat in excludes)
        )
        if any(name in filenames for name in BUILD_FILES):
            found.append(Path(dirpath))
    return found


def find_build_root(project: Path) -> Path:
    """Nearest directory (self or ancestor) with a settings file, else the project itself."""
    for d in (project, *project.parents):
        if any((d / s).is_file() for s in SETTINGS_FILES):
            return d
    return project


def find_gradle(build_root: Path, fallback: str | None = None) -> list[str] | None:
    """Prefer the project's wrapper (searching upward), then `fallback`, then `gradle` on PATH."""
    wrapper_name = "gradlew.bat" if os.name == "nt" else "gradlew"
    for d in (build_root, *build_root.parents):
        wrapper = d / wrapper_name
        if wrapper.is_file():
            if os.name != "nt" and not os.access(wrapper, os.X_OK):
                return ["sh", str(wrapper)]
            return [str(wrapper)]
    if fallback:
        return [str(fallback)]
    system = shutil.which("gradle")
    return [system] if system else None


def run_job(
    job: Job,
    gradle: list[str],
    init_scripts: list[Path],
    extra_args: list[str],
    timeout: int,
    env: Mapping[str, str] | None,
    log: Callable[[str], None],
) -> str:
    """Run one Gradle invocation. Returns 'ok', 'no-lockfile', or 'failed'."""
    cmd = [*gradle, job.task, "--write-locks"]
    for script in init_scripts:
        cmd += ["--init-script", str(script)]
    cmd += ["--console=plain", "--quiet", *extra_args]
    try:
        proc = subprocess.run(
            cmd, cwd=job.build_root, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, env=env,
        )
    except subprocess.TimeoutExpired:
        log(f"    FAILED: timed out after {timeout}s")
        return "failed"
    except OSError as exc:
        log(f"    FAILED: could not start Gradle: {exc}")
        return "failed"

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-15:]
        log(f"    FAILED (exit {proc.returncode}):")
        for line in tail:
            log(f"      {line}")
        return "failed"

    if not job.lockfile.exists():
        log(
            f"    WARNING: Gradle succeeded but {job.lockfile.name} was not created. "
            "The project may have no resolvable dependencies to lock, or the project "
            "path derived from its directory may not match settings.gradle."
        )
        return "no-lockfile"
    return "ok"


def generate_lockfiles(
    root: Path,
    *,
    dry_run: bool = False,
    buildscript: bool = False,
    excludes: Iterable[str] = (),
    timeout: int = 900,  # 15 minutes
    gradle_args: Iterable[str] = (),
    toolchain_provisioning: bool = True,
    foojay_version: str = DEFAULT_FOOJAY_VERSION,
    dependency_verification: str | None = None,
    gradle_exe: str | None = None,
    env: Mapping[str, str] | None = None,
    log: Callable[[str], None] = print,
) -> Result:
    """Generate every missing lock file under `root` and return what happened.

    gradle_exe  Gradle executable to use when a project has no gradlew.
    env         Extra environment variables for Gradle (e.g. GRADLE_USER_HOME).
    log         Called with each line of progress output.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    gradle_args = list(gradle_args)
    run_env = {**os.environ, **env} if env else None

    result = Result()
    projects = find_projects(root, excludes)
    result.projects = len(projects)
    if not projects:
        log(f"No build.gradle / build.gradle.kts files found under {root}")
        return result

    jobs: list[Job] = []
    for proj in projects:
        build_root = find_build_root(proj)
        prefix = "".join(f":{part}" for part in proj.relative_to(build_root).parts)
        wanted = [("gradle.lockfile", f"{prefix}:dependencies")]
        if buildscript:
            wanted.append(("buildscript-gradle.lockfile", f"{prefix}:buildEnvironment"))

        for lock_name, task in wanted:
            lockfile = proj / lock_name
            if lockfile.exists():
                result.already_present += 1
            else:
                jobs.append(Job(proj, build_root, task, lockfile))
    result.missing = len(jobs)

    log(f"Scanned {len(projects)} project(s) under {root}")
    log(f"  lock files already present: {result.already_present}")
    log(f"  missing lock files: {len(jobs)}")

    if not jobs:
        return result

    if dry_run:
        for job in jobs:
            log(f"    - {job.lockfile.relative_to(root)}  (would run {job.task} in {job.build_root})")
        return result

    gradle_cache: dict[Path, list[str] | None] = {}
    notified_verification: set[Path] = set()

    with tempfile.TemporaryDirectory(prefix="gradle-lock-init-") as tmp:
        init_script = Path(tmp) / "enable-locking.init.gradle"
        content = INIT_SCRIPT_PROJECT
        if buildscript:
            content += INIT_SCRIPT_BUILDSCRIPT
        init_script.write_text(content)
        init_scripts = [init_script]
        if toolchain_provisioning:
            toolchain_script = Path(tmp) / "toolchain-provisioning.init.gradle"
            toolchain_script.write_text(
                INIT_SCRIPT_TOOLCHAINS.replace("@FOOJAY_VERSION@", foojay_version)
            )
            init_scripts.append(toolchain_script)

        for i, job in enumerate(jobs, 1):
            rel = job.lockfile.relative_to(root)
            log(f"[{i}/{len(jobs)}] {rel}")
            if job.build_root not in gradle_cache:
                gradle_cache[job.build_root] = find_gradle(job.build_root, gradle_exe)
            gradle = gradle_cache[job.build_root]
            if gradle is None:
                log("    FAILED: no gradlew found in or above the build root, and no `gradle` on PATH")
                result.failed += 1
                continue

            job_args = list(gradle_args)
            mode = dependency_verification
            if (mode is None and toolchain_provisioning
                    and (job.build_root / "gradle" / "verification-metadata.xml").is_file()):
                mode = "lenient"
                if job.build_root not in notified_verification:
                    notified_verification.add(job.build_root)
                    log(
                        "    NOTE: this build uses dependency verification, which would reject the temporary "
                        "Foojay plugin.\n"
                        "          Using --dependency-verification=lenient for these runs (verification failures "
                        "are not enforced).\n"
                        "          Use --dependency-verification=strict to enforce it, or "
                        "--no-toolchain-provisioning with a locally installed JDK."
                    )
            if mode:
                job_args.append(f"--dependency-verification={mode}")

            log(f"    $ {' '.join(gradle)} {job.task} --write-locks  (in {job.build_root})")
            outcome = run_job(job, gradle, init_scripts, job_args, timeout, run_env, log)
            if outcome == "ok":
                result.created += 1
            elif outcome == "no-lockfile":
                result.no_lockfile += 1
            else:
                result.failed += 1

    log(
        f"Done: {result.created} created, {result.no_lockfile} produced no file, "
        f"{result.failed} failed"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate missing Gradle lock files under a directory.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("directory", nargs="?", default=".", help="directory to scan")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="only report missing lock files; exit 1 if any are missing")
    parser.add_argument("--buildscript", action="store_true",
                        help="also generate buildscript-gradle.lockfile (buildEnvironment --write-locks)")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="skip directories whose name matches this glob (repeatable)")
    parser.add_argument("--no-toolchain-provisioning", action="store_true",
                        help="don't add the Foojay resolver; Gradle will not auto-download missing JDKs")
    parser.add_argument("--dependency-verification", choices=("strict", "lenient", "off"), default=None,
                        help="Gradle dependency verification mode for the runs. Default: unchanged, except "
                             "'lenient' when toolchain provisioning is on and the build has "
                             "gradle/verification-metadata.xml (the temporary Foojay plugin isn't in it)")
    parser.add_argument("--foojay-version", default=DEFAULT_FOOJAY_VERSION, metavar="VERSION",
                        help="version of org.gradle.toolchains:foojay-resolver to use")
    parser.add_argument("--timeout", type=int, default=900, help="seconds allowed per Gradle run")
    parser.add_argument("--gradle-arg", action="append", default=[], metavar="ARG",
                        help="extra argument for Gradle, use '=' form: --gradle-arg=--offline (repeatable)")
    args = parser.parse_args(argv)

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    result = generate_lockfiles(
        root,
        dry_run=args.dry_run,
        buildscript=args.buildscript,
        excludes=args.exclude,
        timeout=args.timeout,
        gradle_args=args.gradle_arg,
        toolchain_provisioning=not args.no_toolchain_provisioning,
        foojay_version=args.foojay_version,
        dependency_verification=args.dependency_verification,
    )
    if args.dry_run:
        return 1 if result.missing else 0
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
