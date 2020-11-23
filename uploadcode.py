# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from datatypes import Status, ProjectRepoType

from fossdriver.tasks import CreateFolder, Upload

def doUploadCodeForProject(cfg, fdServer, prj):
    # create top-level folder for project, if it doesn't already exist
    t = CreateFolder(fdServer, prj._name, "Software Repository")
    retval = t.run()
    if not retval:
        print(f"{prj._name}: Could not create folder {prj._name}")
        return False

    # create one project-level folder for this month, and
    # upload all code there
    dstFolder = f"{prj._name}-{cfg._month}"
    t = CreateFolder(fdServer, dstFolder, prj._name)
    retval = t.run()
    if not retval:
        print(f"{prj._name}: Could not create folder {dstFolder}")
        return False

    # and now cycle through each subproject and upload the code here
    for sp in prj._subprojects.values():
        # make sure the subproject has not already had its code uploaded
        if sp._status != Status.UPLOADEDWS:
            print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected UPLOADEDWS")
            continue
        zipPath = sp._code_path
        if zipPath == "":
            print(f"{prj._name}/{sp._name}: skipping, no path found for retrieved code")
            sp._status = Status.STOPPED
            continue
        print(f"{prj._name}/{sp._name}: uploading {zipPath} to {dstFolder}")
        t = Upload(fdServer, zipPath, dstFolder)
        retval = t.run()
        if not retval:
            print(f"Error: Could not upload")
            return False

        # once we get here, the project's code has been uploaded
        sp._status = Status.UPLOADEDCODE
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True

def doUploadCodeForSubproject(cfg, fdServer, prj, sp):
    # create top-level folder for project, if it doesn't already exist
    t = CreateFolder(fdServer, prj._name, "Software Repository")
    retval = t.run()
    if not retval:
        print(f"{prj._name}/{sp._name}: Could not create folder {prj._name}")
        return False

    # create one project-level folder for this month, and
    # upload all code there
    dstFolder = f"{prj._name}-{cfg._month}"
    t = CreateFolder(fdServer, dstFolder, prj._name)
    retval = t.run()
    if not retval:
        print(f"{prj._name}/{sp._name}: Could not create folder {dstFolder}")
        return False

    # make sure the subproject has not already had its code uploaded
    if sp._status != Status.UPLOADEDWS:
        print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected UPLOADEDWS")
        return True
    zipPath = sp._code_path
    if zipPath == "":
        print(f"{prj._name}/{sp._name}: skipping, no path found for retrieved code")
        sp._status = Status.STOPPED
        return True
    print(f"{prj._name}/{sp._name}: uploading {zipPath} to {dstFolder}")
    t = Upload(fdServer, zipPath, dstFolder)
    retval = t.run()
    if not retval:
        print(f"Error: Could not upload")
        return False

    # once we get here, the project's code has been uploaded
    sp._status = Status.UPLOADEDCODE
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
