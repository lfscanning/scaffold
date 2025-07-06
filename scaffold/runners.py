# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
import os
import sys
from pathlib import Path
import shutil

from scaffold.config import saveConfig, updateProjectStatusToSubprojectMin, isInThisCycle
from scaffold.datatypes import ProjectRepoType, Status, Subproject
from scaffold.repolisting import doRepoListingForProject, doRepoListingForGerritProject, doRepoListingForSubproject
from scaffold.getcode import doGetRepoCodeForSubproject, doGetRepoCodeForGerritSubproject
from scaffold.zipcode import doZipRepoCodeForSubproject, doZipRepoCodeForGerritSubproject
from scaffold.uploadws import doUploadWSForSubproject
from scaffold.uploadcode import doUploadCodeForProject, doUploadCodeForSubproject
from scaffold.runagents import doRunAgentsForSubproject
from scaffold.getspdx import doGetSPDXForSubproject
from scaffold.parsespdx import doParseSPDXForSubproject, doCreateCombinedSLMJSONForProject
from scaffold.createreports import doCreateReportForProject, doCreateReportForSubproject
from scaffold.findings import doMakeDraftFindingsIfNoneForSubproject, doMakeFinalFindingsForSubproject, doMakeDraftFindingsIfNoneForProject, doMakeFinalFindingsForProject
from scaffold.approving import doApprove
from scaffold.uploadspdx import doUploadSPDXForSubproject
from scaffold.uploadreport import doUploadReportsForSubproject, doUploadReportsForProject
from scaffold.tickets import doFileTicketsForSubproject

def doNextThing(scaffold_home, cfg, fossologyServer, prj_only, sp_only):
    for prj in cfg._projects.values():
        if prj_only == "" or prj_only == prj._name:
            if isInThisCycle(cfg, prj, None):
                retval = True
                while retval:
                    retval = doNextThingForProject(scaffold_home, cfg, fossologyServer, prj, sp_only)
            else:
                print(f"{prj._name}: not in this cycle; skipping")

# Tries to do the next thing for this project. Returns True if
# accomplished something (meaning that we could call this again
# and possibly do the next-next thing), or False if accomplished
# nothing (meaning that we probably need to intervene).
def doNextThingForProject(scaffold_home, cfg, fossologyServer, prj, sp_only):
    if not isInThisCycle(cfg, prj, None):
        print(f"{prj._name}: not in this cycle; skipping")
        return False
    # if GitHub project, go to subprojects
    if prj._repotype == ProjectRepoType.GITHUB:
        did_something = False
        for sp in prj._subprojects.values():
            if sp_only == "" or sp_only == sp._name:
                retval = True
                while retval:
                    retval = doNextThingForSubproject(scaffold_home, cfg, fossologyServer, prj, sp)
                    updateProjectPostSubproject(cfg, prj)
                    saveConfig(scaffold_home, cfg)
                    if retval:
                        did_something = True
        return did_something

    # if GITHUB_SHARED project, check state to decide when to go to subprojects
    elif prj._repotype == ProjectRepoType.GITHUB_SHARED:
        did_something = False
        retval_prj = True
        while retval_prj:
            if prj._status == Status.START:
                # get repo listing at project level and see if we're good
                retval_prj = doRepoListingForProject(cfg, prj)
                saveConfig(scaffold_home, cfg)
                if retval_prj:
                    did_something = True
            # elif prj._status == Status.GOTCODE:
            #     # upload code to Fossology server
            #     retval_prj = doUploadCodeForProject(cfg, fossologyServer, prj)
            #     updateProjectStatusToSubprojectMin(cfg, prj)
            #     saveConfig(scaffold_home, cfg)
            #     if retval_prj:
            #         did_something = True
            else:
                retval_sp_all = False
                for sp in prj._subprojects.values():
                    if sp_only == "" or sp_only == sp._name:
                        retval = True
                        while retval:
                            retval = doNextThingForSubproject(scaffold_home, cfg, fossologyServer, prj, sp)
                            updateProjectPostSubproject(cfg, prj)
                            saveConfig(scaffold_home, cfg)
                            if retval:
                                did_something = True
                                retval_sp_all = True
                if not retval_sp_all:
                    break
        return did_something

    elif prj._repotype == ProjectRepoType.GERRIT:
        did_something = False
        retval_prj = True
        while retval_prj:
            if prj._status == Status.START:
                # get repo listing at project level and see if we're good
                retval_prj = doRepoListingForGerritProject(cfg, prj)
                updateProjectStatusToSubprojectMin(cfg, prj)
                saveConfig(scaffold_home, cfg)
                if retval_prj:
                    did_something = True
            # elif prj._status == Status.GOTCODE:
            #     # upload code to Fossology server
            #     retval_prj = doUploadCodeForProject(cfg, fossologyServer, prj)
            #     updateProjectStatusToSubprojectMin(cfg, prj)
            #     saveConfig(scaffold_home, cfg)
            #     if retval_prj:
            #         did_something = True
            else:
                retval_sp_all = False
                for sp in prj._subprojects.values():
                    if sp_only == "" or sp_only == sp._name:
                        retval = True
                        while retval:
                            retval = doNextThingForGerritSubproject(scaffold_home, cfg, fossologyServer, prj, sp)
                            updateProjectPostSubproject(cfg, prj)
                            saveConfig(scaffold_home, cfg)
                            if retval:
                                did_something = True
                                retval_sp_all = True
                if not retval_sp_all:
                    break
        return did_something

    else:
        print(f"Invalid project repotype for {prj._name}: {prj._repotype}")
        return False

# Tries to do the next thing for this subproject. Returns True if
# accomplished something (meaning that we could call this again
# and possibly do the next-next thing), or False if accomplished
# nothing (meaning that we probably need to intervene).
def doNextThingForSubproject(scaffold_home, cfg, fossologyServer, prj, sp):
    if not isInThisCycle(cfg, prj, sp):
        print(f"{prj._name}/{sp._name}: not in this cycle; skipping")
        return False
    status = sp._status
    if status == Status.START:
        # get repo listing and see if we're good
        return doRepoListingForSubproject(cfg, prj, sp)
    elif status == Status.GOTLISTING:
        # get code
        return doGetRepoCodeForSubproject(cfg, prj, sp)
    elif status == Status.GOTCODE:
        # delete .git folder and zip code
        return doZipRepoCodeForSubproject(cfg, prj, sp)
    elif status == Status.ZIPPEDCODE:
        # upload to WhiteSource
        return doUploadWSForSubproject(cfg, prj, sp)
    elif status == Status.UPLOADEDWS:
        # upload code
        return doUploadCodeForSubproject(cfg, fossologyServer, prj, sp)
    elif status == Status.UPLOADEDCODE:
        # run agents
        return doRunAgentsForSubproject(cfg, fossologyServer, prj, sp)
    elif status == Status.RANAGENTS:
        # needs manual clearing
        print(f"{prj._name}/{sp._name}: status is RANAGENTS; clear in Fossology then run `clear` action")
        return False
    elif status == Status.CLEARED:
        # get SPDX tag-value file
        return doGetSPDXForSubproject(cfg, fossologyServer, prj, sp)
    elif status == Status.GOTSPDX:
        # parse SPDX tag-value file
        return doParseSPDXForSubproject(cfg, prj, sp)
    elif status == Status.PARSEDSPDX:
        # create report for subproject
        return doCreateReportForSubproject(cfg, prj, sp)
    elif status == Status.CREATEDREPORTS or status == Status.MADEDRAFTFINDINGS:
        # create draft of findings report for subproject, if none yet
        return doMakeDraftFindingsIfNoneForSubproject(cfg, prj, sp)
    elif status == Status.APPROVEDFINDINGS:
        # create final draft of findings report for subproject
        return doMakeFinalFindingsForSubproject(cfg, prj, sp)
    elif status == Status.MADEFINALFINDINGS:
        # upload SPDX file to GitHub org
        return doUploadSPDXForSubproject(cfg, prj, sp)
    elif status == Status.UPLOADEDSPDX:
        # upload findings report to unique URL
        return doUploadReportsForSubproject(cfg, prj, sp)
    elif status == Status.UPLOADEDREPORTS:
        # file and update tickets for instances, if using ticket tracker
        return doFileTicketsForSubproject(cfg, prj, sp)
    elif status == Status.FILEDTICKETS:
        # needs manual delivering
        print(f"{prj._name}/{sp._name}: status is FILEDTICKETS; deliver report then run `deliver` action")
        return False
    elif status == Status.DELIVERED:
        # we are done
        return False
    elif status == Status.STOPPED:
        # we aren't going any further
        return False

    else:
        return False


# Tries to do the next thing for this Gerrit subproject. Returns True if
# accomplished something (meaning that we could call this again and possibly do
# the next-next thing), or False if accomplished nothing (meaning that we
# probably need to intervene). Does not handle START case because that is
# handled at the project level.
def doNextThingForGerritSubproject(scaffold_home, cfg, fossologyServer, prj, sp):
    if not isInThisCycle(cfg, prj, sp):
        print(f"{prj._name}/{sp._name}: not in this cycle; skipping")
        return False
    status = sp._status
    if status == Status.GOTLISTING:
        # get code
        return doGetRepoCodeForGerritSubproject(cfg, prj, sp)
    elif status == Status.GOTCODE:
        # delete .git folder and zip code
        return doZipRepoCodeForGerritSubproject(cfg, prj, sp)
    elif status == Status.ZIPPEDCODE:
        # upload to WhiteSource
        return doUploadWSForSubproject(cfg, prj, sp)
    elif status == Status.UPLOADEDWS:
        # upload code
        return doUploadCodeForSubproject(cfg, fossologyServer, prj, sp)
    elif status == Status.UPLOADEDCODE:
        # run agents
        return doRunAgentsForSubproject(cfg, fossologyServer, prj, sp)
    elif status == Status.RANAGENTS:
        # needs manual clearing
        print(f"{prj._name}/{sp._name}: status is RANAGENTS; clear in Fossology then run `clear` action")
        return False
    elif status == Status.CLEARED:
        # get SPDX tag-value file
        return doGetSPDXForSubproject(cfg, fossologyServer, prj, sp)
    elif status == Status.GOTSPDX:
        # parse SPDX tag-value file
        return doParseSPDXForSubproject(cfg, prj, sp)
    elif status == Status.PARSEDSPDX:
        # create report for subproject
        return doCreateReportForSubproject(cfg, prj, sp)
    elif status == Status.CREATEDREPORTS or status == Status.MADEDRAFTFINDINGS:
        # create draft of findings report for subproject, if none yet
        return doMakeDraftFindingsIfNoneForSubproject(cfg, prj, sp)
    elif status == Status.APPROVEDFINDINGS:
        # create final draft of findings report for subproject
        return doMakeFinalFindingsForSubproject(cfg, prj, sp)
    elif status == Status.MADEFINALFINDINGS:
        # upload SPDX file to GitHub org
        return doUploadSPDXForSubproject(cfg, prj, sp)
    elif status == Status.UPLOADEDSPDX:
        # upload findings report to unique URL
        return doUploadReportsForSubproject(cfg, prj, sp)
    elif status == Status.UPLOADEDREPORTS:
        # file and update tickets for instances, if using ticket tracker
        return doFileTicketsForSubproject(cfg, prj, sp)
    elif status == Status.FILEDTICKETS:
        # needs manual delivering
        print(f"{prj._name}/{sp._name}: status is FILEDTICKETS; deliver report then run `deliver` action")
        return False
    elif status == Status.DELIVERED:
        # we are done
        return False
    elif status == Status.STOPPED:
        # we aren't going any further
        return False

    else:
        return False

# For some steps, after all subprojects have reached a particular
# point, sometimes a step needs to be taken at the project level
# before the status is advanced. This includes (if appropriate)
# advancing the status of the project.
def updateProjectPostSubproject(cfg, prj):
    # if all subprojects have either parsed SPDX into JSON or are
    # stopped, then we should check whether we need to prepare
    # a combined project JSON as well
    if prj._slm_combined_report == True and prj._status == Status.GOTSPDX:
        readyForJSON = True
        for sp in prj._subprojects.values():
            if sp._status.value < Status.PARSEDSPDX.value:
                readyForJSON = False
                break
        if readyForJSON:
            # try to build the report, and exit without updating
            # status if we fail
            retval = doCreateCombinedSLMJSONForProject(cfg, prj)
            if retval == False:
                return

    # if all subprojects have either created reports or are
    # stopped, then we should check whether we need to create
    # a combined project report as well
    if prj._slm_combined_report == True and prj._status == Status.PARSEDSPDX:
        readyForReport = True
        for sp in prj._subprojects.values():
            if sp._status.value < Status.CREATEDREPORTS.value:
                readyForReport = False
                break
        if readyForReport:
            # try to build the report, and exit without updating
            # status if we fail
            retval = doCreateReportForProject(cfg, prj)
            if retval == False:
                return

    # if all subprojects have either created draft findings or
    # are stopped, then we should check whether we need to create
    # combined draft project findings as well
    elif prj._slm_combined_report == True and (prj._status == Status.CREATEDREPORTS or prj._status == Status.MADEDRAFTFINDINGS):
        readyForDraftFindings = True
        for sp in prj._subprojects.values():
            if sp._status.value < Status.MADEDRAFTFINDINGS.value:
                readyForDraftFindings = False
                break
        if readyForDraftFindings:
            # try to build the report, and exit without updating
            # status if we fail
            retval = doMakeDraftFindingsIfNoneForProject(cfg, prj)
            if retval == False:
                return

    # if all subprojects have either created final findings or
    # are stopped, then we should check whether we need to create
    # combined final project findings as well
    elif prj._slm_combined_report == True and prj._status == Status.APPROVEDFINDINGS:
        readyForFinalFindings = True
        for sp in prj._subprojects.values():
            if sp._status.value < Status.MADEFINALFINDINGS.value:
                readyForFinalFindings = False
                break
        if readyForFinalFindings:
            # try to build the report, and exit without updating
            # status if we fail
            retval = doMakeFinalFindingsForProject(cfg, prj)
            if retval == False:
                return

    # if all subprojects have finished uploading their reports or
    # are stopped, then we should check whether we need to upload
    # project-wide findings as well
    elif prj._slm_combined_report == True and prj._status == Status.UPLOADEDSPDX:
        readyForUpload = True
        for sp in prj._subprojects.values():
            if sp._status.value < Status.UPLOADEDREPORTS.value:
                readyForUpload = False
                break
        if readyForUpload:
            # try to upload the report, and exit without updating
            # status if we fail
            retval = doUploadReportsForProject(cfg, prj)
            if retval == False:
                return

    # and, if appropriate, advance the status of the project to
    # be the minimum of all its subprojects
    updateProjectStatusToSubprojectMin(cfg, prj)
