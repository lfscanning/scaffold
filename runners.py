# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
import os
import shutil
import zipfile

import git

from config import saveConfig
from datatypes import ProjectRepoType, Status, Subproject
from github import getGithubRepoList
from gerrit import getGerritRepoDict

def doNextThing(scaffold_home, cfg, prj_only, sp_only):
    for prj in cfg._projects.values():
        if prj_only == "" or prj_only == prj._name:
            retval = True
            while retval:
                retval = doNextThingForProject(scaffold_home, cfg, prj, sp_only)

def updateProjectStatusToSubprojectMin(cfg, prj):
    minStatus = Status.MAX
    for sp in prj._subprojects.values():
        if sp._status.value < minStatus.value:
            minStatus = sp._status
    prj._status = minStatus

# Tries to do the next thing for this project. Returns True if
# accomplished something (meaning that we could call this again
# and possibly do the next-next thing), or False if accomplished
# nothing (meaning that we probably need to intervene).
def doNextThingForProject(scaffold_home, cfg, prj, sp_only):
    # if GitHub project, go to subprojects
    if prj._repotype == ProjectRepoType.GITHUB:
        did_something = False
        for sp in prj._subprojects.values():
            if sp_only == "" or sp_only == sp._name:
                retval = True
                while retval:
                    retval = doNextThingForSubproject(scaffold_home, cfg, prj, sp)
                    updateProjectStatusToSubprojectMin(cfg, prj)
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
                retval_sp_all = False
                for sp in prj._subprojects.values():
                    if sp_only == "" or sp_only == sp._name:
                        retval = True
                        while retval:
                            retval = doNextThingForSubproject(scaffold_home, cfg, prj, sp)
                            updateProjectStatusToSubprojectMin(cfg, prj)
                            saveConfig(scaffold_home, cfg)
                            if retval:
                                did_something = True
                                retval_sp_all = True
                if not retval_sp_all:
                    break
        return did_something

    elif prj._repotype == ProjectRepoType.GERRIT:
        did_something = False
        retval_prj = True
        while retval_prj:
            if prj._status == Status.START:
                # get repo listing at project level and see if we're good
                retval_prj = doRepoListingForGerritProject(cfg, prj)
                updateProjectStatusToSubprojectMin(cfg, prj)
                saveConfig(scaffold_home, cfg)
                if retval_prj:
                    did_something = True
            else:
                retval_sp_all = False
                for sp in prj._subprojects.values():
                    if sp_only == "" or sp_only == sp._name:
                        retval = True
                        while retval:
                            retval = doNextThingForGerritSubproject(scaffold_home, cfg, prj, sp)
                            updateProjectStatusToSubprojectMin(cfg, prj)
                            saveConfig(scaffold_home, cfg)
                            if retval:
                                did_something = True
                                retval_sp_all = True
                if not retval_sp_all:
                    break
        return did_something

    else:
        print(f"Invalid project repotype for {prj._name}: {prj._repotype}")
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


# Tries to do the next thing for this Gerrit subproject. Returns True if
# accomplished something (meaning that we could call this again and possibly do
# the next-next thing), or False if accomplished nothing (meaning that we
# probably need to intervene). Does not handle START case because that is
# handled at the project level.
def doNextThingForGerritSubproject(scaffold_home, cfg, prj, sp):
    status = sp._status
    if status == Status.GOTLISTING:
        # get code and see if we're good
        return doGetRepoCodeForGerritSubproject(cfg, prj, sp)

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

# Runner for START in GERRIT
def doRepoListingForGerritProject(cfg, prj):
    if prj._gerrit_subproject_config == "auto":
        doRepoListingForGerritAutoProject(cfg, prj)
    elif prj._gerrit_subproject_config == "one":
        doRepoListingForGerritOneProject(cfg, prj)
    elif prj._gerrit_subproject_config == "manual":
        print(f"{prj._name}: subproject-config value of 'manual' not yet implemented")
        return False
    else:
        print(f"{prj._name}: invalid subproject-config value: {prj._gerrit_subproject_config}")
        return False

# Runner for START in GERRIT where subproject-config is auto
def doRepoListingForGerritAutoProject(cfg, prj):
    # get the sorted dictionary of repos by top-level grouping, if any
    rd = getGerritRepoDict(prj._gerrit_apiurl)

    # now, figure out which repos to assign to which subprojects
    # and create subprojects where needed
    groupings_seen = []
    for grouping, repos in rd.items():
        if grouping not in prj._gerrit_repos_ignore:
            groupings_seen.append(grouping)
            sp = prj._subprojects.get(grouping, None)
            if sp == None:
                sp = Subproject()
                sp._name = grouping
                sp._repotype = ProjectRepoType.GERRIT
                sp._status = Status.START
                prj._subprojects[grouping] = sp
            # now, figure out which new repos in this grouping we need to add
            repos_seen = []
            repos_to_remove = []
            for repo in repos:
                repos_seen.append(repo)
                if repo not in sp._repos:
                    sp._repos.append(repo)
                    print(f"{prj._name}/{sp._name}: added {repo} to repos")
            # and which old repos we need to remove
            for repo in sp._repos:
                if repo not in repos_seen:
                    repos_to_remove.append(repo)
            for repo in repos_to_remove:
                sp._repos.remove(repo)
                print(f"{prj._name}/{sp._name}: removed {repo} from repos")

    # now, finally, figure out which old subprojects we need to remove
    subprojects_to_remove = []
    for sp_name in prj._subprojects.keys():
        if sp_name not in groupings_seen:
            subprojects_to_remove.append(sp_name)
    for sp_name in subprojects_to_remove:
        prj._subprojects.remove(sp_name)
        print(f"{prj._name}: removed subproject {sp_name}")

    # finally, update status for remaining subprojects
    for sp in prj._subprojects.values():
        sp._status = Status.GOTLISTING
    prj._status = Status.GOTLISTING

    return True

# Runner for START in GERRIT where subproject-config is one
def doRepoListingForGerritOneProject(cfg, prj):
    # check that there's only one subproject and that it has the right name
    if len(prj._subprojects) > 1:
        print(f"{prj._name}: subproject-config value is 'one' but more than one subproject exists")
        return False
    if len(prj._subprojects) == 1:
        # should only be one but we'll iterate to get the first one
        for sp_name in prj._subprojects.keys():
            if sp_name != prj._name:
                print(f"{prj._name}: subproject-config value is 'one' but subproject has different name from project: {sp_name}")
                return False
    # or if no subprojects, create new subproject for this gerrit org overall
    if len(prj._subprojects) == 0:
        sp = Subproject()
        sp._name = prj._name
        sp._repotype = ProjectRepoType.GERRIT
        sp._status = Status.START
        prj._subprojects[prj._name] = sp

    # get the sorted dictionary of repos by top-level grouping, if any
    rd = getGerritRepoDict(prj._gerrit_apiurl)

    # now, figure out which repos to add
    repos_seen = []
    sp = prj._subprojects.get(prj._name, None)
    if sp == None:
        print(f"{prj._name}: unable to get subproject {prj._name}")
        return False
    for grouping, repos in rd.items():
        if grouping not in prj._gerrit_repos_ignore:
            for repo in repos:
                repos_seen.append(repo)
                if repo not in sp._repos:
                    sp._repos.append(repo)
                    print(f"{prj._name}/{sp._name}: added {repo} to repos")
    # and which ones to remove
    repos_to_remove = []
    for repo in sp._repos:
        if repo not in repos_seen:
            repos_to_remove.append(repo)
    for repo in repos_to_remove:
        sp._repos.remove(repo)
        print(f"{prj._name}/{sp._name}: removed {repo} from repos")

    # finally, update status for remaining subprojects
    sp._status = Status.GOTLISTING
    prj._status = Status.GOTLISTING

    return True

# Runner for START in GERRIT where subproject-config is manual
def doRepoListingForGerritManualProject(cfg, prj):
    # not yet implemented; need to account for grouping vs. flat repo names
    # could have same repo names in different groupings
    return False

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
    sp._code_pulled = today
    return True

# Runner for GOTLISTING in GERRIT
def doGetRepoCodeForGerritSubproject(cfg, prj, sp):
    # first, get path and make directory (if doesn't exist) for collecting code
    today = datetime.today().strftime("%Y-%m-%d")
    sp_path = os.path.join(cfg._storepath, cfg._month, "code", prj._name, sp._name)
    ziporg_path = os.path.join(sp_path, sp._name)
    # clear contents if it's already there
    if os.path.exists(ziporg_path):
        shutil.rmtree(ziporg_path)
    # and create it if it isn't
    if not os.path.exists(ziporg_path):
        os.makedirs(ziporg_path)

    # clone each repo and remove its .git directory
    for repo in sp._repos:
        # parse repo name
        dashName = repo.replace("/", "-")
        dstFolder = os.path.join(ziporg_path, dashName)
        gitAddress = os.path.join(prj._gerrit_apiurl, repo)
        # get repo
        print(f"{prj._name}/{sp._name}: cloning {gitAddress}")
        git.Repo.clone_from(gitAddress, dstFolder)
        # remove .git/
        dotgit_path = os.path.join(dstFolder, ".git")
        shutil.rmtree(dotgit_path)

    # before zipping it all together, check and see whether it actually has any files
    for _, _, files in os.walk(dstFolder):
        if not files:
            print(f"{prj._name}/{sp._name}: skipping, no files found")
            sp._code_anyfiles = False
            # still advance state because we checked for code
            sp._status = Status.GOTCODE
            sp._code_pulled = today
            return True

    # great, there are files, so keep going
    sp._code_anyfiles = True

    # now zip it all together
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
    sp._code_pulled = today
    return True
