# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from fossdriver.tasks import Scanners, Copyright, Reuse, BulkTextMatch

from datatypes import Status, ProjectRepoType
from datefuncs import parseYM, priorMonth, getYMStr

def priorUploadExists(fdServer, priorUploadFolder, priorUploadName):
    # first, get the old scan's folder and upload ID
    oldFolderNum = fdServer.GetFolderNum(priorUploadFolder)
    if oldFolderNum is None or oldFolderNum == -1:
        return False
    oldUploadNum = fdServer.GetUploadNum(oldFolderNum, priorUploadName, False)
    if oldUploadNum is None or oldUploadNum == -1:
        return False
    # if we get here, the old scan exists
    return True


def doRunAgentsForSubproject(cfg, fdServer, prj, sp):
    year, month = parseYM(cfg._month)

    uploadName = os.path.basename(sp._code_path)
    uploadFolder = f"{prj._name}-{cfg._month}"

    if uploadName == "":
        print(f"{prj._name}/{sp._name}: no code path in config, so no upload name; not running agents")
        return False

    # run nomos and monk
    print(f"{prj._name}/{sp._name}: running nomos and monk")
    t = Scanners(fdServer, uploadName, uploadFolder)
    retval = t.run()
    if not retval:
        print(f"{prj._name}/{sp._name}: error running license scanners")
        return False
    
    # run copyright
    print(f"{prj._name}/{sp._name}: running copyright")
    t = Copyright(fdServer, uploadName, uploadFolder)
    retval = t.run()
    if not retval:
        print(f"{prj._name}/{sp._name}: error running copyright scanner")
        return False
    
    # run reuser agent if prior upload exists, checking up to 6 prior months
    pYear = year
    pMonth = month
    numTries = 6
    foundPrior = False
    while numTries > 0:
        pYear, pMonth = priorMonth(pYear, pMonth)
        pYM = getYMStr(pYear, pMonth)
        priorUploadFragment = f"{sp._name}-{pYM}"
        priorFolder = f"{prj._name}-{pYM}"

        if priorUploadExists(fdServer, priorFolder, priorUploadFragment):
            foundPrior = True
            print(f"{prj._name}/{sp._name}: running reuser from {pYM}")
            t = Reuse(fdServer, uploadName, uploadFolder, priorUploadFragment, priorFolder)
            t.exact = False
            retval = t.run()
            if not retval:
                # keep going anyway, don't fail
                print(f"{prj._name}/{sp._name}: error running reuse from {priorUploadFragment} in {priorFolder}, skipping reuser")
            break
        else:
            print(f"{prj._name}/{sp._name}: didn't find prior upload for {pYM}")
            numTries -= 1

    if not foundPrior:
        print(f"{prj._name}/{sp._name}: no prior upload found in preceding 6 months, skipping reuser")
    
    # run bulk matches if the project has any
    if prj._matches != []:
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

    # once we get here, the agents have been run
    sp._status = Status.RANAGENTS
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
