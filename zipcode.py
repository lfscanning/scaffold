# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
import os
import shutil
import zipfile

import git

from datatypes import ProjectRepoType, Status

# Runner for GOTCODE in GITHUB and GITHUB_SHARED
def doZipRepoCodeForSubproject(cfg, prj, sp):
    # first, get path where code was collected
    sp_path = os.path.join(cfg._storepath, cfg._month, "code", prj._name, sp._name)
    ziporg_path = ""
    if sp._repotype == ProjectRepoType.GITHUB_SHARED:
        ziporg_path = os.path.join(sp_path, sp._name)
    elif sp._repotype == ProjectRepoType.GITHUB:
        ziporg_path = os.path.join(sp_path, sp._github_ziporg)

    # remove each repo's .git directory
    for repo in sp._repos:
        dotgit_path = os.path.join(ziporg_path, repo, ".git")
        shutil.rmtree(dotgit_path)

    # before zipping it all together, check and see whether it actually has any files
    if not sp._code_anyfiles:
        print(f"{prj._name}/{sp._name}: not zipping, no files found")
        # still advance state because we passed the zip stage
        sp._status = Status.ZIPPEDCODE
        return True

    # now zip it all together
    zf_path = os.path.join(sp_path, f"{ziporg_path}-{sp._code_pulled}.zip")
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
    sp._status = Status.ZIPPEDCODE
    sp._code_path = zf_path
    return True

# Runner for GOTCODE in GERRIT
def doZipRepoCodeForGerritSubproject(cfg, prj, sp):
    # first, get path where code was collected
    sp_path = os.path.join(cfg._storepath, cfg._month, "code", prj._name, sp._name)
    ziporg_path = os.path.join(sp_path, sp._name)

    # remove each repo's .git directory
    for repo in sp._repos:
        dashName = repo.replace("/", "-")
        dstFolder = os.path.join(ziporg_path, dashName)
        dotgit_path = os.path.join(dstFolder, ".git")
        shutil.rmtree(dotgit_path)

    # before zipping it all together, check and see whether it actually has any files
    if not sp._code_anyfiles:
        print(f"{prj._name}/{sp._name}: not zipping, no files found")
        # still advance state because we checked for code
        sp._status = Status.ZIPPEDCODE
        return True

    # now zip it all together
    zf_path = os.path.join(sp_path, f"{ziporg_path}-{sp._code_pulled}.zip")
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
    sp._status = Status.ZIPPEDCODE
    sp._code_path = zf_path
    return True
