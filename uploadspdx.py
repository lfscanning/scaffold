# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import zipfile
from subprocess import run, PIPE

from git import Repo

from .datatypes import Status

MAX_FILE_SIZE = 50 * 1000000 # Maximum file size to push to GitHub - 50MB
def doUploadSPDXForSubproject(cfg, prj, sp):
    srcFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
    srcFilename = f"{sp._name}-{sp._code_pulled}.spdx"
    if doUploadFileForSubproject(cfg, prj, sp, srcFolder, srcFilename):
        sp._status = Status.UPLOADEDSPDX
        return True
    else:
        return False

def doUploadFileForSubproject(cfg, prj, sp, srcFolder, srcFilename):
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
    srcAbs = os.path.join(srcFolder, srcFilename)
    needToZip = os.path.getsize(srcAbs) > MAX_FILE_SIZE
    dstRel = os.path.join(sp._name, cfg._month, srcFilename + ".zip") if needToZip else os.path.join(sp._name, cfg._month, srcFilename)
    dstAbs = os.path.join(repoPath, dstRel)

    # create directories if needed
    dstAbsDir = os.path.dirname(dstAbs)
    os.makedirs(dstAbsDir, mode=0o755, exist_ok=True)

    # copy or zip the file
    if needToZip:
        with zipfile.ZipFile(dstAbs, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(srcAbs, srcFilename)
    else:
        shutil.copyfile(srcAbs, dstAbs)

    # add it
    repo.index.add([dstRel])

    # commit it
    commitMsg = f"add SPDX file {srcFilename} for {sp._name} from {cfg._month}\n\nSigned-off-by: {cfg._spdx_github_signoff}"
    repo.index.commit(commitMsg)
    print(f"{prj._name}/{sp._name}: added and committed spdx {srcFilename} file at {dstRel}")

    # and push it
    if not origin.push():
        print(f"{prj._name}/{sp._name}: Failed to push to {cfg._spdx_github_org}/{repoName}.  Check the size of the upload and the git repository integrity.")
        return False
    else:
        print(f"{prj._name}/{sp._name}: pushed to {cfg._spdx_github_org}/{repoName}")
    del repo
    return True
