# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE
import uuid
from shutil import copyfile

from datatypes import Status

# Upload a single file ending with the suffix
# returns the URL for the file - None if there was an error
def doUploadSingleReportForSubproject(cfg, prj, sp, suffix, extension):
    # make sure we're at the right stage
    if not (sp._status.value >= Status.ZIPPEDCODE.value and sp._status != Status.STOPPED):
        print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected ZIPPEDCODE or higher")
        return False

    if sp._web_uuid != "":
        web_uuid = sp._web_uuid
    else:
        # pick random uuid
        web_uuid = str(uuid.uuid4())
        sp._web_uuid = web_uuid

    # determine source and dest filenames
    srcReportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    srcReportFileName = f"{sp._name}-{sp._code_pulled}{'-' + suffix if suffix else ''}.{extension}"
    srcReportFilePath = os.path.join(srcReportFolder, srcReportFileName)

    dstReportFolder = os.path.join(cfg._web_reports_path, prj._name)
    dstReportFilename = f"{sp._name}-{sp._code_pulled}{'-' + suffix if suffix else ''}-{web_uuid}.{extension}"
    dstReportFilePath = os.path.join(dstReportFolder, dstReportFilename)

    # copy HTML report to server, if it exists (e.g., if there were any findings)
    if os.path.exists(srcReportFilePath):
        if cfg._web_server_use_scp:
            cmd = ["scp", srcReportFilePath, f"{cfg._web_server_username}@{cfg._web_server}:{dstReportFilePath}"]
            cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            if cp.returncode != 0:
                print(f"""{prj._name}/{sp._name}: scp of report file {srcReportFileName} failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
                return None
            else:
                print(f"{prj._name}/{sp._name}: uploaded report file {srcReportFileName}")
                return f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstReportFilename}"
        else:
            os.makedirs(os.path.dirname(dstReportFilePath), exist_ok=True)
            copyfile(srcReportFilePath, dstReportFilePath)
            print(f"{prj._name}/{sp._name}: uploaded report file {srcReportFileName}")
            return f"https://{cfg._web_server}/{cfg._web_reports_url}/{prj._name}/{dstReportFilename}"
    else:
        # no HTML file b/c no findings
        print(f"{prj._name}/{sp._name}: no report file {srcReportFileName} on disk, skipping")
    return None

def doUploadReportsForSubproject(cfg, prj, sp):
    # make sure we're at the right stage
    if sp._status != Status.UPLOADEDSPDX:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't upload findings reports")
        return False

    if sp._web_uuid != "":
        web_uuid = sp._web_uuid
    else:
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

# Runner for UPLOADREPORTS for overall project (where combined report)
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
