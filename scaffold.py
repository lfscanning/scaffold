# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import os
import sys

from config import loadConfig
import datefuncs

def printUsage():
    print(f"")
    print(f"Usage: {sys.argv[0]} <month> <command>")
    print(f"Month: in format YYYY-MM")
    print(f"Commands:")
    print(f"  status:  Print status for all subprojects")
    print(f"  run:     Run next steps for all subprojects")
    print(f"")

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
    # for name, prj in projects.items():
    #     print(f"{name}: {prj}")

    if len(sys.argv) == 3:
        month = sys.argv[1]
        command = sys.argv[2]

        if command == "status":
            ran_command = True

        elif command == "run":
            ran_command = True

    if ran_command == False:
        printUsage()
        sys.exit(1)

