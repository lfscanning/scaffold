# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import glob
import os
import shutil

from config import saveConfig
from datatypes import Status
import datefuncs

def copyToNextMonth(scaffold_home, cfg):
    existing_ym = cfg._month
    # make sure there isn't already a folder for the next month
    year, month = datefuncs.parseYM(cfg._month)
    if year == 0 or month == 0:
        print(f"Unable to parse current year-month from config object; bailing")
        return False
    newYear, newMonth = datefuncs.nextMonth(year, month)
    newMonthDir = os.path.join(scaffold_home, f"{newYear}-{newMonth}")
    if os.path.exists(newMonthDir):
        print(f"Directory for next month already exists at {newMonthDir}; bailing")
        return False

    # update the config object
    cfg._month = f"{newYear}-{newMonth}"
    cfg._version = 1

    # update the config object's projects and subprojects
    for prj in cfg._projects.values():
        prj._status = Status.START
        for sp in prj._subprojects.values():
            sp._status = Status.START
            # reset code retrieval vars
            sp._code_pulled = ""
            sp._code_path = ""
            sp._code_anyfiles = False
            # reset scan-dependent SLM vars
            sp._slm_scan_id = -1
            sp._slm_pending_lics = []

    # create the new directory and save out the config object
    os.makedirs(newMonthDir)
    saveConfig(scaffold_home, cfg)
    print(f"Saved new config file for month {cfg._month}")

    # copy matches files
    existing_matches = glob.glob(os.path.join(scaffold_home, existing_ym, "matches*.json"))
    for em in existing_matches:
        new_filename = os.path.basename(em)
        new_dst = os.path.join(newMonthDir, new_filename)
        shutil.copyfile(em, new_dst)
        print(f"Copied matches file to {new_dst}")

    # copy findings files
    existing_findings = glob.glob(os.path.join(scaffold_home, existing_ym, "findings*.yaml"))
    for em in existing_findings:
        new_filename = os.path.basename(em)
        new_dst = os.path.join(newMonthDir, new_filename)
        shutil.copyfile(em, new_dst)
        print(f"Copied findings file to {new_dst}")

    return True
