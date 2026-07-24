# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import zipfile

from git import Repo

from datatypes import Status
from uploadreport import doUploadSingleReportForSubproject

UPLOAD_SPDX_SUFFIX = "spdx-v2"
JSON_EXTENSION = "json"
SPDX_EXTENSION = "spdx"
UPLOAD_SPDX_V3_SUFFIX = "spdx-v3"
MERGED_SBOM_SUFFIX = "merged-spdx-v2"
MERGED_SBOM_V3_SUFFIX = "merged-spdx-v3"

SUFFIX_TO_ATTRIBUTE_MAP = {
    UPLOAD_SPDX_SUFFIX : "_web_sbom_spdxv2",
    UPLOAD_SPDX_V3_SUFFIX : "_web_sbom_spdxv3",
    MERGED_SBOM_SUFFIX : "_web_sbom_spdxv2_merged",
    MERGED_SBOM_V3_SUFFIX : "_web_sbom_spdxv3_merged"
}

MAX_FILE_SIZE = 50 * 1000000 # Maximum file size to push to GitHub - 50MB
def doUploadSPDXForSubproject(cfg, prj, sp):
    srcFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
    if doUploadFileForSubproject(cfg, prj, sp, srcFolder, "", "spdx"):
        sp._status = Status.UPLOADEDSPDX
        return True
    else:
        return False

# Upload a file into Git or Reports folder depending on reports_private config
# Zips large files if needed
def doUploadFileForSubproject(cfg, prj, sp, sourceFolder, suffix, extension):
    if sp._reports_private:
        return doCopyToReportsFolder(cfg, prj, sp, sourceFolder, suffix, extension)
    else:
        return doUploadToGitForSubproject(cfg, prj, sp, sourceFolder, suffix, extension)

def doCopyToReportsFolder(cfg, prj, sp, srcFolder, suffix, extension):
    srcFilename = f"{sp._name}-{sp._code_pulled}-{suffix}.{extension}" if suffix else f"{sp._name}-{sp._code_pulled}.{extension}"
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    if not os.path.exists(reportFolder):
        os.makedirs(reportFolder)
    sourcePath = os.path.join(srcFolder, srcFilename)
    needToZip = os.path.getsize(sourcePath) > MAX_FILE_SIZE
    reportPath = os.path.join(reportFolder, srcFilename + ".zip") if needToZip else os.path.join(reportFolder, srcFilename)
    # create report directory for project if it doesn't already exist
    # copy or zip the file
    if needToZip:
        with zipfile.ZipFile(reportPath, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(sourcePath, srcFilename)
    else:
        shutil.copy(sourcePath, reportPath)
    webUrl = doUploadSingleReportForSubproject(cfg, prj, sp, suffix, f"{extension}.zip" if needToZip else extension)
    if webUrl:
        if extension == SPDX_EXTENSION:
            sp._web_spdx = webUrl
            print(f"Web version of SPDX file {srcFilename} available at: {webUrl}")
            return True
        elif extension == JSON_EXTENSION:
            if not suffix in SUFFIX_TO_ATTRIBUTE_MAP:
                print(f"Unidentified SBOM file suffix {suffix}.  Could not upload report file.")
                return False
            setattr(sp, SUFFIX_TO_ATTRIBUTE_MAP[suffix], webUrl)
            print(f"Web version of SBOM file {srcFilename} available at: {webUrl}")
            return True
        else:
            print(f"Unidentified SBOM file extension {extension}.  Could not upload report file.")
            return False
    else:
        # Unable to upload teh file
        return False


def doUploadToGitForSubproject(cfg, prj, sp, srcFolder, suffix, extension):
    # get path to this project's local SPDX repo
    srcFilename = f"{sp._name}-{sp._code_pulled}-{suffix}.{extension}" if suffix else f"{sp._name}-{sp._code_pulled}.{extension}"
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
