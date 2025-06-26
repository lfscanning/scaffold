# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from .datatypes import Status, ProjectRepoType
from .runagents import getUploadFolder, getUpload
from fossology.obj import ReportFormat
def doGetSPDXForSubproject(cfg, fossologyServer, prj, sp):
    uploadName = os.path.basename(sp._code_path)
    uploadFolderName = f"{prj._name}-{cfg._month}"
    spdxFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
    spdxFilename = f"{sp._name}-{sp._code_pulled}.spdx"

    if uploadName == "":
        print(f"{prj._name}/{sp._name}: no code path in config, so no upload name; not running agents")
        return False

    uploadFolder = getUploadFolder(fossologyServer, uploadFolderName)
    if not uploadFolder:
        print(f"{prj._name}/{sp._name}: error getting the upload folder for generation of SPDX file")
        return False
    upload = getUpload(fossologyServer, uploadFolder, uploadName)
    if not upload:
        print(f"{prj._name}/{sp._name}: error getting the upload generation of SPDX file")
        return False
        
    # create spdx directory for project if it doesn't already exist
    if not os.path.exists(spdxFolder):
        os.makedirs(spdxFolder)
    
    print(f"{prj._name}/{sp._name}: getting SPDX tag-value file")
    spdxFilePath = os.path.join(spdxFolder, spdxFilename)
    
    try:
        report_id = fossologyServer.generate_report(upload, report_format=ReportFormat.SPDX2TV, group="fossy")
        content, name = fossologyServer.download_report(report_id, wait_time=60)
        with open(spdxFilePath, "wb") as reportFile:
            written = reportFile.write(content)
            assert written == len(content)
    except Exception as e:
        print(f"{prj._name}/{sp._name}: error getting SPDX tag-value file")
        print(e)
        return False

    # once we get here, the agents have been run
    sp._status = Status.GOTSPDX
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
