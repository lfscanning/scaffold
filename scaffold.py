# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from operator import itemgetter
import os
import sys

from tabulate import tabulate

from config import loadConfig, saveConfig
import datefuncs
from runners import doNextThing

def printUsage():
    print(f"")
    print(f"Usage: {sys.argv[0]} <month> <command>")
    print(f"Month: in format YYYY-MM")
    print(f"Commands:")
    print(f"  status:  Print status for all subprojects")
    print(f"  run:     Run next steps for all subprojects")
    print(f"  cleared: Flag cleared in Fossology for [sub]project")
    print(f"")

def status(projects):
    headers = ["Project", "Subproject", "Status"]
    table = []

    for prj in projects.values():
        for sp in prj._subprojects.values():
            row = [prj._name, sp._name, sp._status.name]
            table.append(row)

    table = sorted(table, key=itemgetter(0, 1))
    print(tabulate(table, headers=headers))

if __name__ == "__main__":
    # check and parse year-month
    if len(sys.argv) < 2:
        printUsage()
        sys.exit(1)
    year, month = datefuncs.parseYM(sys.argv[1])
    if year == 0 and month == 0:
        printUsage()
        sys.exit(1)

    # get scaffold home directory
    SCAFFOLD_HOME = os.getenv('SCAFFOLD_HOME')
    if SCAFFOLD_HOME == None:
        SCAFFOLD_HOME = os.path.join(Path.home(), "scaffold")
    MONTH_DIR = os.path.join(SCAFFOLD_HOME, f"{year}-{month}")

    ran_command = False

    # load configuration file for this month
    cfg_file = os.path.join(MONTH_DIR, "config.json")
    cfg = loadConfig(cfg_file)
    print(f"config: {cfg}")

    if len(sys.argv) == 3:
        month = sys.argv[1]
        command = sys.argv[2]

        if command == "status":
            ran_command = True
            status(cfg._projects)

        elif command == "run":
            ran_command = True
            # FIXME determine whether all, one project or one subproject

            # run commands
            doNextThing(cfg)

            # save modified config file
            saveConfig(SCAFFOLD_HOME, cfg)
            print(f"Saved new config.json as version {cfg._version}")

    if ran_command == False:
        printUsage()
        sys.exit(1)

