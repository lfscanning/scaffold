# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE
import uuid
from shutil import copyfile

from scaffold.datatypes import Status

# Upload ony the SBOMs
def doUploadSBOMReportsForSubproject(cfg, prj, sp):
    # make sure we're at the right stage
    if not (sp._status.value >= Status.ZIPPEDCODE.value and sp._status != Status.STOPPED):
        print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected ZIPPEDCODE or higher")
        return False

    # pick random uuid
    web_uuid = str(uuid.uuid4())
    sp._web_uuid = web_uuid

    # determine source and dest filenames
    srcReportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    srcSbomXlsx = f"{prj._name}-{sp._name}-dependencies.xlsx"
    srcSbomPath = os.path.join(srcReportFolder, srcSbomXlsx)

    dstReportFolder = os.path.join(cfg._web_reports_path, prj._name)
    dstSbomFilename = f"{prj._name}-{sp._name}-{web_uuid}-dependencies.xlsx"
    dstSbomPath = os.path.join(dstReportFolder, dstSbomFilename)

    # copy HTML report to server, if it exists (e.g., if there were any findings)
    if os.path.exists(srcSbomPath):
        if cfg._web_server_use_scp:
            cmd = ["scp", srcSbomPath, f"{cfg._web_server_username}@{cfg._web_server}:{dstSbomPath}"]
            cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            if cp.returncode != 0:
                print(f"""{prj._name}/{sp._name}: scp of SBOM dependency report failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
                return False
            else:
                print(f"{prj._name}/{sp._name}: uploaded SBOM dependency report")
                sp._web_sbom_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstSbomFilename}"
        else:
            os.makedirs(os.path.dirname(dstSbomPath), exist_ok=True)
            copyfile(srcSbomPath, dstSbomPath)
            print(f"{prj._name}/{sp._name}: uploaded SBOM dependency report")
            sp._web_sbom_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstSbomFilename}"
    else:
        # no HTML file b/c no findings
        print(f"{prj._name}/{sp._name}: no SBOM dependency report on disk, skipping")
    return True

# Runner for UPLOADEDSPDX for subproject
def doUploadReportsForSubproject(cfg, prj, sp):
    # make sure we're at the right stage
    if sp._status != Status.UPLOADEDSPDX:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't upload findings reports")
        return False

    # pick random uuid
    web_uuid = str(uuid.uuid4())
    sp._web_uuid = web_uuid

    # determine source and dest filenames
    srcReportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    srcHtmlFilename = f"{sp._name}-{sp._code_pulled}.html"
    srcHtmlPath = os.path.join(srcReportFolder, srcHtmlFilename)
    srcXlsxFilename = f"{sp._name}-{sp._code_pulled}.xlsx"
    srcXlsxPath = os.path.join(srcReportFolder, srcXlsxFilename)

    dstReportFolder = os.path.join(cfg._web_reports_path, prj._name)
    dstHtmlFilename = f"{sp._name}-{sp._code_pulled}-{web_uuid}.html"
    dstHtmlPath = os.path.join(dstReportFolder, dstHtmlFilename)
    dstXlsxFilename = f"{sp._name}-{sp._code_pulled}-{web_uuid}.xlsx"
    dstXlsxPath = os.path.join(dstReportFolder, dstXlsxFilename)

    # copy HTML report to server, if it exists (e.g., if there were any findings)
    if os.path.exists(srcHtmlPath):
        if cfg._web_server_use_scp:
            cmd = ["scp", srcHtmlPath, f"{cfg._web_server_username}@{cfg._web_server}:{dstHtmlPath}"]
            cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            if cp.returncode != 0:
                print(f"""{prj._name}/{sp._name}: scp of HTML report failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
                return False
            else:
                print(f"{prj._name}/{sp._name}: uploaded HTML report")
                sp._web_html_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstHtmlFilename}"
        else:
            os.makedirs(os.path.dirname(dstHtmlPath), exist_ok=True)
            copyfile(srcHtmlPath, dstHtmlPath)
            print(f"{prj._name}/{sp._name}: uploaded HTML report")
            sp._web_html_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstHtmlFilename}"
    else:
        # no HTML file b/c no findings
        print(f"{prj._name}/{sp._name}: no HTML report on disk, skipping")

    # copy XLSX report to server
    if cfg._web_server_use_scp:
        cmd = ["scp", srcXlsxPath, f"{cfg._web_server_username}@{cfg._web_server}:{dstXlsxPath}"]
        cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        if cp.returncode != 0:
            print(f"""{prj._name}/{sp._name}: scp of XLSX report failed with error code {cp.returncode}:
    ----------
    output:
    {cp.stdout}
    ----------
    errors:
    {cp.stderr}
    ----------
    """)
            return False
        else:
            print(f"{prj._name}/{sp._name}: uploaded XLSX report")
            sp._web_xlsx_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstXlsxFilename}"
    else:
        os.makedirs(os.path.dirname(dstXlsxPath), exist_ok=True)
        copyfile(srcXlsxPath, dstXlsxPath)
        print(f"{prj._name}/{sp._name}: uploaded XLSX report")
        sp._web_xlsx_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstXlsxFilename}"

    # success!
    sp._status = Status.UPLOADEDREPORTS
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True

# Runner for UPLOADEDSPDX for overall project (where combined report)
def doUploadReportsForProject(cfg, prj):
    # make sure we're at the right stage
    if prj._status != Status.UPLOADEDSPDX:
        print(f"{prj._name} COMBINED: status is {prj._status}, won't upload findings reports")
        return False

    # pick random uuid
    web_uuid = str(uuid.uuid4())
    prj._web_combined_uuid = web_uuid

    # determine source and dest filenames
    srcReportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    srcHtmlFilename = f"{prj._name}-{cfg._month}.html"
    srcHtmlPath = os.path.join(srcReportFolder, srcHtmlFilename)
    srcXlsxFilename = f"{prj._name}-{cfg._month}.xlsx"
    srcXlsxPath = os.path.join(srcReportFolder, srcXlsxFilename)

    dstReportFolder = os.path.join(cfg._web_reports_path, prj._name)
    dstHtmlFilename = f"{prj._name}-{cfg._month}-{web_uuid}.html"
    dstHtmlPath = os.path.join(dstReportFolder, dstHtmlFilename)
    dstXlsxFilename = f"{prj._name}-{cfg._month}-{web_uuid}.xlsx"
    dstXlsxPath = os.path.join(dstReportFolder, dstXlsxFilename)
    

    # scp HTML report to server, if it exists (e.g., if there were any findings)
    if os.path.exists(srcHtmlPath):
        if cfg._web_server_use_scp:
            cmd = ["scp", srcHtmlPath, f"{cfg._web_server_username}@{cfg._web_server}:{dstHtmlPath}"]
            cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            if cp.returncode != 0:
                print(f"""{prj._name}: scp of HTML report failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
                return False
            else:
                print(f"{prj._name}: uploaded HTML report")
                prj._web_combined_html_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstHtmlFilename}"
        else:
            os.makedirs(os.path.dirname(dstHtmlPath), exist_ok=True)
            copyfile(srcHtmlPath, dstHtmlPath)
            print(f"{prj._name}: uploaded HTML report")
            prj._web_combined_html_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstHtmlFilename}"
    else:
        # no HTML file b/c no findings
        print(f"{prj._name}: no HTML report on disk, skipping")

    # scp XLSX report to server
    if cfg._web_server_use_scp:
        cmd = ["scp", srcXlsxPath, f"{cfg._web_server_username}@{cfg._web_server}:{dstXlsxPath}"]
        cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        if cp.returncode != 0:
            print(f"""{prj._name}: scp of XLSX report failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
            return False
        else:
            print(f"{prj._name}: uploaded XLSX report")
            prj._web_combined_xlsx_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstXlsxFilename}"
    else:
        os.makedirs(os.path.dirname(dstHtmlPath), exist_ok=True)
        copyfile(srcHtmlPath, dstHtmlPath)
        print(f"{prj._name}: uploaded XLSX report")
        prj._web_combined_xlsx_url = f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstXlsxFilename}"
    # success!
    prj._status = Status.UPLOADEDREPORTS

    return True
