# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os

from jira import JIRA
from jira.exceptions import JIRAError

from datatypes import Priority, Status, TicketType
from config import updateProjectStatusToSubprojectMin
from instancesfile import loadInstances, saveInstances

# Helper to extract a particular Finding by ID.
def getFindingByID(prj, finding_id):
    for f in prj._findings:
        if finding_id == f._id:
            return f
    return None

def doFileTicketsForSubproject(cfg, prj, sp):
    # check that we're at the right status
    if sp._status != Status.UPLOADEDREPORTS:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't file tickets now")
        return False

    # if this isn't a project that files tickets, just skip
    if prj._ticket_type == TicketType.NONE:
        print(f"{prj._name}/{sp._name}: no ticket tracking configured, skipping ticket filing")
        sp._status = Status.FILEDTICKETS
        return True

    # get connection details for this project
    jiraSecret = cfg._secrets._jira.get(prj._name, None)
    if jiraSecret is None:
        print(f"{prj._name}/{sp._name}: unable to retrieve Jira secret details; bailing")
        return False

    # connect to JIRA server
    jira = JIRA(server=jiraSecret._server, basic_auth=(jiraSecret._username, jiraSecret._password))

    # load current month's instances
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    instancesJsonFilename = f"{sp._name}-instances-{sp._code_pulled}.json"
    instancesJsonPath = os.path.join(reportFolder, instancesJsonFilename)
    instSet = loadInstances(instancesJsonPath)
    if instSet is None:
        print(f"{prj._name}/{sp._name}: unable to load instances from {instancesJsonPath}; bailing")
        return False

    # walk through current instances, either annotating if previous ticket existed or
    # creating new ticket otherwise
    for inst in instSet._flagged:
        fi = getFindingByID(prj, inst._finding_id)
        if fi is None:
            print(f"{prj._name}/{sp._name}: unable to get finding with ID {inst._finding_id}; skipping")
            continue

        if inst._isnew:
            # create new ticket
            summary = f"{sp._name}: {fi._title}"
            filelist = " * " + "\n * ".join(inst._files)
            description = f"""
{fi._text}

Files:
{filelist}

-----

Based on license scan of repo snapshot taken {sp._code_pulled}. Please contact Steve Winslow at [swinslow@linuxfoundation.org|mailto:swinslow@linuxfoundation.org] with any questions about the license scan findings.
"""
            if fi._priority == Priority.VERYHIGH:
                priority = "Highest"
            elif fi._priority == Priority.HIGH:
                priority = "High"
            elif fi._priority == Priority.MEDIUM:
                priority = "Medium"
            elif fi._priority == Priority.LOW:
                priority = "Low"
            else:
                priority = "Medium"

            new_issue = jira.create_issue(
                project=jiraSecret._jira_project,
                summary=summary,
                description=description,
                issuetype={'name': 'Task'},
                priority={"name": priority},
            )

            # save issue key in instance data
            inst._jira_id = new_issue.key
            print(f"{prj._name}/{sp._name}: created JIRA ticket {inst._jira_id} for finding instance ID {inst._finding_id}")

        else:
            if inst._jira_id == "":
                print(f"{prj._name}/{sp._name}: prior JIRA ID not listed for instance with ID {inst._finding_id}; skipping")
                continue
            try:
                issue = jira.issue(inst._jira_id)
            except JIRAError as e:
                print(f'Error retrieving issue {inst._jira_id} for instance with ID {inst._finding_id}: {str(e)}; skipping')
                continue

            if inst._files_changed:
                # add comment with updated file list
                filelist = " * " + "\n * ".join(inst._files)
                commentText = f"Update from license scan of repo snapshot taken {sp._code_pulled}: issue still detected; updated file list:\n{filelist}\n"
                jira.add_comment(issue, commentText)
                print(f"{prj._name}/{sp._name}: added update to JIRA ticket {inst._jira_id} for finding instance ID {inst._finding_id}")

            else:
                # add comment noting same files still detected
                commentText = f"Update from license scan of repo snapshot taken {sp._code_pulled}: issue still detected; file list unchanged\n"
                jira.add_comment(issue, commentText)
                print(f"{prj._name}/{sp._name}: added update to JIRA ticket {inst._jira_id} for finding instance ID {inst._finding_id}")

    # when we're done, save the instance data back to disk
    # since we've updated e.g. issue numbers
    saveInstances(instancesJsonPath, instSet)

    # once we get here, the spdx file has been uploaded
    sp._status = Status.FILEDTICKETS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
