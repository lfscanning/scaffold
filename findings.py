# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import glob
import json
import os

from jinja2 import Template

from datatypes import Instance, Priority, Status, InstanceSet
from datefuncs import getYMStr, parseYM, priorMonth
from instancesfile import loadInstances, saveInstances

# Helper for calculating findings instances and review categories
# Call with spName == "COMBINED" for combined report (should only
#   be used in print statements anyway)
# Returns InstanceSet for instance findings
# Returns None if no findings templates or other error
def analyzeFindingsInstances(cfg, prj, spName, slmJsonFilename):
    instances = []
    needReview = []

    # confirm whether this project has any findings templates
    if prj._findings == []:
        print(f'{prj._name}/{spName}: No findings template, skipping analysis')
        return None

    # get SLM JSON analysis details
    catLicFiles = loadSLMJSON(slmJsonFilename)
    if catLicFiles == []:
        print(f'{prj._name}/{spName}: Could not get any SLM category/license/file results; bailing')
        return None

    # walk through each finding template, and determine whether it has any instances
    # for this subproject
    for fi in prj._findings:
        inst = Instance()
        foundAny = False

        # for now, skip over subproject-only findings
        if fi._matches_subproject != [] and fi._matches_path == [] and fi._matches_license == []:
            continue

        # for this finding template, walk through each cat/lic/file tuple and see whether it applies
        for catName, licName, fileName in catLicFiles:
            matchesSubproject = False
            matchesPath = False
            matchesLic = False
            failedMatch = False

            # if the finding requires a subproject match, does it (contains) match any?
            if fi._matches_subproject != []:
                # requires subproject match, so check each one
                for p in fi._matches_subproject:
                    if p in fileName:
                        matchesSubproject = True
                if not matchesSubproject:
                    # failed the subproject match, so go on to the next lic/file pair
                    failedMatch = True

            # if the finding requires a path match, does it (contains) match any?
            if fi._matches_path != []:
                # requires path match, so check each one
                for p in fi._matches_path:
                    if p in fileName:
                        matchesPath = True
                if not matchesPath:
                    # failed the path match, so go on to the next lic/file pair
                    failedMatch = True

            # if the finding requires a license match, does it (exactly) match any?
            if fi._matches_license != []:
                # requires license match, so check each one
                for l in fi._matches_license:
                    if l == licName:
                        matchesLic = True
                if not matchesLic:
                    # failed the license match, so go on to the next lic/file pair
                    failedMatch = True

            # check whether it's a match
            if not failedMatch:
                # it's a match!
                if foundAny:
                    # this is a repeat finding, so just add our file to the existing one
                    inst._files.append(fileName)
                else:
                    # this is the first one for this instance, so initialize it
                    inst._finding_id = fi._id
                    # we'll add a "priority" field so it can be used to sort below
                    # FIXME this isn't ideal, might be a way to pull priority during the sort
                    inst._priority = fi._priority
                    inst._files = [fileName]
                    foundAny = True

        # done with lic/file pairs, so add this instance if we found any files
        if foundAny:
            instances.append(inst)

    # now, walk back through the category / license / files list again. for the
    # flagged categories, if a file is listed and is NOT in any instance, add it to
    # the review list
    for catName, licName, fileName in catLicFiles:
        found = False
        if catName in prj._flag_categories:
            # check if this file is in any instance
            for inst in instances:
                if fileName in inst._files:
                    found = True
            if not found:
                # it wasn't, so add it to the review list
                clf = [catName, licName, fileName]
                needReview.append(clf)
    
    # also, if there are any matches which list a subproject and NEITHER paths
    # nor licenses, then make sure we add that one for the subproject, if
    # applies to this subproject
    for fi in prj._findings:
        if fi._matches_subproject != [] and fi._matches_path == [] and fi._matches_license == [] and (spName == "COMBINED" or spName in fi._matches_subproject):
            inst = Instance()
            inst._finding_id = fi._id
            # we'll add a "priority" field so it can be used to sort below
            # FIXME this isn't ideal, might be a way to pull priority during the sort
            inst._priority = fi._priority
            if spName == "COMBINED":
                inst._subprojects = fi._matches_subproject
            instances.append(inst)

    # finally, sort instances by finding priority
    instances.sort(key=lambda inst: inst._priority.value, reverse=True)

    instSet = InstanceSet()
    instSet._flagged = instances
    instSet._unflagged = needReview

    return instSet

# Helper to find prior month's instances file, load it, and return the instances set.
# FIXME rather than glob searching, really we should probably look at the prior month's
# FIXME config file and pull out the specific file that we want.
def getPriorInstancesSet(cfg, prj, spName):
    curYear, curMonth = parseYM(cfg._month)
    pYear, pMonth = priorMonth(curYear, curMonth)
    priorYM = getYMStr(pYear, pMonth)
    priorReportFolder = os.path.join(cfg._storepath, priorYM, "report", prj._name)
    # search for file with the right prefix and extension
    if spName == "COMBINED":
        wantFile = f"{prj._name}-instances-{priorYM}.json"
    else:
        wantFile = f"{spName}-instances-{priorYM}-??.json"
    filenames = glob.glob(os.path.join(priorReportFolder, wantFile))
    filenames.sort()
    if len(filenames) == 0:
        return None

    # FIXME if multiple are present, we'll use the first one
    return loadInstances(filenames[0])

# Helper to load prior month's instances, compare what we've got, and annotate them.
def comparePriorInstances(cfg, prj, spName, currentInstanceSet):
    # load prior month's instances, if any
    priorInstanceSet = getPriorInstancesSet(cfg, prj, spName)
    if priorInstanceSet is None:
        print(f"{prj._name}/{spName}: no instances file found for prior month")
        # flag all as new
        for inst in currentInstanceSet._flagged:
            inst._first = cfg._month
            inst._isnew = True
            inst._jira_id = ""
        return

    # create lookup table for last month's instances
    priorInstancesDict = {}
    for pi in priorInstanceSet._flagged:
        priorInstancesDict[pi._finding_id] = pi

    # now, walk through each current instance, determining whether it is new
    # (and, if it isn't, filling in prior details)
    pi = None
    for ci in currentInstanceSet._flagged:
        pi = priorInstancesDict.get(ci._finding_id, None)
        if pi is None:
            ci._first = cfg._month
            ci._isnew = True
            ci._jira_id = ""
        else:
            ci._first = pi._first
            ci._isnew = False
            ci._files_changed = (sorted(pi._files) != sorted(ci._files))
            ci._jira_id = pi._jira_id

# Helper for calculating category/license summary file counts.
# Returns (cats, totalCount, noLicThird, noLicEmpty, noLicExt) tuple
#   cats = (name, list of (lics, catTotalCount) tuples)
#     lics = list of (license, licCount) tuples
#   totalCount = total number of files overall
#   noLicThird = total "No license found" files in third-party dirs
#   noLicEmpty = total "No license found" empty files (prefers noLicThird)
#   noLicExt   = total "No license found" files with "ignore" extensions
#                  (prefers noLicExt)
#   noLicRest  = total "No license found" not falling into other categories
# Zero count lics / cats are ignored and not returned.
def getLicenseSummaryDetails(cfg, slmJsonFilename):
    cats = []
    totalCount = 0
    noLicThird = 0
    noLicEmpty = 0
    noLicExt = 0
    noLicRest = 0

    # walk through SLM JSON file and prepare summary count details
    try:
        with open(slmJsonFilename, "r") as f:
            # not using "get" below b/c we want it to crash if JSON is malformed
            # should be array of category objects
            cat_arr = json.load(f)
            for cat_dict in cat_arr:
                cat_numFiles = cat_dict["numFiles"]
                # ignore categories with no files
                if cat_numFiles == 0:
                    continue
                totalCount += cat_numFiles
                cat_name = cat_dict["name"]
                # get licenses and file counts
                lics = []
                for lic_dict in cat_dict["licenses"]:
                    lic_numFiles = lic_dict["numFiles"]
                    # ignore licenses with no files
                    if lic_numFiles == 0:
                        continue
                    lic = (lic_dict["name"], lic_numFiles)
                    lics.append(lic)
                    # also do further processing if this is "No license found"
                    if lic_dict["name"] == "No license found":
                        for file_dict in lic_dict["files"]:
                            findings_dict = file_dict.get("findings", {})
                            if findings_dict.get("thirdparty", "no") == "yes":
                                noLicThird += 1
                                continue
                            if findings_dict.get("emptyfile", "no") == "yes":
                                noLicEmpty += 1
                                continue
                            if findings_dict.get("extension", "no") == "yes":
                                noLicExt += 1
                                continue
                            noLicRest += 1
                # add these licenses to the cats array
                cat = (cat_name, lics, cat_numFiles)
                cats.append(cat)

        return (cats, totalCount, noLicThird, noLicEmpty, noLicExt, noLicRest)

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {slmJsonFilename}: {str(e)}')
        return []

# Helper to load SLM JSON document, and return a list of (category, license, filename) tuples
def loadSLMJSON(slmJsonFilename):
    catLicFiles = []
    try:
        with open(slmJsonFilename, "r") as f:
            # not using "get" below b/c we want it to crash if JSON is malformed
            # should be array of category objects
            cat_arr = json.load(f)
            for cat_dict in cat_arr:
                cat_name = cat_dict["name"]
                # contains array of license objects
                lic_arr = cat_dict["licenses"]
                for lic_dict in lic_arr:
                    # contains license name and array of file objects
                    lic_name = lic_dict["name"]
                    file_arr = lic_dict["files"]
                    for file_dict in file_arr:
                        # contains file path in path key
                        file_name = file_dict["path"]
                        cfl_tup = (cat_name, lic_name, file_name)
                        catLicFiles.append(cfl_tup)
        catLicFiles.sort(key=lambda tup: (tup[0], tup[1], tup[2]))
        return catLicFiles
    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {slmJsonFilename}: {str(e)}')
        return []

def getShortPriorityString(p):
    if p == Priority.VERYHIGH:
        return "veryhigh"
    elif p == Priority.HIGH:
        return "high"
    elif p == Priority.MEDIUM:
        return "medium"
    elif p == Priority.LOW:
        return "low"
    else:
        return "unknown"
    
def getFullPriorityString(p):
    if p == Priority.VERYHIGH:
        return "Very High"
    elif p == Priority.HIGH:
        return "High"
    elif p == Priority.MEDIUM:
        return "Medium"
    elif p == Priority.LOW:
        return "Low"
    else:
        return "Unspecified"


# Helper to extract a particular Finding by ID.
def getFindingByID(prj, finding_id):
    for f in prj._findings:
        if finding_id == f._id:
            return f
    return None

# Helper for creating subproject findings document, whether draft or final
# Returns path to findings report (or "" if not written) and path to
# review report (or "" if not written)
def makeFindingsForSubproject(cfg, prj, sp, isDraft, includeReview=True):
    reviewReportWrittenPath = ""

    # load template
    tmplstr = ""
    with open("templates/findings.html", "r") as tmpl_f:
        tmplstr = tmpl_f.read()

    # calculate paths; report folder would have been created in doCreateReport stage
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    instancesJsonFilename = f"{sp._name}-instances-{sp._code_pulled}.json"
    instancesJsonPath = os.path.join(reportFolder, instancesJsonFilename)
    slmJsonFilename = f"{sp._name}-{sp._code_pulled}.json"
    slmJsonPath = os.path.join(reportFolder, slmJsonFilename)
    if isDraft:
        htmlFilename = f"{sp._name}-{sp._code_pulled}-DRAFT.html"
    else:
        htmlFilename = f"{sp._name}-{sp._code_pulled}.html"
    htmlPath = os.path.join(reportFolder, htmlFilename)

    # if there's already a file at the location, needs to be deleted before we will proceed
    if os.path.exists(htmlPath):
        # print(f"{prj._name}/{sp._name}: run 'approve' action to finalize or delete existing report to re-run")
        return "", ""

    # get analysis results
    spInstances = analyzeFindingsInstances(cfg, prj, sp._name, slmJsonPath)

    # compare to prior month's instances and annotate instances with results
    comparePriorInstances(cfg, prj, sp._name, spInstances)

    # save instances to disk
    saveInstances(instancesJsonPath, spInstances)

    # if no instances, that's fine, we'll still want to create the report

    # get license summary data
    cats, totalCount, noLicThird, noLicEmpty, noLicExt, noLicRest = getLicenseSummaryDetails(cfg, slmJsonPath)

    # build template data fillers
    repoData = []
    for repoName, commit in sp._code_repos.items():
        rdTup = (repoName, commit[0:8])
        repoData.append(rdTup)
    repoData.sort(key=lambda tup: tup[0])

    findingData = []
    for inst in spInstances._flagged:
        finding = getFindingByID(prj, inst._finding_id)
        fd = {
            "findingID": finding._id,
            "priorityShort": getShortPriorityString(finding._priority),
            "priorityFull": getFullPriorityString(finding._priority),
            "description": finding._text,
            "numFiles": len(inst._files),
            "files": inst._files,
            "subprojects": inst._subprojects,
        }
        findingData.append(fd)

    renderData = {
        "prjName": prj._name,
        "spName": sp._name,
        "codeDate": sp._code_pulled,
        "repoData": repoData,
        "findingData": findingData,
        "licenseSummary": {
            "cats": cats,
            "totalCount": totalCount,
            "noLicThird": noLicThird,
            "noLicEmpty": noLicEmpty,
            "noLicExt": noLicExt,
            "noLicRest": noLicRest,
        },
    }

    # and render it!
    tmpl = Template(tmplstr)
    renderedHtml = tmpl.render(renderData)

    # and write the results to disk
    with open(htmlPath, "w") as report_f:
        report_f.write(renderedHtml)
    
    if isDraft:
        print(f"{prj._name}/{sp._name}: DRAFT findings written to {htmlFilename}")
    else:
        print(f"{prj._name}/{sp._name}: FINAL findings written to {htmlFilename}")

    return htmlPath, reviewReportWrittenPath

# Helper for creating project findings document, whether draft or final
# Returns path to findings report (or "" if not written) and path to
# review report (or "" if not written)
def makeFindingsForProject(cfg, prj, isDraft, includeReview=True):
    reviewReportWrittenPath = ""

    # load template
    tmplstr = ""
    with open("templates/findings.html", "r") as tmpl_f:
        tmplstr = tmpl_f.read()

    # calculate paths; report folder would have been created in doCreateReport stage
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    instancesJsonFilename = f"{prj._name}-instances-{cfg._month}.json"
    instancesJsonPath = os.path.join(reportFolder, instancesJsonFilename)
    slmJsonFilename = f"{prj._name}-{cfg._month}.json"
    slmJsonPath = os.path.join(reportFolder, slmJsonFilename)
    if isDraft:
        htmlFilename = f"{prj._name}-{cfg._month}-DRAFT.html"
    else:
        htmlFilename = f"{prj._name}-{cfg._month}.html"
    htmlPath = os.path.join(reportFolder, htmlFilename)

    # if there's already a file at the location, needs to be deleted before we will proceed
    if os.path.exists(htmlPath):
        # print(f"{prj._name}: run 'approve' action to finalize or delete existing report to re-run")
        return "", ""

    # get analysis results
    prjInstances = analyzeFindingsInstances(cfg, prj, "COMBINED", slmJsonPath)

    # compare to prior month's instances and annotate instances with results
    comparePriorInstances(cfg, prj, "COMBINED", prjInstances)

    # save instances to disk
    saveInstances(instancesJsonPath, prjInstances)

    # if no instances, that's fine, we'll still want to create the report

    # get license summary data
    cats, totalCount, noLicThird, noLicEmpty, noLicExt, noLicRest = getLicenseSummaryDetails(cfg, slmJsonPath)

    # build template data fillers
    repoData = []
    for sp in prj._subprojects.values():
        for repoName, commit in sp._code_repos.items():
            rdTup = (repoName, commit[0:8])
            repoData.append(rdTup)
    repoData.sort(key=lambda tup: tup[0])

    findingData = []
    for inst in prjInstances._flagged:
        finding = getFindingByID(prj, inst._finding_id)
        fd = {
            "findingID": finding._id,
            "priorityShort": getShortPriorityString(finding._priority),
            "priorityFull": getFullPriorityString(finding._priority),
            "description": finding._text,
            "numFiles": len(inst._files),
            "files": inst._files,
            "numSubprojects": len(inst._subprojects),
            "subprojects": inst._subprojects,
        }
        findingData.append(fd)

    renderData = {
        "prjName": prj._name,
        "spName": "(all subprojects)",
        "codeDate": cfg._month,
        "repoData": repoData,
        "findingData": findingData,
        "licenseSummary": {
            "cats": cats,
            "totalCount": totalCount,
            "noLicThird": noLicThird,
            "noLicEmpty": noLicEmpty,
            "noLicExt": noLicExt,
            "noLicRest": noLicRest,
        },
    }

    # and render it!
    tmpl = Template(tmplstr)
    renderedHtml = tmpl.render(renderData)

    # and write the results to disk
    with open(htmlPath, "w") as report_f:
        report_f.write(renderedHtml)

    if isDraft:
        print(f"{prj._name}: DRAFT findings written to {htmlFilename}")
    else:
        print(f"{prj._name}: FINAL findings written to {htmlFilename}")

    return htmlPath, reviewReportWrittenPath

# Runner for CREATEDREPORTS and MADEDRAFTFINDINGS for one subproject
def doMakeDraftFindingsIfNoneForSubproject(cfg, prj, sp):
    orig_status = sp._status
    # make sure we're at the right stage
    if sp._status != Status.CREATEDREPORTS and sp._status != Status.MADEDRAFTFINDINGS:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't create draft findings now")
        return False

    # make findings report and the review file, if any
    findingsPath, _ = makeFindingsForSubproject(cfg, prj, sp, True, True)
    if findingsPath == "":
        # print(f"{prj._name}/{sp._name}: no draft findings report written")
        # only return false if it's the same as when we came in
        if orig_status == Status.MADEDRAFTFINDINGS:
            return False

    # once we get here, the draft findings report has been created, if there is one
    sp._status = Status.MADEDRAFTFINDINGS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects --
    # AFTER taking into account creating a combined report, if needed
    return True

# Runner for CREATEDREPORTS and MADEDRAFTFINDINGS for one project, overall
def doMakeDraftFindingsIfNoneForProject(cfg, prj):
    orig_status = prj._status
    # make sure we're at the right stage
    if prj._status != Status.CREATEDREPORTS and prj._status != Status.MADEDRAFTFINDINGS:
        print(f"{prj._name}: status is {prj._status}, won't create draft findings now")
        return False

    # make findings report and the review file, if any
    findingsPath, _ = makeFindingsForProject(cfg, prj, True, True)
    if findingsPath == "":
        # print(f"{prj._name}: no draft findings report written")
        # only return false if it's the same as when we came in
        if orig_status == Status.MADEDRAFTFINDINGS:
            return False

    # once we get here, the draft findings report has been created, if there is one
    prj._status = Status.MADEDRAFTFINDINGS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects --
    # AFTER taking into account creating a combined report, if needed
    return True

# Runner for APPROVEDFINDINGS for one subproject
def doMakeFinalFindingsForSubproject(cfg, prj, sp):
    orig_status = sp._status
    # make sure we're at the right stage
    if sp._status != Status.APPROVEDFINDINGS:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't create final findings now")
        return False

    # make findings report and the review file, if any
    findingsPath, _ = makeFindingsForSubproject(cfg, prj, sp, False, True)
    if findingsPath == "":
        print(f"{prj._name}/{sp._name}: no final findings report written")
        # only return false if it's the same as when we came in
        # FIXME is this incorrect? since it needs to be APPROVEDFINDINGS
        # FIXME to get here?
        if orig_status == Status.MADEDRAFTFINDINGS:
            return False

    # once we get here, the final findings report has been created, if there is one
    sp._status = Status.MADEFINALFINDINGS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects --
    # AFTER taking into account creating a combined report, if needed
    return True

# Runner for APPROVEDFINDINGS for one project overall
def doMakeFinalFindingsForProject(cfg, prj):
    orig_status = prj._status
    # make sure we're at the right stage
    if prj._status != Status.APPROVEDFINDINGS:
        print(f"{prj._name}: status is {prj._status}, won't create final findings now")
        return False

    # make findings report and the review file, if any
    findingsPath, _ = makeFindingsForProject(cfg, prj, False, True)
    if findingsPath == "":
        print(f"{prj._name}: no final findings report written")
        # only return false if it's the same as when we came in
        # FIXME is this incorrect? since it needs to be APPROVEDFINDINGS
        # FIXME to get here?
        if orig_status == Status.MADEDRAFTFINDINGS:
            return False

    # once we get here, the final findings report has been created, if there is one
    prj._status = Status.MADEFINALFINDINGS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects --
    # AFTER taking into account creating a combined report, if needed
    return True
