# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
import time
from pathlib import Path
from fossology.obj import Upload

from datatypes import Status, ProjectRepoType


TIME_BETWEEN_RETRIES = 10  # seconds
RETRIES_BETWEEN_MESSAGES = 12

def upload_file(fossologyServer, folder, file):
    # some code copied from fossology-python https://github.com/fossology/fossology-python/blob/main/fossology/uploads.py#L128
    # Licensed under MIT
    headers = {"folderId": str(folder.id)}
    headers["uploadType"] = "file"
    with open(file, "rb") as fp:
        files = {"fileInput": fp}
        response = fossologyServer.session.post(
            f"{fossologyServer.api}/uploads", files=files, headers=headers
        )
        # This will initiate the file upload
    source = f"{file}"
    if response.status_code == 201:
        # Successfully initiated - now we need to check to see if it is done
        upload_id =  response.json()["message"]
        done = False
        retries = 0
        while not done:
            checkResponse = fossologyServer.session.get(f"{fossologyServer.api}/uploads/{upload_id}", headers={})
            if checkResponse.status_code == 200:
                # we're done
                done = True
                upload = Upload.from_json(checkResponse.json())
                print(f"Upload completed for {file}")
            elif checkResponse.status_code == 403:
                description = f"Authorization error checking for status on upload for {file}"
                raise Exception(description)
            elif checkResponse.status_code == 503:
                # Still waiting
                retries = retries + 1
                if retries % RETRIES_BETWEEN_MESSAGES == 0:
                    msg = f"Waiting for upload of {file}"
                    print(msg)
                time.sleep(TIME_BETWEEN_RETRIES)
            else:
                description = f"Error checking for status on upload for {file}"
                raise Exception(description)
    elif response.status_code == 403:
        description = f"Authorization error uploading {file}"
        raise Exception(description)
    else:
        description = "Error uploading {file}"
        raise Exception(description)
    return True

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
            retval = upload_file(fossologyServer, folder, zipPath)
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
        retval = upload_file(fossologyServer, folder, zipPath)
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
