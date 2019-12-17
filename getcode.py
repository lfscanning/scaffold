# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
import os
import shutil
import zipfile

import git

from datatypes import ProjectRepoType, Status

# Runner for GOTLISTING in GITHUB and GITHUB_SHARED
def doGetRepoCodeForSubproject(cfg, prj, sp):
    # first, get path and make directory (if doesn't exist) for collecting code
    today = datetime.today().strftime("%Y-%m-%d")
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
        # also record the top commit
        r = git.Repo(dotgit_path)
        cmts = list(r.iter_commits())
        if len(cmts) > 0:
            sp._code_repos[repo] = cmts[0].hexsha

    # before finishing, check and see whether it actually has any files
    anyfiles = False
    for _, _, files in os.walk(ziporg_path):
        if files:
            anyfiles = True
            break
    if not anyfiles:
        print(f"{prj._name}/{sp._name}: skipping, no files found")
        sp._code_anyfiles = False
        # still advance state because we checked for code
        sp._status = Status.GOTCODE
        sp._code_pulled = today
        return True

    # great, there are files, so keep going
    sp._code_anyfiles = True

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
        # also record the top commit
        dotgit_path = os.path.join(dstFolder, ".git")
        r = git.Repo(dotgit_path)
        if len(r.refs) > 0:
            cmts = list(r.iter_commits())
            if len(cmts) > 0:
                sp._code_repos[repo] = cmts[0].hexsha

    # before zipping it all together, check and see whether it actually has any files
    anyfiles = False
    for _, _, files in os.walk(ziporg_path):
        if files:
            anyfiles = True
            break
    if not anyfiles:
        print(f"{prj._name}/{sp._name}: skipping, no files found")
        sp._code_anyfiles = False
        # still advance state because we checked for code
        sp._status = Status.GOTCODE
        sp._code_pulled = today
        return True

    # great, there are files, so keep going
    sp._code_anyfiles = True

    # success - advance state
    sp._status = Status.GOTCODE
    sp._code_pulled = today
    return True
