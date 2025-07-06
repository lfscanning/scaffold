# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from scaffold.datatypes import Status
from scaffold.ws import wsagent
from scaffold.ws import wsapi
from scaffold.ws import wscfg

# run WS agent, either through manual trigger or runner
def wsAgentForSubproject(cfg, prj, sp):
    # it's possible to re-run even if the agent has already run once
    # (e.g., we might change configuration and re-run)
    # have to at least have the code
    if not (sp._status.value >= Status.ZIPPEDCODE.value and sp._status != Status.STOPPED):
        print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected ZIPPEDCODE or higher")
        return False

    userkey = wscfg.getWSUserKey(cfg, prj)
    org_token = wscfg.getWSOrgToken(cfg, prj, sp)

    # check that the sp exists as a product in whitesource;
    # will only call API if not yet called for this project in this
    # scaffold run
    product_name = wscfg.getWSProductName(cfg, prj, sp)
    product_token = wsapi.getProductToken(cfg, prj, product_name, userkey, org_token)
    if product_token == "":
        # try to create product
        print(f"Didn't find product {product_name}, attempting to create")
        product_token = wsapi.createProduct(cfg, prj, userkey, org_token, product_name)
        if product_token == "":
            print(f"Unable to get product token for {product_name} from WSAPI; bailing")
            return False

    # also check that the sp exists as a project within that product
    project_name = wscfg.getWSProjectName(cfg, prj, sp)
    project_token = wsapi.getProjectToken(cfg, prj, project_name, userkey, org_token)
    if project_token == "":
        # try to create project
        print(f"Didn't find project {project_name}, attempting to create")
        project_token = wsapi.createProject(cfg, prj, userkey, product_token, project_name)
        if project_token == "":
            print(f"Unable to get project token for {project_name} from WSAPI; bailing")
            return False

    # it exists, so we can proceed
    print(f"{prj._name}/{sp._name}: running WhiteSource unified agent")
    retval = wsagent.runUnifiedAgent(cfg, prj, sp)
    if not retval:
        print(f"{prj._name}/{sp._name}: failed to run WhiteSource unified agent")
        return False

    print(f"{prj._name}/{sp._name}: ran WhiteSource unified agent")

    # don't update status; runner can update if it wants to
    return True

def runManualWSAgent(cfg, prj_only="", sp_only=""):
    if prj_only == "":
        print(f"Error: `ws` command requires specifying only one project and only one subproject")
        return False

    prj = cfg._projects.get(prj_only, None)
    if not prj:
        print(f"{prj_only}: Project not found in config")
        return False

    sp = prj._subprojects.get(sp_only, None)
    if not sp:
        print(f"{prj_only}/{sp_only}: Subproject not found in project config")
        return False

    return wsAgentForSubproject(cfg, prj, sp)
