# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os

# from fossdriver.tasks import CreateFolder, Upload, Scanners, Copyright, BulkTextMatch, SPDXRDF, ImportRDF

from datatypes import Status

def doTransfer(scaffold_home, cfg, prj_name, old_server, new_server):
    raise RuntimeError("The transfer feature has not been upgraded to fossology python")
    if prj_name == "":
        print(f"Error: `transfer` command requires specifying only one project")
        return False

    # get prj for this project name
    prj = cfg._projects.get(prj_name, None)
    if prj is None:
        print(f"Error: cannot find project {prj_name}")
        return False

    # create top-level folder on new server for project,
    # if it doesn't already exist
    t = CreateFolder(new_server, prj._name, "Software Repository")
    retval = t.run()
    if not retval:
        print(f"{prj._name}: Could not create folder {prj._name}")
        return False

    # create one project-level folder on new server for
    # this month, and upload all code there
    dstFolder = f"{prj._name}-{cfg._month}"
    t = CreateFolder(new_server, dstFolder, prj._name)
    retval = t.run()
    if not retval:
        print(f"{prj._name}: Could not create folder {dstFolder}")
        return False

    dstFolderNum = new_server.GetFolderNum(dstFolder)

    # for each subproject where code was previously uploaded:
    for sp in prj._subprojects.values():
        if sp._status.value >= Status.UPLOADEDCODE.value and sp._status != Status.STOPPED:

            zipPath = sp._code_path
            uploadName = os.path.basename(zipPath)
            rdfFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
            rdfFilename = f"{sp._name}-{sp._code_pulled}.rdf"
            rdfFilePath = os.path.join(rdfFolder, rdfFilename)

            # check if already uploaded
            priorUploadNum = new_server.GetUploadNum(dstFolderNum, uploadName, True)
            if priorUploadNum != -1:
                print(f"{prj._name}/{sp._name}: already uploaded to new server; skipping")
                continue

            # retrieve RDF file from old server
            print(f"{prj._name}/{sp._name}: retrieving RDF for {uploadName} from old server, saving to {rdfFilePath}")
            t = SPDXRDF(old_server, uploadName, dstFolder, rdfFilePath)
            retval = t.run()

            # upload code to new server
            print(f"{prj._name}/{sp._name}: uploading {zipPath} to new server at {dstFolder}")
            t = Upload(new_server, zipPath, dstFolder)
            retval = t.run()
            if not retval:
                print(f"Error: upload failed")
                return False

            # run scanners and matches on new server
            # run nomos and monk
            print(f"{prj._name}/{sp._name}: running nomos and monk")
            t = Scanners(new_server, uploadName, dstFolder)
            retval = t.run()
            if not retval:
                print(f"{prj._name}/{sp._name}: error running license scanners")
                return False

            # run copyright
            print(f"{prj._name}/{sp._name}: running copyright")
            t = Copyright(new_server, uploadName, dstFolder)
            retval = t.run()
            if not retval:
                print(f"{prj._name}/{sp._name}: error running copyright scanner")
                return False

            # run bulk matches if the project has any
            if prj._matches != []:
                for m in prj._matches:
                    t = BulkTextMatch(new_server, uploadName, dstFolder, m._text)
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

            # import RDF on new server
            print(f"{prj._name}/{sp._name}: running RDF import")
            t = ImportRDF(new_server, rdfFilePath, uploadName, dstFolder)
            retval = t.run()
            if not retval:
                print(f"{prj._name}/{sp._name}: error running RDF import")
                return False

            # user will now need to manually re-clear copyrights.
            # note that the importing of copyright statements in Fossology
            # appears to be broken, as it results in duplicates of each
            # copyright statement.
            print(f"{prj._name}/{sp._name}: completed; now needs copyright re-clearing")

    return True
