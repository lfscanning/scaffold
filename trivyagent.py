# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE
import sys
import zipfile
import tempfile
import spdx.spdxutil
import spdx.xlsx
import shutil
from uploadspdx import doUploadFileForSubproject
from spdx_tools.spdx.parser.error import SPDXParsingError

def runUnifiedAgent(cfg, prj, sp):
    # make sure that the code to upload actually exists!
    if not sp._code_path:
        print(f"{prj._name}/{sp._name}: No code path found; can not run Trivy")
        return False
    if not os.path.exists(sp._code_path):
        print(f"{prj._name}/{sp._name}: Nothing found at code path {sp._code_path}; can not run Trivy")
        return False
    if not os.path.isfile(sp._code_path):
        print(f"{prj._name}/{sp._name}: Code path {sp._code_path} exists but is not a file; can not run Trivy")
        return False
    with tempfile.TemporaryDirectory() as tempdir:
        # Unzip file to a temporary directory
        analysisdir = os.path.join(tempdir, "code")
        os.mkdir(analysisdir)
        with zipfile.ZipFile(sp._code_path, mode='r') as zip:
            zip.extractall(analysisdir)
        cmd = [cfg._trivy_exec_path, "fs", "--timeout", "30m", "--scanners", "license,vuln", "--format", "spdx-json", analysisdir]
        result = os.path.join(tempdir, f"{prj._name}-{sp._name}-trivy-spdx.json")
        with open(result, 'w') as outfile:
            cp = run(cmd, stdout=outfile, stderr=PIPE, universal_newlines=True)
            if cp.returncode != 0:
                print(f"""{prj._name}/{sp._name}: Trivy failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
                return False
        try:
            spdxDocument = spdx.spdxutil.parseFile(result)
        except SPDXParsingError:
            print(f"{prj._name}/{sp._name}: unable to parse Trivy generated SPDX document")
            return False
        spdx.spdxutil.augmentTrivyDocument(spdxDocument, cfg, prj, sp)
        uploadSpdxFileName = f"{prj._name}-{sp._name}-spdx.json"
        uploadSpdxFile = os.path.join(tempdir, uploadSpdxFileName)
        spdx.spdxutil.writeFile(spdxDocument, uploadSpdxFile)
        if not doUploadFileForSubproject(cfg, prj, sp, tempdir, uploadSpdxFileName):
            print(f"{prj._name}/{sp._name}: unable to upload SPDX dependencies file")
            return False
        workbook = spdx.xlsx.makeXlsx(spdxDocument)
        workbookFilePath = os.path.join(tempdir, f"{prj._name}-{sp._name}-dependencies.xlsx")
        spdx.xlsx.saveXlsx(workbook, workbookFilePath)
        reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
        if not os.path.exists(reportFolder):
            os.makedirs(reportFolder)
        reportFilePath = os.path.join(reportFolder, f"{prj._name}-{sp._name}-dependencies.xlsx");
        shutil.copy(workbookFilePath, reportFilePath)
        print(f"{prj._name}/{sp._name}: Trivy successfully run")
        return True
        
