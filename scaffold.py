# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from operator import itemgetter
import os
import sys

from tabulate import tabulate

from fossdriver.config import FossConfig
from fossdriver.server import FossServer

from config import loadConfig, saveBackupConfig, saveConfig
import datefuncs
from runners import doNextThing
from clearing import doCleared
from newmonth import copyToNextMonth
from approving import doApprove
from emailing import printEmail, printAllLinks, printReportLinks
from delivering import doDelivered
from metrics import getMetrics, printMetrics
from metricsfile import saveMetrics

def printUsage():
    print(f"""
Usage: {sys.argv[0]} <month> <command> [<project>] [<subproject>]
Month: in format YYYY-MM

Commands:

  Running:
    newmonth:   Begin a new month and reset status for all projects
    run:        Run next steps for all subprojects
    clear:      Flag cleared in Fossology for [sub]project
    approve:    Flag approved auto-generated findings in report for [sub]project
    deliver:    Flag delivered report for [sub]project

  Printing:
    status:           Print status for all subprojects
    printemail:       Print email with links to reports for [sub]project
    printlinks:       Print links to all reports for [sub]project
    printreportlinks: Print only findings link(s) for [sub]project

  Metrics:
    getmetrics:       Analyze and save metrics for overall current status to JSON file
    printmetrics:     Load and print metrics from JSON file

""")

def status(projects, prj_only, sp_only):
    headers = ["Project", "Subproject", "Status"]
    table = []

    for prj in projects.values():
        if prj_only == "" or prj_only == prj._name:
            row = [prj._name, "", prj._status.name]
            table.append(row)
            for sp in prj._subprojects.values():
                if sp_only == "" or sp_only == sp._name:
                    row = [prj._name, sp._name, sp._status.name]
                    table.append(row)

    table = sorted(table, key=itemgetter(0, 1))
    print(tabulate(table, headers=headers))

def fossdriverSetup():
    config = FossConfig()
    configPath = os.path.join(str(Path.home()), ".fossdriver", "fossdriverrc.json")
    retval = config.configure(configPath)
    if not retval:
        print(f"Error: Could not load config file from {configPath}")
        return False

    server = FossServer(config)
    server.Login()

    return server

# FIXME move this into secrets file
def githubOauthSetup():
    scaffoldrc = os.path.join(Path.home(), ".scaffoldrc")
    try:
        with open(scaffoldrc, "r") as f:
            js = json.load(f)
            return js.get("gh_oauth_token", "")

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {scaffoldrc}: {str(e)}')
        return ""

if __name__ == "__main__":
    # check and parse year-month
    if len(sys.argv) < 2:
        printUsage()
        sys.exit(1)
    year, month = datefuncs.parseYM(sys.argv[1])
    if year == 0 and month == 0:
        printUsage()
        sys.exit(1)

    # get github oauth token
    GITHUB_OAUTH = githubOauthSetup()

    # get scaffold home directory
    SCAFFOLD_HOME = os.getenv('SCAFFOLD_HOME')
    if SCAFFOLD_HOME == None:
        SCAFFOLD_HOME = os.path.join(Path.home(), "scaffold")
    MONTH_DIR = os.path.join(SCAFFOLD_HOME, datefuncs.getYMStr(year, month))

    ran_command = False

    # load configuration file for this month
    cfg_file = os.path.join(MONTH_DIR, "config.json")
    cfg = loadConfig(cfg_file, SCAFFOLD_HOME)
    cfg._gh_oauth_token = GITHUB_OAUTH

    # we'll check if added optional args limit to one prj / sp
    prj_only = ""
    sp_only = ""

    if len(sys.argv) >= 3:
        month = sys.argv[1]
        command = sys.argv[2]
        if len(sys.argv) >= 4:
            prj_only = sys.argv[3]
            if len(sys.argv) >= 5:
                sp_only = sys.argv[4]

        if command == "status":
            ran_command = True
            status(cfg._projects, prj_only, sp_only)

        elif command == "newmonth":
            ran_command = True
            copyToNextMonth(SCAFFOLD_HOME, cfg)

        elif command == "run":
            ran_command = True
            saveBackupConfig(SCAFFOLD_HOME, cfg)

            # set up fossdriver server connection
            fdServer = fossdriverSetup()
            if not fdServer:
                print(f"Unable to connect to Fossology server with fossdriver")
                sys.exit(1)

            # run commands
            doNextThing(SCAFFOLD_HOME, cfg, fdServer, prj_only, sp_only)

            # save modified config file
            saveConfig(SCAFFOLD_HOME, cfg)

        elif command == "clear":
            ran_command = True
            saveBackupConfig(SCAFFOLD_HOME, cfg)

            # clear if in RANAGENTS state
            doCleared(SCAFFOLD_HOME, cfg, prj_only, sp_only)

            # save config file, even if not modified (b/c saved backup)
            saveConfig(SCAFFOLD_HOME, cfg)

        elif command == "approve":
            ran_command = True
            saveBackupConfig(SCAFFOLD_HOME, cfg)

            # approve if in MADEDRAFTFINDINGS state
            doApprove(SCAFFOLD_HOME, cfg, prj_only, sp_only)

            # save config file, even if not modified (b/c saved backup)
            saveConfig(SCAFFOLD_HOME, cfg)

        elif command == "printemail":
            ran_command = True

            # print email details if in UPLOADEDREPORTS state
            printEmail(cfg, prj_only, sp_only)

        elif command == "printlinks":
            ran_command = True

            # print report link details if in UPLOADEDREPORTS state
            printAllLinks(cfg, prj_only, sp_only)

        elif command == "printreportlinks":
            ran_command = True

            # print report link details if in UPLOADEDREPORTS state
            printReportLinks(cfg, prj_only, sp_only)

        elif command == "deliver":
            ran_command = True
            saveBackupConfig(SCAFFOLD_HOME, cfg)

            # clear if in UPLOADEDSPDX state
            doDelivered(SCAFFOLD_HOME, cfg, prj_only, sp_only)

            # save config file, even if not modified (b/c saved backup)
            saveConfig(SCAFFOLD_HOME, cfg)

        elif command == "getmetrics":
            ran_command = True
            fdServer = fossdriverSetup()
            if not fdServer:
                print(f"Unable to connect to Fossology server with fossdriver")
                sys.exit(1)
            all_metrics = getMetrics(cfg, fdServer)

            metricsFilename = os.path.join(cfg._storepath, cfg._month, "metrics.json")
            saveMetrics(metricsFilename, all_metrics)

        elif command == "printmetrics":
            ran_command = True
            metricsFilename = os.path.join(cfg._storepath, cfg._month, "metrics.json")
            printMetrics(metricsFilename)

    if ran_command == False:
        printUsage()
        sys.exit(1)

