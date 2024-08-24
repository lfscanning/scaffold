# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE

import trivyagent

from datatypes import Status

# run trivy, either through manual trigger or runner
def trivyAgentForSubproject(cfg, prj, sp):
    # have to at least have the code
    if not (sp._status.value >= Status.ZIPPEDCODE.value and sp._status != Status.STOPPED):
        print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected ZIPPEDCODE or higher")
        return False
    
    if not trivyagent.runUnifiedAgent(cfg, prj, sp):
        return False
    else:
        print(f"{prj._name}/{sp._name}: Trivy succeeded")
        return True
    
def runManualTrivyAgent(cfg, prj_only="", sp_only=""):
    if prj_only == "":
        print(f"Error: `trivy` command requires specifying only one project and only one subproject")
        return False

    prj = cfg._projects.get(prj_only, None)
    if not prj:
        print(f"{prj_only}: Project not found in config")
        return False

    sp = prj._subprojects.get(sp_only, None)
    if not sp:
        print(f"{prj_only}/{sp_only}: Subproject not found in project config")
        return False

    return trivyAgentForSubproject(cfg, prj, sp)
