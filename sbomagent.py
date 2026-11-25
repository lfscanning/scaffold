# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import json
import os
import pdb
from subprocess import run, PIPE
import sys
import zipfile
import tempfile
import spdx.spdxutil
import spdx.xlsx
import spdx.dependencyhtml
import shutil
from datetime import datetime
from pathlib import Path

import gradle_lockfiles
import npm_lockfiles
import uploadreport
import uploadspdx
from spdx_tools.spdx.parser.error import SPDXParsingError

trivyDebug = False
parlayDebug = False
cdsbomDebug = False
spdxV3Debug = False

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
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Looking for NPM projects to lock")
        npmResult = generateNpmLockFiles(analysisdir, cfg, prj, sp)
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Looking for Gradle projects to lock")
        gradleResult = generateGradleLockFiles(analysisdir, cfg, prj, sp)
        dependencyReport = makeDependencyReport([npmResult, gradleResult])
        totals = dependencyReport["summary"]
        print(f"{prj._name}/{sp._name}: Dependency collection summary: {totals['processed']} processed, "
              f"{totals['errors']} errors, {totals['skipped']} skipped")
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
            print(f"""{prj._name}/{sp._name}: WARNING: cdsbom skipped due to failure with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
            result = parlay_result
            # skip cdsbom - reference issue 175
        spdx.spdxutil.fixLicenseExpressions(result)
        try:
            spdxDocument = spdx.spdxutil.parseFile(result)
        except SPDXParsingError:
            print(f"{prj._name}/{sp._name}: unable to parse Parlay augmented SPDX document")
            return False
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Augmenting SPDX document")
        spdx.spdxutil.augmentTrivyDocument(spdxDocument, cfg, prj, sp)
        uploadSpdxFileName = f"{sp._name}-{sp._code_pulled}-{uploadspdx.UPLOAD_SPDX_SUFFIX}.{uploadspdx.JSON_EXTENSION}"
        uploadSpdxFile = os.path.join(tempdir, uploadSpdxFileName)
        spdx.spdxutil.writeFile(spdxDocument, uploadSpdxFile)
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Creating SPDX 3 document")
        uploadSpdxV3FileName = f"{sp._name}-{sp._code_pulled}-{uploadspdx.UPLOAD_SPDX_V3_SUFFIX}.{uploadspdx.JSON_EXTENSION}"
        if spdxV3Debug:
            uploadSpdxV3File = os.path.join(Path.home(), uploadSpdxV3FileName)
        else:
            uploadSpdxV3File = os.path.join(tempdir, uploadSpdxV3FileName)
        try:
            convertToV3(uploadSpdxFile, uploadSpdxV3File, cfg, prj, sp)
            if spdxV3Debug:
                shutil.copy(uploadSpdxV3File, os.path.join(Path.home(), f"{prj._name}-{sp._name}-spdx-v3-before-fix.json"))
            if os.path.exists(uploadSpdxV3File):
                spdx.spdxutil.fixSpdxV3File(uploadSpdxV3File)
        except Exception as e:
            print(f"{prj._name}/{sp._name}: error converting dependency SBOM to SPDX V3")
            print(f"Detailed exception message: {e}")
            if Path(uploadSpdxV3File).is_file():
                os.remove(uploadSpdxV3File)

        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Merging SPDX documents")
        mergedSbom = mergeSourceAndSbom(cfg, prj, sp, tempdir, spdxDocument)
        if mergedSbom:
            mergedSbomFileName = f"{sp._name}-{sp._code_pulled}-{uploadspdx.MERGED_SBOM_SUFFIX}.{uploadspdx.JSON_EXTENSION}"
            uploadMergedSbomFile = os.path.join(tempdir, mergedSbomFileName)
            spdx.spdxutil.writeFile(mergedSbom, uploadMergedSbomFile)
            mergedSbomV3FileName = f"{sp._name}-{sp._code_pulled}-{uploadspdx.MERGED_SBOM_V3_SUFFIX}.{uploadspdx.JSON_EXTENSION}"
            if spdxV3Debug:
                uploadMergedSbomV3File = os.path.join(Path.home(), mergedSbomV3FileName)
            else:
                uploadMergedSbomV3File = os.path.join(tempdir, mergedSbomV3FileName)
            try:
                convertToV3(uploadMergedSbomFile, uploadMergedSbomV3File, cfg, prj, sp)
                if os.path.exists(uploadMergedSbomV3File):
                    if spdxV3Debug:
                        shutil.copy(uploadMergedSbomV3File, os.path.join(Path.home(), f"{prj._name}-{sp._name}-merged-spdx-v3-before-fix.json"))
                    spdx.spdxutil.fixSpdxV3File(uploadMergedSbomV3File)
            except Exception as e:
                print(f"{prj._name}/{sp._name}: error converting merged SBOM to SPDX V3")
                print(f"Detailed exception message: {e}")
                if Path(uploadMergedSbomV3File).is_file():
                    os.remove(uploadMergedSbomV3File)
        else:
            print(f"{prj._name}/{sp._name}: Fossology SPDX file not found - skipping merge")
            uploadMergedSbomFile = None
            uploadMergedSbomV3File = None

        # Upload the documents
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: Uploading SBOMs")
        if not uploadspdx.doUploadFileForSubproject(cfg, prj, sp, tempdir, uploadspdx.UPLOAD_SPDX_SUFFIX, uploadspdx.JSON_EXTENSION):
            print(f"{prj._name}/{sp._name}: unable to upload SPDX dependencies file")
            return False
        if uploadSpdxV3File and os.path.exists(uploadSpdxV3File):
            if not uploadspdx.doUploadFileForSubproject(cfg, prj, sp, Path.home() if spdxV3Debug else tempdir, uploadspdx.UPLOAD_SPDX_V3_SUFFIX, uploadspdx.JSON_EXTENSION):
                print(f"{prj._name}/{sp._name}: unable to upload SPDX V3 dependencies file")
                return False
        else:
            print(f"{prj._name}/{sp._name}: no SPDX V3 file to upload")
            print(f"Filename: {uploadSpdxV3File}")
            print(f"V2 SPDX filename: {uploadSpdxFile}")
        if uploadMergedSbomFile and os.path.exists(uploadMergedSbomFile):
            if not uploadspdx.doUploadFileForSubproject(cfg, prj, sp, tempdir, uploadspdx.MERGED_SBOM_SUFFIX, uploadspdx.JSON_EXTENSION):
                print(f"{prj._name}/{sp._name}: unable to upload merged SPDX file")
                print(f"Filename: {uploadMergedSbomFile}")
                return False
        else:
            print(f"{prj._name}/{sp._name}: no merged SBOM file to upload")
        if uploadMergedSbomV3File and os.path.exists(uploadMergedSbomV3File):
            if not uploadspdx.doUploadFileForSubproject(cfg, prj, sp, Path.home() if spdxV3Debug else tempdir, uploadspdx.MERGED_SBOM_V3_SUFFIX, uploadspdx.JSON_EXTENSION):
                print(f"{prj._name}/{sp._name}: unable to upload merged SPDX V3 file")
                print(f"Filename: {uploadMergedSbomV3File}")
                return False
        else:
            print(f"{prj._name}/{sp._name}: no merged SPDX V3 SBOM file to upload")
        workbook = spdx.xlsx.makeXlsx(spdxDocument)
        workbookSuffix = "dependencies"
        workbookExtension = "xlsx"
        workbookFilePath = os.path.join(tempdir, f"{sp._name}-{sp._code_pulled}-{workbookSuffix}.{workbookExtension}")
        spdx.xlsx.saveXlsx(workbook, workbookFilePath)
        reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
        if not os.path.exists(reportFolder):
            os.makedirs(reportFolder)
        reportFilePath = os.path.join(reportFolder, f"{sp._name}-{sp._code_pulled}-{workbookSuffix}.{workbookExtension}");
        shutil.copy(workbookFilePath, reportFilePath)
        webSbomUrl = uploadreport.doUploadSingleReportForSubproject(cfg, prj, sp, workbookSuffix, workbookExtension)
        if webSbomUrl:
            sp._web_sbom_url: bool | str = webSbomUrl
            print(f"Excel dependency report available at: {sp._web_sbom_url}")
        dependenciesHtmlSuffix = "dependencies"
        htmlExtension = "html"
        dependenciesHtml = spdx.dependencyhtml.makeHtml(spdxDocument, prj, sp)
        dependenciesHtmlFilePath = os.path.join(reportFolder, f"{sp._name}-{sp._code_pulled}-{dependenciesHtmlSuffix}.{htmlExtension}")
        with open(dependenciesHtmlFilePath, "w") as report_f:
            report_f.write(dependenciesHtml)
        dependenciesHtmlUrl = uploadreport.doUploadSingleReportForSubproject(cfg, prj, sp, dependenciesHtmlSuffix, htmlExtension)
        if dependenciesHtmlUrl:
            sp._dependencies_html_url = dependenciesHtmlUrl
            print(f"Web version of dependency report available at: {sp._dependencies_html_url}")
        if dependencyReport["errors"] or dependencyReport["skipped"]:
            errorsSuffix = "dependency-errors"
            errorsExtension = "json"
            errorsFilePath = os.path.join(reportFolder, f"{sp._name}-{sp._code_pulled}-{errorsSuffix}.{errorsExtension}")
            with open(errorsFilePath, "w", encoding="utf-8") as errors_f:
                json.dump(dependencyReport, errors_f, indent=2)
            errorsUrl = uploadreport.doUploadSingleReportForSubproject(cfg, prj, sp, errorsSuffix, errorsExtension)
            if errorsUrl:
                print(f"Dependency collection errors available at: {errorsUrl}")
        print(f"{prj._name}/{sp._name} [{datetime.now()}]: SBOM successfully run")
        return True

def mergeSourceAndSbom(cfg, prj, sp, tempdir, spdxDocument):
    fossologySpdxTagPath = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name, f"{sp._name}-{sp._code_pulled}.spdx")
    if os.path.exists(fossologySpdxTagPath):
        fixedFossologySpdxTagPath = os.path.join(tempdir, f"{sp._name}-{sp._code_pulled}-fixed.spdx")
        if not spdx.spdxutil.fixSpdxTagValue(fossologySpdxTagPath, fixedFossologySpdxTagPath):
            print(f"{prj._name}/{sp._name}: WARNING: Unable to fix SPDX tag/value file")
            return None
        # Convert to JSON using the Java utility - refererence https://github.com/lfscanning/scaffold/issues/201
        fossologySpdxPath = os.path.join(tempdir, f"{sp._name}-{sp._code_pulled}.json")
        convertSpdxFile(fixedFossologySpdxTagPath, fossologySpdxPath, cfg, prj, sp, "TAG", "JSON")
        if os.path.exists(fossologySpdxPath):
            fossologySbom = spdx.spdxutil.parseFile(fossologySpdxPath)
            return spdx.spdxutil.mergeSpdxDocs(fossologySbom, spdxDocument, cfg, prj, sp)
        else:
            print(f"{prj._name}/{sp._name}: WARNING: No converted FOSSOlogy JSON file")
            return None
    else:
        return None

def makeDependencyReport(results):
    # Combine the per-ecosystem results into one report: a summary plus the individual errors and skips.
    errors = [e for r in results for e in r["errors"]]
    skipped = [s for r in results for s in r["skipped"]]
    return {
        "summary": {
            "processed": sum(r["processed"] for r in results),
            "errors": len(errors),
            "skipped": len(skipped),
            "by_ecosystem": {
                r["ecosystem"]: {"processed": r["processed"], "errors": len(r["errors"]), "skipped": len(r["skipped"])}
                for r in results
            },
        },
        "errors": errors,
        "skipped": skipped,
    }

def generateNpmLockFiles(sourceDir, cfg, prj, sp):
    # Create package-lock.json for NPM projects that don't have one so that Trivy can see
    # their resolved dependencies. Like generateGradleLockFiles, failures never stop the run.
    # Individual errors and skips are not logged; they are returned for the dependency report.
    # Returns {"ecosystem", "processed", "errors": [...], "skipped": [...]}.
    cachedir = os.path.join(cfg._zippath, "npmcache")
    errors = []
    skipped = []
    processed = 0
    try:
        summary = npm_lockfiles.generate_npm_lockfiles(
            sourceDir,
            cfg._npm_exec_path,
            cachedir,
            errors=errors,
            skipped=skipped,
        )
        processed = summary["processed"]
    except Exception as e:
        errors.append({"ecosystem": "npm", "file": ".", "error": f"NPM lock file generation failed unexpectedly: {e}"})
    return {"ecosystem": "npm", "processed": processed, "errors": errors, "skipped": skipped}

def generateGradleLockFiles(sourceDir, cfg, prj, sp):
    # Create gradle.lockfile for Gradle projects that don't have one so that Trivy can see
    # their resolved dependencies. Like installNpm, failures are reported but never stop the run.
    label = f"{prj._name}/{sp._name}"
    # Individual errors and skips are not logged; they are returned for the dependency report.
    # Returns {"ecosystem", "processed", "errors": [...], "skipped": [...]}.
    cachedir = os.path.join(cfg._zippath, "gradlecache")
    try:
        result = gradle_lockfiles.generate_lockfiles(
            Path(sourceDir),
            gradle_exe=getattr(cfg, "_gradle_exec_path", None),  # used only when a project has no gradlew
            java_home=None,  # we only want to use the jdks parameter, java_home will override jdks
            jdks=getattr(cfg, "_gradle_jdks", None) or (),  # or several (e.g. JDK 17 + 21): the right one is picked per build
            env={"GRADLE_USER_HOME": cachedir},
            log=lambda msg: print(f"{label}: {msg}"),
        )
    except Exception as e:
        return {"ecosystem": "gradle", "processed": 0, "skipped": [],
                "errors": [{"ecosystem": "gradle", "file": ".",
                            "error": f"Gradle lock file generation failed unexpectedly: {e}"}]}
    return {"ecosystem": "gradle", "processed": result.processed, "errors": result.errors, "skipped": result.skipped}

def convertToV3(spdxv2File, spdxv3File, cfg, prj, sp):
    convertSpdxFile(spdxv2File, spdxv3File, cfg, prj, sp, "JSON", "JSONLD")

def convertSpdxFile(fromFile, toFile, cfg, prj, sp, fromType, toType):
    if Path(toFile).is_file():
        os.remove(toFile)
    cmd = ["java", "-jar", cfg._tools_java_path, "Convert", str(fromFile), str(toFile), fromType, toType]
    cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if cp.returncode != 0:
        print(f"""{prj._name}/{sp._name}: WARNING: unable to convert {fromFile} to {toFile} due to {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        if toFile and Path(toFile).is_file():
            os.remove(toFile)  # clean up failed conversion