# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
import os
import shutil
import zipfile

import git

from config import saveConfig
from datatypes import ProjectRepoType, Status
from github import getGithubRepoList

def doNextThing(scaffold_home, cfg):
    for prj in cfg._projects.values():
        retval = True
        while retval:
            retval = doNextThingForProject(scaffold_home, cfg, prj)

# Tries to do the next thing for this project. Returns True if
# accomplished something (meaning that we could call this again
# and possibly do the next-next thing), or False if accomplished
# nothing (meaning that we probably need to intervene).
def doNextThingForProject(scaffold_home, cfg, prj):
    # if GitHub project, go to subprojects
    if prj._repotype == ProjectRepoType.GITHUB:
        did_something = False
        for sp in prj._subprojects.values():
            retval = True
            while retval:
                retval = doNextThingForSubproject(scaffold_home, cfg, prj, sp)
                saveConfig(scaffold_home, cfg)
                if retval:
                    did_something = True
        return did_something

    # if GITHUB_SHARED project, check state to decide when to go to subprojects
    elif prj._repotype == ProjectRepoType.GITHUB_SHARED:
        did_something = False
        retval_prj = True
        while retval_prj:
            if prj._status == Status.START:
                # get repo listing at project level and see if we're good
                retval_prj = doRepoListingForProject(cfg, prj)
                saveConfig(scaffold_home, cfg)
                if retval_prj:
                    did_something = True
            else:
                for sp in prj._subprojects.values():
                    retval = True
                    while retval:
                        retval = doNextThingForSubproject(scaffold_home, cfg, prj, sp)
                        saveConfig(scaffold_home, cfg)
                        if retval:
                            did_something = True
        return did_something

    else:
        # or if Gerrit project, do everything here
        status = prj._status
        if status == Status.START:
            # get repo listing and see if we're good
            # FIXME figure out handling this for Gerrit
            #return doRepoListingForProject(prj)
            return False

        else:
            print(f"Invalid status for {prj._name}: {prj._status}")
            return False

# Tries to do the next thing for this subproject. Returns True if
# accomplished something (meaning that we could call this again
# and possibly do the next-next thing), or False if accomplished
# nothing (meaning that we probably need to intervene).
def doNextThingForSubproject(scaffold_home, cfg, prj, sp):
    status = sp._status
    if status == Status.START:
        # get repo listing and see if we're good
        return doRepoListingForSubproject(cfg, prj, sp)
    elif status == Status.GOTLISTING:
        # get code and see if we're good
        return doGetRepoCodeForSubproject(cfg, prj, sp)

    else:
        print(f"Invalid status for {sp._name}: {sp._status}")
        return False


# Runner for START in GitHub
def doRepoListingForSubproject(cfg, prj, sp):
    allrepos = getGithubRepoList(sp._github_org)

    # first, figure out what repos need to be added
    for r in allrepos:
        if r not in sp._repos and r not in sp._github_repos_ignore and r not in sp._github_repos_pending:
            sp._github_repos_pending.append(r)
            print(f"{prj._name}/{sp._name}: new pending repo: {r}")

    # then, figure out what repos need to be removed
    repos_to_remove = []
    for r in sp._repos:
        if r not in allrepos:
            repos_to_remove.append(r)
    for r in repos_to_remove:
        sp._repos.remove(r)
        print(f"{prj._name}/{sp._name}: removed {r} from repos")

    repos_ignore_to_remove = []
    for r in sp._github_repos_ignore:
        if r not in allrepos:
            repos_ignore_to_remove.append(r)
    for r in repos_ignore_to_remove:
        sp._github_repos_ignore.remove(r)
        print(f"{prj._name}/{sp._name}: removed {r} from repos-ignore")

    # finally, throw a "fail" if any new repos are pending
    if len(sp._github_repos_pending) > 0:
        print(f"{prj._name}/{sp._name}: stopped, need to assign repos-pending")
        return False
    else:
        # success - advance state
        sp._status = Status.GOTLISTING
        return True

# Runner for START in GITHUB-SHARED
def doRepoListingForProject(cfg, prj):
    if prj._repotype == ProjectRepoType.GITHUB_SHARED:
        # collect all configured repos, and what subprojects they're in
        allcfgrepos = {}
        for sp_name, sp in prj._subprojects.items():
            for r in sp._repos:
                allcfgrepos[r] = sp_name

        # collect all real repos currently on GitHub
        allrealrepos = getGithubRepoList(prj._github_shared_org)

        # first, figure out what repos need to be added
        for r in allrealrepos:
            config_sp = allcfgrepos.get(r, "")
            if config_sp == "" and r not in prj._github_shared_repos_ignore and r not in prj._github_shared_repos_pending:
                prj._github_shared_repos_pending.append(r)
                print(f"{prj._name}: new pending repo: {r}")

        # then, figure out what repos need to be removed
        for sp_name, sp in prj._subprojects.items():
            repos_to_remove = []
            for r in sp._repos:
                if r not in allrealrepos:
                    repos_to_remove.append(r)
            for r in repos_to_remove:
                sp._repos.remove(r)
                print(f"{prj._name}/{sp._name}: removed {r} from repos")

        repos_ignore_to_remove = []
        for r in prj._github_shared_repos_ignore:
            if r not in allrealrepos:
                repos_ignore_to_remove.append(r)
        for r in repos_ignore_to_remove:
            prj._github_shared_repos_ignore.remove(r)
            print(f"{prj._name}: removed {r} from repos-ignore")

        # finally, throw a "fail" if any new repos are pending
        if len(prj._github_shared_repos_pending) > 0:
            print(f"{prj._name}: stopped, need to assign repos-pending")
            return False
        else:
            # success - advance state
            prj._status = Status.GOTLISTING
            for _, sp in prj._subprojects.items():
                sp._status = Status.GOTLISTING
            return True

# Runner for GOTLISTING in GITHUB and GITHUB_SHARED
def doGetRepoCodeForSubproject(cfg, prj, sp):
    # first, get path and make directory (if doesn't exist) for collecting code
    sp_path = os.path.join(cfg._storepath, cfg._month, "code", prj._name, sp._name)
    org = ""
    ziporg_path = ""
    if sp._repotype == ProjectRepoType.GITHUB_SHARED:
        org = prj._github_shared_org
        ziporg_path = os.path.join(sp_path, sp._name)
    elif sp._repotype == ProjectRepoType.GITHUB:
        org = sp._github_org
        ziporg_path = os.path.join(sp_path, sp._github_ziporg)
    # clear contents if it's already there
    if os.path.exists(ziporg_path):
        shutil.rmtree(ziporg_path)
    # and create it if it isn't
    if not os.path.exists(ziporg_path):
        os.makedirs(ziporg_path)

    # clone each repo and remove its .git directory
    for repo in sp._repos:
        git_url = f"git@github.com:{org}/{repo}.git"
        print(f"{prj._name}/{sp._name}: cloning {git_url}")
        git.Git(ziporg_path).clone(git_url)
        dotgit_path = os.path.join(ziporg_path, repo, ".git")
        shutil.rmtree(dotgit_path)

    # now zip it all together
    today = datetime.today().strftime("%Y-%m-%d")
    zf_path = os.path.join(sp_path, f"{ziporg_path}-{today}.zip")
    print(f"{prj._name}/{sp._name}: zipping into {zf_path}")
    if os.path.exists(zf_path):
        os.remove(zf_path)
    zf = zipfile.ZipFile(zf_path, 'w', compression=zipfile.ZIP_DEFLATED)
    for root, _, files in os.walk(ziporg_path):
        for f in files:
            fpath = os.path.join(root, f)
            rpath = os.path.relpath(fpath, ziporg_path)
            if not os.path.islink(fpath):
                zf.write(fpath, arcname=rpath)
    zf.close()

    # and finally, remove the original unzipped directory
    shutil.rmtree(ziporg_path)

    # success - advance state
    sp._status = Status.GOTCODE
    return True
