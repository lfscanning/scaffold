# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from datatypes import Status, ProjectRepoType

WAIT_TIME = 10      # Time in seconds to check status on upload to fossology - timeout it 10 times this value

def doUploadCodeForProject(cfg, fossologyServer, prj):
    # create top-level folder for project, if it doesn't already exist
    try:
        folder = fossologyServer.create_folder(fossologyServer.rootFolder, prj._name)
    except Exception as e:
        print("Exception creating folder", e)
    if not folder:
        print(f"{prj._name}/{sp._name}: Could not create folder {prj._name}")
        return False

    # create one project-level folder for this month, and
    # upload all code there
    
    dstFolder = f"{prj._name}-{cfg._month}"
    try:
        folder = fossologyServer.create_folder(folder, dstFolder)
    except Exception as e:
        print("Exception creating folder", e)
    if not folder:
        print(f"{prj._name}/{sp._name}: Could not create folder {dstFolder}")
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
        retval = None
        try:
            retval = fossologyServer.upload_file(folder, file=zipPath, wait_time=WAIT_TIME)
        except Exception as e:
            print("Exception uploading file", e)
        if not retval:
            print(f"Error: Could not upload")
            return False
        # once we get here, the project's code has been uploaded
        sp._status = Status.UPLOADEDCODE
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True

def doUploadCodeForSubproject(cfg, fossologyServer, prj, sp):
    # create top-level folder for project, if it doesn't already exist
    try:
        folder = fossologyServer.create_folder(fossologyServer.rootFolder, prj._name)
    except Exception as e:
        print("Exception creating folder", e)
    if not folder:
        print(f"{prj._name}/{sp._name}: Could not create folder {prj._name}")
        return False

    # create one project-level folder for this month, and
    # upload all code there
    
    dstFolder = f"{prj._name}-{cfg._month}"
    try:
        folder = fossologyServer.create_folder(folder, dstFolder)
    except Exception as e:
        print("Exception creating folder", e)
    if not folder:
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
    retval = None
    try:
        retval = fossologyServer.upload_file(folder, file=zipPath, wait_time=WAIT_TIME)
    except Exception as e:
        print("Exception uploading file", e)
    if not retval:
        print(f"Error: Could not upload")
        return False

    # once we get here, the project's code has been uploaded
    sp._status = Status.UPLOADEDCODE
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
