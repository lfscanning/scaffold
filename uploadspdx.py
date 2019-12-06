# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
import shutil

from git import Repo

from datatypes import Status

def doUploadSPDXForSubproject(cfg, prj, sp):
    # get path to this project's local SPDX repo
    repoName = f"spdx-{prj._name}"
    repoPath = os.path.join(cfg._storepath, "spdxrepos", repoName)

    if not os.path.exists(repoPath):
        print(f"{prj._name}/{sp._name}: local SPDX repo not found; create repo '{repoName}' on GitHub in org '{cfg._spdx_github_org}' and clone to {repoPath}")
        return False

    repo = Repo(repoPath)

    # check that the repo origin is correct
    # should only be one origin and should be correct org and name
    # FIXME note that we assume there is only one origin
    origin = repo.remote(name="origin")
    originUrl = ""
    for u in origin.urls:
        originUrl = u
        break
    expectedUrl = f"git@github.com:{cfg._spdx_github_org}/{repoName}.git"
    if expectedUrl != originUrl:
        print(f"{prj._name}/{sp._name}: for SPDX upload, expected origin remote to be {expectedUrl} but got {originUrl}; bailing")
        return False

    # figure out which file to copy to where
    srcFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
    srcFilename = f"{sp._name}-{sp._code_pulled}.spdx"
    srcAbs = os.path.join(srcFolder, srcFilename)
    dstRel = os.path.join(sp._name, cfg._month, srcFilename)
    dstAbs = os.path.join(repoPath, dstRel)

    # create directories if needed
    dstAbsDir = os.path.dirname(dstAbs)
    os.makedirs(dstAbsDir, mode=0o755)

    # copy the file
    shutil.copyfile(srcAbs, dstAbs)

    # add it
    repo.index.add([dstRel])

    # commit it
    commitMsg = f"add SPDX file for {sp._name} from {cfg._month} Fossology scan\n\nSigned-off-by: {cfg._spdx_github_signoff}"
    repo.index.commit(commitMsg)
    print(f"{prj._name}/{sp._name}: added and committed spdx file at {dstRel}")

    # and push it
    origin.push()
    print(f"{prj._name}/{sp._name}: pushed to {cfg._spdx_github_org}/{repoName}")

    # once we get here, the spdx file has been uploaded
    sp._status = Status.UPLOADEDSPDX
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
