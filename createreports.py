# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from subprocess import run, PIPE

from datatypes import Status

def doCreateReportForSubproject(cfg, prj, sp):
    # make sure we're at the right stage
    if sp._status != Status.IMPORTEDSCAN:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't create report now")
        return False

    # set report path
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    reportFilename = f"{sp._name}-{sp._code_pulled}.xlsx"
    jsonFilename = f"{sp._name}-{sp._code_pulled}.json"

    # create report directory for project if it doesn't already exist
    if not os.path.exists(reportFolder):
        os.makedirs(reportFolder)

    # set up environment variables
    os.environ["SLM_HOME"] = cfg._slm_home
    if prj._slm_shared == True:
        os.environ["SLM_PROJECT"] = prj._slm_prj
    else:
        os.environ["SLM_PROJECT"] = sp._slm_prj
    os.environ["SLM_SUBPROJECT"] = sp._slm_sp

    # prep args
    cmd = [
        "slm",
        "create-report",
        f"--scan_id={sp._slm_scan_id}",
        f"--report_path={os.path.join(reportFolder, reportFilename)}",
        f"--report_format=xlsx",
    ]

    # run the command
    cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    # was it successful?
    if cp.returncode != 0:
        print(f"""{prj._name}/{sp._name}: XLSX report creation failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        return False

    # success!
    print(f"{prj._name}/{sp._name}: created xlsx report")

    # also create JSON report
    cmd = [
        "slm",
        "create-report",
        f"--scan_id={sp._slm_scan_id}",
        f"--report_path={os.path.join(reportFolder, jsonFilename)}",
        f"--report_format=json",
    ]
    cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if cp.returncode != 0:
        print(f"""{prj._name}/{sp._name}: JSON report creation failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        return False
    print(f"{prj._name}/{sp._name}: created json report")

    # once we get here, the report has been created
    sp._status = Status.CREATEDREPORTS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects --
    # AFTER taking into account creating a combined report, if needed
    return True

def getScanIdsString(cfg, prj):
    ids_set = set()
    min_id = 999999999999
    max_id = 0
    for sp in prj._subprojects.values():
        if sp._status.value >= Status.CREATEDREPORTS.value and sp._status != Status.STOPPED:
            ids_set.add(sp._slm_scan_id)
            if min_id > sp._slm_scan_id:
                min_id = sp._slm_scan_id
            if max_id < sp._slm_scan_id:
                max_id = sp._slm_scan_id
    
    # if just one ID, return it
    if len(ids_set) == 1:
        return f"{min_id}"
    
    ids = sorted(list(ids_set))

    # if more than one, see if we can combine them into a range
    # check if length is the same
    num_wanted = (max_id - min_id) + 1
    if num_wanted == len(ids):
        # walk through them and see if they totally fill the range
        good = True
        i = min_id
        for thisId in ids:
            if i != thisId:
                good = False
                break
            i = i + 1
        if good == True:
            # yup, it's a range
            return f"{min_id}-{max_id}"
    
    # it's not just a simple range, so let's just return all of them
    # as separate entries
    return ','.join(str(x) for x in ids)

def doCreateReportForProject(cfg, prj):
    # make sure we're at the right stage
    if prj._status != Status.IMPORTEDSCAN:
        print(f"{prj._name}: status is {prj._status}, won't create combined report now")
        return False

    # set report path
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    reportFilename = f"{prj._name}-{cfg._month}.xlsx"
    jsonFilename = f"{prj._name}-{cfg._month}.json"

    # create report directory for project if it doesn't already exist
    if not os.path.exists(reportFolder):
        os.makedirs(reportFolder)

    # set up environment variables
    os.environ["SLM_HOME"] = cfg._slm_home
    if prj._slm_shared == True:
        os.environ["SLM_PROJECT"] = prj._slm_prj
    else:
        print(f"{prj._name}: this is not an slm shared repo, won't create combined report")
        return False

    # gather scan IDs string
    scan_ids_string = getScanIdsString(cfg, prj)

    # prep args
    cmd = [
        "slm",
        "create-report",
        f"--scan_ids={scan_ids_string}",
        f"--report_path={os.path.join(reportFolder, reportFilename)}",
        f"--report_format=xlsx",
    ]

    # run the command
    cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    # was it successful?
    if cp.returncode != 0:
        print(f"""{prj._name}: report creation failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        return False

    # success!
    print(f"{prj._name}: created xlsx report")

    # also create JSON report
    cmd = [
        "slm",
        "create-report",
        f"--scan_ids={scan_ids_string}",
        f"--report_path={os.path.join(reportFolder, jsonFilename)}",
        f"--report_format=json",
    ]
    cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    # was it successful?
    if cp.returncode != 0:
        print(f"""{prj._name}: JSON report creation failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        return False
    print(f"{prj._name}: created json report")

    # once we get here, the project combined report has been created
    prj._status = Status.CREATEDREPORTS

    return True
