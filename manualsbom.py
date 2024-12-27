# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import sbomagent

from datatypes import Status

# run sbom, either through manual trigger or runner
def sbomAgentForSubproject(cfg, prj, sp):
    # have to at least have the code
    if not (sp._status.value >= Status.ZIPPEDCODE.value and sp._status != Status.STOPPED):
        print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected ZIPPEDCODE or higher")
        return False
    
    if not sbomagent.runUnifiedAgent(cfg, prj, sp):
        return False
    else:
        print(f"{prj._name}/{sp._name}: Sbom succeeded")
        return True
    
def runManualSbomAgent(cfg, prj_only="", sp_only=""):
    if prj_only == "":
        print(f"Error: `sbom` command requires specifying only one project")
        return False

    prj = cfg._projects.get(prj_only, None)
    if not prj:
        print(f"{prj_only}: Project not found in config")
        return False
    did_something = False
    for sp in prj._subprojects.values():
        if sp_only == "" or sp_only == sp._name:
            if not sbomAgentForSubproject(cfg, prj, sp):
                return False
            did_something = True
    return did_something

