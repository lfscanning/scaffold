# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

from .datatypes import Status
from .config import updateProjectStatusToSubprojectMin

def doCleared(scaffold_home, cfg, prj_only="", sp_only=""):
    if prj_only == "":
        print(f"Error: `clear` command requires specifying only one project (and optionally only one subproject)")
        return False

    # update status to CLEARED if was RANAGENTS, otherwise don't
    prj = cfg._projects.get(prj_only, None)
    if not prj:
        print(f"{prj_only}: Project not found in config")
        return False

    ran_command = False
    for sp in prj._subprojects.values():
        if sp_only == "" or sp_only == sp._name:
            if sp._status == Status.CLEARED:
                print(f"{prj._name}/{sp._name}: already marked as CLEARED, not changing")
                ran_command = True
            elif sp._status == Status.RANAGENTS:
                sp._status = Status.CLEARED
                print(f"{prj._name}/{sp._name}: updated status to CLEARED")
                ran_command = True
            else:
                print(f"{prj._name}/{sp._name}: status is {sp._status}, skipping clearing")

    # update project status overall
    updateProjectStatusToSubprojectMin(cfg, prj)
    
    return ran_command
