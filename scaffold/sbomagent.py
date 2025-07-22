# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
import pdb
from subprocess import run, PIPE
import sys
import zipfile
import tempfile
import spdx.spdxutil
import spdx.xlsx
import shutil
from datetime import datetime
from pathlib import Path

from scaffold.uploadspdx import doUploadFileForSubproject
from spdx_tools.spdx.parser.error import SPDXParsingError

trivyDebug = False
parlayDebug = False
cdsbomDebug = False

def runUnifiedAgent(cfg, prj, sp):
    # make sure that the code to upload actually exists!
    if not sp._code_path:
        print(f"{prj._name}/{sp._name}: No code path found; can not run sbom")
        return False
    if not os.path.exists(sp._code_path):
        print(f"{prj._name}/{sp._name}: Nothing found at code path {sp._code_path}; can not run sbom")
        return False
    if not os.path.isfile(sp._code_path):
        print(f"{prj._name}/{sp._name}: Code path {sp._code_path} exists but is not a file; can not run sbom")
        return False
    with tempfile.TemporaryDirectory() as tempdir:
        # Unzip file to a temporary directory
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Unzipping project files")
        analysisdir = os.path.join(tempdir, "code")
        os.mkdir(analysisdir)
        with zipfile.ZipFile(sp._code_path, mode='r') as zip:
            zip.extractall(analysisdir)
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Looking for NPM projects to install")
        installNpm(analysisdir, cfg, prj, sp)
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Running Trivy")
        if trivyDebug:
            trivy_cmd = [cfg._trivy_exec_path, "fs", "--timeout", "840m", "--debug", "--scanners", "license", "--format", "spdx-json", analysisdir]
            trivy_result = os.path.join(Path.home(), f"{prj._name}-{sp._name}-trivy-spdx.json")
        else:
            trivy_cmd = [cfg._trivy_exec_path, "fs", "--timeout", "840m", "--scanners", "license", "--format", "spdx-json", analysisdir]
            trivy_result = os.path.join(tempdir, f"{prj._name}-{sp._name}-trivy-spdx.json")
        trivy_error = Path.home() / "last-trivy-debug.txt"
        with open(trivy_result, 'w') as outfile:
            if trivyDebug:
                with open(trivy_error, 'w') as errorfile:
                    cp = run(trivy_cmd, stdout=outfile, stderr=errorfile, universal_newlines=True)
            else:
                cp = run(trivy_cmd, stdout=outfile, stderr=PIPE, universal_newlines=True)
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
        if parlayDebug:
            parlay_result = os.path.join(Path.home(), f"{prj._name}-{sp._name}-parlay-spdx.json")
        else:
            parlay_result = os.path.join(tempdir, f"{prj._name}-{sp._name}-parlay-spdx.json")
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Running Parlay")
        parlay_cmd = [cfg._parlay_exec_path, "ecosystems", "enrich", str(trivy_result)]
        with open(parlay_result, 'w') as outfile:
            cp = run(parlay_cmd, stdout=outfile, stderr=PIPE, universal_newlines=True)
            if cp.returncode != 0:
                print(f"""{prj._name}/{sp._name}: Parlay failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
                return False
        if cdsbomDebug:
            result = os.path.join(Path.home(), f"{prj._name}-{sp._name}-cdsbom-spdx.json")
        else:
            result = os.path.join(tempdir, f"{prj._name}-{sp._name}-cdsbom-spdx.json")
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Running cdsbom")
        cdsbom_cmd = [cfg._cdsbom_exec_path, "-out", str(result), str(parlay_result)]
        cp = run(cdsbom_cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        if cp.returncode != 0:
            print(f"""{prj._name}/{sp._name}: cdsbom failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
            return False
        spdx.spdxutil.fixLicenseExpressions(result)
        try:
            spdxDocument = spdx.spdxutil.parseFile(result)
        except SPDXParsingError:
            print(f"{prj._name}/{sp._name}: unable to parse Parlay augmented SPDX document")
            return False
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Augmenting SPDX document")
        spdx.spdxutil.augmentTrivyDocument(spdxDocument, cfg, prj, sp)
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Merging SPDX documents")
        fossologySpdxPath = os.path.join(cfg._storepath, "spdxrepos", f"spdx-{prj._name}", f"{sp._name}", f"{cfg._month}", f"{sp._name}-{sp._code_pulled}.spdx")
        if os.path.exists(fossologySpdxPath):
            fossologySbom = spdx.spdxutil.parseFile(fossologySpdxPath)
            mergedSbom = spdx.spdxutil.mergeSpdxDocs(fossologySbom, spdxDocument, cfg, prj, sp)
            mergedSbomFileName = f"{prj._name}-{sp._name}-merged-spdx.json"
            uploadMergedSbomFile = os.path.join(tempdir, mergedSbomFileName)
            spdx.spdxutil.writeFile(mergedSbom, uploadMergedSbomFile)
        else:
            print(f"{prj._name}/{sp._name}: Fossology SPDX file not found - skipping merge")
            mergedSbomFileName = None
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Uploading SBOMs")
        uploadSpdxFileName = f"{prj._name}-{sp._name}-spdx.json"
        uploadSpdxFile = os.path.join(tempdir, uploadSpdxFileName)
        spdx.spdxutil.writeFile(spdxDocument, uploadSpdxFile)
        if not doUploadFileForSubproject(cfg, prj, sp, tempdir, uploadSpdxFileName):
            print(f"{prj._name}/{sp._name}: unable to upload SPDX dependencies file")
            return False
        if mergedSbomFileName:
            if not doUploadFileForSubproject(cfg, prj, sp, tempdir, mergedSbomFileName):
                print(f"{prj._name}/{sp._name}: unable to upload merged SPDX file")
                return False
        workbook = spdx.xlsx.makeXlsx(spdxDocument)
        workbookFilePath = os.path.join(tempdir, f"{prj._name}-{sp._name}-dependencies.xlsx")
        spdx.xlsx.saveXlsx(workbook, workbookFilePath)
        reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
        if not os.path.exists(reportFolder):
            os.makedirs(reportFolder)
        reportFilePath = os.path.join(reportFolder, f"{prj._name}-{sp._name}-dependencies.xlsx");
        shutil.copy(workbookFilePath, reportFilePath)
        if uploadreport.doUploadSBOMReportsForSubproject(cfg, prj, sp):
            print(f"Web version of dependency report available at: {sp._web_sbom_url}")
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: SBOM successfully run")
        return True

def installNpm(sourceDir, cfg, prj, sp):
    npm_dirs = []
    for (root,dirs,files) in os.walk(sourceDir, topdown=True):
        if 'package.json' in files and 'node_modeles/' not in root and 'node_modules' not in dirs:
            npm_dirs.append(root)
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
        if '.git' in dirs:
            dirs.remove('.git')
    cachedir = os.path.join(cfg._zippath, "npmcache")
    for npm_dir in npm_dirs:
        cmd = [cfg._npm_exec_path, "install", "--production", "--cache", cachedir]
        cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd=npm_dir)
        if cp.returncode != 0:
            print(f"{prj._name}/{sp._name}: NPM install failed for {npm_dir} with exit code {cp.returncode}.")
    
