# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
import copy
from pathlib import Path

from datatypes import Status, ProjectRepoType
from datefuncs import parseYM, priorMonth, getYMStr

def getUploadFolder(fossologyServer, uploadFolderName):
    ''' Gets the prior upload folder searching all folders for a matching name
        returns None if no upload or priorUploadFolder exists
    '''
    folder = None
    for fossFolder in fossologyServer.list_folders():
        if fossFolder.name == uploadFolderName:
            folder = fossFolder
            break
    return folder
    
def getUpload(fossologyServer, uploadFolder, uploadNameFragment):
    '''
    Gets an upload from the upload folder if the folder contains an upload who's name starts with uploadNameFragment.  Returns None if it doesn't exists
    '''
    if not uploadFolder:
        return None
    uploads = fossologyServer.list_uploads(folder=uploadFolder)[0]
    for upload in uploads:
        if upload.uploadname.lower().startswith(uploadNameFragment.lower()):
            return upload
    return None     # Didn't find it

def uploadExists(fossologyServer, priorUploadFolder, uploadNameFragment):
    folder = priorUploadFolder
    if isinstance(folder, str):
        folder = getUploadFolder(fossologyServer, priorUploadFolder)
        if not folder:
            return None
    if getUpload(fossologyServer, folder, uploadNameFragment):
        return True
    else:
        return False

def doRunAgentsForSubproject(cfg, fossologyServer, prj, sp):
    year, month = parseYM(cfg._month)

    uploadName = os.path.basename(sp._code_path)
    uploadFolderName = f"{prj._name}-{cfg._month}"

    if uploadName == "":
        print(f"{prj._name}/{sp._name}: no code path in config, so no upload name; not running agents")
        return False

    # run nomos and monk
    print(f"{prj._name}/{sp._name}: running nomos and monk")
    uploadFolder = getUploadFolder(fossologyServer, uploadFolderName)
    if not uploadFolder:
        print(f"{prj._name}/{sp._name}: Upload folder not found")
        return False
    upload = getUpload(fossologyServer, uploadFolder, uploadName)
    if not upload:
        print(f"{prj._name}/{sp._name}: Upload found")
        return False
        
    jobSpec = copy.deepcopy(cfg._fossology_job_spec)
    # run reuser agent if prior upload exists, checking up to 12 prior months
    pYear = year
    pMonth = month
    numTries = 24
    foundPrior = False
    while numTries > 0:
        pYear, pMonth = priorMonth(pYear, pMonth)
        pYM = getYMStr(pYear, pMonth)
        priorUploadFragment = f"{sp._name}-{pYM}"
        priorFolderName = f"{prj._name}-{pYM}"
        priorFolder = getUploadFolder(fossologyServer, priorFolderName)
        if priorFolder:
            priorUpload = getUpload(fossologyServer, priorFolder, priorUploadFragment)
            if priorUpload:           
                foundPrior = True
                print(f"{prj._name}/{sp._name}: running reuser from {pYM}")
                jobSpec["reuse"] = {
                    "reuse_upload": priorUpload.id,
                    "reuse_group": "fossy",
                    "reuse_main": True,
                    "reuse_enhanced": False,
                    "reuse_report": False,
                    "reuse_copyright": True,
                }
                break
            else:
                print(f"{prj._name}/{sp._name}: didn't find prior upload for {pYM}")
                numTries -= 1
        else:
            print(f"{prj._name}/{sp._name}: didn't find prior upload folder {pYM}")
            numTries -= 1

    if not foundPrior:
        print(f"{prj._name}/{sp._name}: no prior upload found in preceding 12 months, skipping reuser")
    
    # run bulk matches if the project has any
    if prj._matches != []:
        print(f"{prj._name}/{sp._name}: contains bulk matches - these were not run - this feature depends on the next version of FOSSology")
        '''
        for m in prj._matches:
            t = BulkTextMatch(fdServer, uploadName, uploadFolder, m._text)
            for (action, licName) in m._actions:
                if action == "add":
                    t.add(licName)
                elif action == "remove":
                    t.remove(licName)
            if m._comment == "":
                print(f"{prj._name}/{sp._name}: running bulk text match")
            else:
                print(f"{prj._name}/{sp._name}: running bulk text match for {m._comment}")
            retval = t.run()
            if not retval:
                print(f"{prj._name}/{sp._name}: error running bulk text match")
                return False
        '''
    # We have everything configured, we can start the run
    try:
        job = fossologyServer.schedule_jobs(uploadFolder, upload, jobSpec, wait=True, timeout=10)
    except Exception:
         print(f"{prj._name}/{sp._name}: Exception running scanning job - see FOSSology for details")
         return False
    # Poll for completion
    while job.status == "Processing":
        print(f"{prj._name}/{sp._name}: Waiting for scan completion...")
        job = fossologyServer.detail_job(job.id, wait=True, timeout=30)
    if job.status != "Completed":
        print(f"{prj._name}/{sp._name}: Error running scanning job - see FOSSology for details")
        return False
    # once we get here, the agents have been run
    sp._status = Status.RANAGENTS
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
