# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from scaffold.datatypes import Status
from scaffold.datefuncs import getTextYM

def printEmail(cfg, prj_only="", sp_only=""):
    if prj_only == "":
        print(f"Error: `printemail` command requires specifying only one project (and optionally only one subproject)")
        return False

    # make sure we're at the right stage
    prj = cfg._projects.get(prj_only, None)
    if not prj:
        print(f"{prj_only}: Project not found in config")
        return False

    ran_command = False
    for sp in prj._subprojects.values():
        if sp_only == "" or sp_only == sp._name:
            if sp._status == Status.FILEDTICKETS:
                printEmailForSubproject(cfg, prj, sp)
                ran_command = True
            elif sp._status == Status.DELIVERED:
                print(f"{prj._name}/{sp._name}: reports already delivered")
            else:
                print(f"{prj._name}/{sp._name}: need to upload reports / file tickets before printing email")

    return ran_command

def printEmailForSubproject(cfg, prj, sp):
    spdxRepoName = f"spdx-{prj._name}"

    ym = getTextYM(cfg._month)
    if ym is None:
        subject_line = f"{sp._name} license scan report"
    else:
        subject_line = f"{sp._name} license scan report, {getTextYM(cfg._month)}"

    if sp._web_html_url == "":
        findings_line = "No significant findings or action items were detected in the scan."
    else:
        findings_line = f"The key findings and action items are available at: {sp._web_html_url}"

    print(f"********************")
    print(f"*** {prj._name} / {sp._name}")
    print(f"********************\n")

    print(f"Subject: {subject_line}\n")

    print(f"""Text:
A license scan and analysis has been completed for:

    Project: {prj._name}
    Subproject: {sp._name}

This scan is based on snapshots of the {sp._name} repos as of {sp._code_pulled}.

{findings_line}

A catalogue of the detected licenses, with a summary as well as per-file details, is available at: {sp._web_xlsx_url}

SPDX files generated from the license scans are available at: https://github.com/{cfg._spdx_github_org}/{spdxRepoName}. These SPDX files are provided for you and the broader project community, in the hopes that they may be useful for license compliance efforts when redistributing the project source code.

Please feel free to reach out to me with any questions.
""")

def printAllLinks(cfg, prj_only="", sp_only=""):
    if prj_only == "":
        print(f"Error: `printlinks` command requires specifying only one project (and optionally only one subproject)")
        return False

    # make sure we're at the right stage
    prj = cfg._projects.get(prj_only, None)
    if not prj:
        print(f"{prj_only}: Project not found in config")
        return False

    ran_command = False
    for sp in prj._subprojects.values():
        if sp_only == "" or sp_only == sp._name:
            if sp._status.value >= Status.FILEDTICKETS.value and sp._status != Status.STOPPED:
                printAllLinksForSubproject(cfg, prj, sp)
                ran_command = True
            elif sp._status != Status.STOPPED:
                print(f"{prj._name}/{sp._name}: need to upload reports / file tickets before printing links")

    # also print for main project if combined
    if sp_only == "" and prj._slm_combined_report == True:
        print(f"= = = = =")
        print(f"{prj._name} combined:")
        print(f"  - report: {prj._web_combined_html_url}")
        print(f"  - xlsx:   {prj._web_combined_xlsx_url}")
        print(f"")

    return ran_command

def printAllLinksForSubproject(cfg, prj, sp):
    spdxRepoName = f"spdx-{prj._name}"

    print(f"{prj._name}/{sp._name}, code pulled {sp._code_pulled}")
    print(f"  - report:      {sp._web_html_url}")
    print(f"  - xlsx:        {sp._web_xlsx_url}")
    print(f"  - spdx:        https://github.com/{cfg._spdx_github_org}/{spdxRepoName}/tree/master/{sp._name}/{cfg._month}")
    if sp._web_sbom_url:
        print(f"  - sbom xlsx:   {sp._web_sbom_url}")
        print(f"  - sbom json:   https://github.com/{cfg._spdx_github_org}/{spdxRepoName}/tree/master/{sp._name}/{cfg._month}")
    print(f"")

def printReportLinks(cfg, prj_only="", sp_only=""):
    if prj_only == "":
        print(f"Error: `printlinks` command requires specifying only one project (and optionally only one subproject)")
        return False

    # make sure we're at the right stage
    prj = cfg._projects.get(prj_only, None)
    if not prj:
        print(f"{prj_only}: Project not found in config")
        return False

    ran_command = False
    for sp in prj._subprojects.values():
        if sp_only == "" or sp_only == sp._name:
            if sp._status.value >= Status.FILEDTICKETS.value and sp._status != Status.STOPPED:
                print(f"{prj._name}/{sp._name}: {sp._web_html_url}")
                ran_command = True
            elif sp._status != Status.STOPPED:
                print(f"{prj._name}/{sp._name}: need to upload reports / file tickets before printing links")

    # also print for main project if combined
    if sp_only == "" and prj._slm_combined_report == True:
        print(f"= = = = =")
        print(f"{prj._name} combined: {prj._web_combined_html_url}")

    return ran_command
