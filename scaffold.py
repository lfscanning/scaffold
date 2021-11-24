# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from operator import itemgetter
import os
import sys

from tabulate import tabulate

from fossdriver.config import FossConfig
from fossdriver.server import FossServer

from config import loadConfig, saveBackupConfig, saveConfig, isInThisCycle
import datefuncs
from runners import doNextThing
from manualws import runManualWSAgent
from clearing import doCleared
from newmonth import copyToNextMonth
from approving import doApprove
from emailing import printEmail, printAllLinks, printReportLinks
from delivering import doDelivered
from metrics import getMetrics, printMetrics
from metricsfile import saveMetrics
from transfer import doTransfer
from datetime import datetime

LOCK_FILE_NAME = "lock.lock"

def printUsage():
    print(f"""
Usage: {sys.argv[0]} <month> <command> [<project>] [<subproject>]
Month: in format YYYY-MM

Commands:

  Running:
    newmonth:         Begin a new month and reset status for all projects
    run:              Run next steps for all subprojects
    clear:            Flag cleared in Fossology for [sub]project
    approve:          Flag approved auto-generated findings in report for [sub]project
    deliver:          Flag delivered report for [sub]project

  Manual run:
    ws:               Manually run a new WhiteSource scan

  Printing:
    status:           Print status for all subprojects
    printemail:       Print email with links to reports for [sub]project
    printlinks:       Print links to all reports for [sub]project
    printreportlinks: Print only findings link(s) for [sub]project

  Metrics:
    getmetrics:       Analyze and save metrics for overall current status to JSON file
    printmetrics:     Load and print metrics from JSON file

  Admin:
    transfer:         Transfer project scans from old Fossology server to new
    clearlock:        Clear the lock file

""")

def status(cfg, prj_only, sp_only):
    headers = ["Project", "Subproject", "Status", "Notes"]
    table = []
    projects = cfg._projects

    for prj in projects.values():
        if prj_only == "" or prj_only == prj._name:
            row = [prj._name, "", prj._status.name, ""]
            table.append(row)
            for sp in prj._subprojects.values():
                if sp_only == "" or sp_only == sp._name:
                    extras = []
                    if not isInThisCycle(cfg, prj, sp):
                        extras.append(f"off-cycle")
                    if sp._github_branch != "":
                        extras.append(f"branch: {sp._github_branch}")

                    row = [prj._name, sp._name, sp._status.name, ";".join(extras)]
                    table.append(row)

    table = sorted(table, key=itemgetter(0, 1))
    print(tabulate(table, headers=headers))

def fossdriverSetup(fossdriverrc_path):
    config = FossConfig()
    retval = config.configure(fossdriverrc_path)
    if not retval:
        print(f"Error: Could not load config file from {fossdriverrc_path}")
        return False

    server = FossServer(config)
    server.Login()

    return server

def lockfile(config_dir):
    ''' Lock the lockfile for the month
    config_dir - directory for the month containing the configuration file
    Returns true if the month was successfully locked or false if the month is already locked
    '''
    
    lockfile = os.path.join(config_dir, LOCK_FILE_NAME)
    try:
        with open(lockfile, 'x') as f:
            f.write('Open for lock on ')
            f.write(str(datetime.now()))
            return True
    except:
        return False

def unlockfile(config_dir):
    ''' Unlocks the lockfile for the month
    '''
    lockfile = os.path.join(config_dir, LOCK_FILE_NAME)
    os.remove(lockfile)

def clear_lock(config_dir):
    '''
    Clears the lock file
    '''
    lockfile = os.path.join(config_dir, LOCK_FILE_NAME)
    if os.path.exists(lockfile):
        os.remove(lockfile)

def exec_command(SCAFFOLD_HOME, cfg, args):
    '''
    Executes the command
    cfg - Configuration
    args - Arguments - args[1] month; args[2] command; args[3] optional project; args[4] optional subproject
    returns true if successful, false if not
    '''
    # we'll check if added optional args limit to one prj / sp
    prj_only = ""
    sp_only = ""
    ran_command = False

    if len(args) >= 3:
        command = args[2]

    if len(args) >= 4:
        prj_only = args[3]
        if len(args) >= 5:
            sp_only = args[4]

    if command == "status":
        ran_command = True
        status(cfg, prj_only, sp_only)

    elif command == "newmonth":
        ran_command = True
        copyToNextMonth(SCAFFOLD_HOME, cfg)

    elif command == "run":
        ran_command = True
        saveBackupConfig(SCAFFOLD_HOME, cfg)

        # set up fossdriver server connection
        fossdriverrc_path = os.path.join(str(Path.home()), ".fossdriver", "fossdriverrc.json")
        fdServer = fossdriverSetup(fossdriverrc_path)
        if not fdServer:
            print(f"Unable to connect to Fossology server with fossdriver")
            sys.exit(1)

        # run commands
        doNextThing(SCAFFOLD_HOME, cfg, fdServer, prj_only, sp_only)

        # save modified config file
        saveConfig(SCAFFOLD_HOME, cfg)

    elif command == "ws":
        ran_command = True
        if prj_only == "" or sp_only == "":
            print(f"ws command requires specifying project and subproject")
            sys.exit(1)

        # run WS agent manually if between ZIPPEDCODE and CLEARED state
        # does not modify the config file
        runManualWSAgent(cfg, prj_only, sp_only)

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
        fossdriverrc_path = os.path.join(str(Path.home()), ".fossdriver", "fossdriverrc.json")
        fdServer = fossdriverSetup(fossdriverrc_path)
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

    elif command == "transfer":
        ran_command = True

        # set up fossdriver server connections
        old_fossdriverrc_path = os.path.join(str(Path.home()), ".fossdriver", "fossdriverrc.json")
        old_server = fossdriverSetup(old_fossdriverrc_path)
        if not old_server:
            print(f"Unable to connect to old Fossology server with fossdriver")
            sys.exit(1)
        new_fossdriverrc_path = os.path.join(str(Path.home()), ".fossdriver", "fossdriver3rc.json")
        new_server = fossdriverSetup(new_fossdriverrc_path)
        if not new_server:
            print(f"Unable to connect to new Fossology server with fossdriver")
            sys.exit(1)

        # run transfer
        doTransfer(SCAFFOLD_HOME, cfg, prj_only, old_server, new_server)
        
    return ran_command

if __name__ == "__main__":
    # check and parse year-month
    if len(sys.argv) < 2:
        printUsage()
        sys.exit(1)
    year, month = datefuncs.parseYM(sys.argv[1])
    if year == 0 and month == 0:
        print("Invalid month\n")
        printUsage()
        sys.exit(1)

    # get scaffold home directory
    SCAFFOLD_HOME = os.getenv('SCAFFOLD_HOME')
    if SCAFFOLD_HOME == None:
        SCAFFOLD_HOME = os.path.join(Path.home(), "scaffold")
    MONTH_DIR = os.path.join(SCAFFOLD_HOME, datefuncs.getYMStr(year, month))

    if sys.argv[2] == "clearlock":
        clear_lock(MONTH_DIR)
    else:
        # load configuration file for this month
        cfg_file = os.path.join(MONTH_DIR, "config.json")
        cfg = loadConfig(cfg_file, SCAFFOLD_HOME)
        ran_command = False
        if lockfile(MONTH_DIR):
            try:
                ran_command = exec_command(SCAFFOLD_HOME, cfg, sys.argv)
            finally:
                unlockfile(MONTH_DIR)
        else:
            print("""
It looks like Scaffold is already running for this month.
If you are Absolutely sure scaffold is Not being run by another user,
you can run the 'clearlock' command to remove the lock file.
            """)
        if not ran_command:
            printUsage()
            sys.exit(1) 
