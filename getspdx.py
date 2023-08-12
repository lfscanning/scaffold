# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

# from fossdriver.tasks import SPDXTV

from datatypes import Status, ProjectRepoType

def doGetSPDXForSubproject(cfg, fdServer, prj, sp):
    uploadName = os.path.basename(sp._code_path)
    uploadFolder = f"{prj._name}-{cfg._month}"
    spdxFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
    spdxFilename = f"{sp._name}-{sp._code_pulled}.spdx"

    if uploadName == "":
        print(f"{prj._name}/{sp._name}: no code path in config, so no upload name; not running agents")
        return False

    # create spdx directory for project if it doesn't already exist
    if not os.path.exists(spdxFolder):
        os.makedirs(spdxFolder)

    # run SPDX tag-value agent
    print(f"{prj._name}/{sp._name}: getting SPDX tag-value file")
    spdxFilePath = os.path.join(spdxFolder, spdxFilename)
    t = SPDXTV(fdServer, uploadName, uploadFolder, spdxFilePath)
    retval = t.run()
    if not retval:
        print(f"{prj._name}/{sp._name}: error getting SPDX tag-value file")
        return False

    # once we get here, the agents have been run
    sp._status = Status.GOTSPDX
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
