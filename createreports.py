# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from datatypes import Status
from slmjson import loadSLMCategories
from slm.xlsx import makeXlsx, saveXlsx

def doCreateReportForSubproject(cfg, prj, sp):
    # make sure we're at the right stage
    if sp._status != Status.PARSEDSPDX:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't create report now")
        return False

    # set report path
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    reportFilename = f"{sp._name}-{sp._code_pulled}.xlsx"
    reportPath = os.path.join(reportFolder, reportFilename)
    jsonFilename = f"{sp._name}-{sp._code_pulled}.json"
    jsonPath = os.path.join(reportFolder, jsonFilename)

    # create report directory for project if it doesn't already exist
    if not os.path.exists(reportFolder):
        os.makedirs(reportFolder)

    # load JSON license scan results
    categories = loadSLMCategories(prj, sp, jsonPath)

    # generate the workbook
    wb = makeXlsx(categories)

    # was it successful?
    if wb is None:
        print(f"{prj._name}/{sp._name}: XLSX report creation failed")
        return False

    # save the workbook
    retval = saveXlsx(wb, reportPath)
    if retval is None:
        print(f"{prj._name}/{sp._name}: error saving XLSX report to disk")
        return False

    # success!
    sp._slm_report_xlsx = reportPath
    print(f"{prj._name}/{sp._name}: created xlsx report")

    # once we get here, the report has been created
    sp._status = Status.CREATEDREPORTS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects --
    # AFTER taking into account creating a combined report, if needed
    return True

def doCreateReportForProject(cfg, prj):
    # make sure we're at the right stage
    if prj._status != Status.PARSEDSPDX:
        print(f"{prj._name}: status is {prj._status}, won't create combined report now")
        return False

    # set report path
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    reportFilename = f"{prj._name}-{cfg._month}.xlsx"
    reportPath = os.path.join(reportFolder, reportFilename)
    jsonFilename = f"{prj._name}-{cfg._month}.json"
    jsonPath = os.path.join(reportFolder, jsonFilename)

    # create report directory for project if it doesn't already exist
    if not os.path.exists(reportFolder):
        os.makedirs(reportFolder)

    # load JSON license scan results for combined project data
    categories = loadSLMCategories(prj, None, jsonPath)

    # generate the workbook
    wb = makeXlsx(categories)

    # was it successful?
    if wb is None:
        print(f"{prj._name}/COMBINED: XLSX report creation failed")
        return False

    # save the workbook
    retval = saveXlsx(wb, reportPath)
    if retval is None:
        print(f"{prj._name}/COMBINED: error saving XLSX report to disk")
        return False

    # success!
    print(f"{prj._name}/COMBINED: created xlsx report")

    # once we get here, the project combined report has been created
    prj._status = Status.CREATEDREPORTS

    return True
