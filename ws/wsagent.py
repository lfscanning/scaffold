# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE
import sys

import ws.wscfg

def runUnifiedAgent(cfg, prj, sp):
    # get environment, including necessary values
    env = ws.wscfg.getWSEnv(cfg, prj, sp)
    env["WS_WSS_URL"] = cfg._ws_server_url + "/agent"
    org_token = ws.wscfg.getWSOrgToken(cfg, prj, sp)
    #env["WS_API_KEY"] = org_token
    product_name = ws.wscfg.getWSProductName(cfg, prj, sp)
    env["WS_PRODUCTNAME"] = product_name
    project_name = ws.wscfg.getWSProjectName(cfg, prj, sp)
    env["WS_PROJECTNAME"] = project_name

    cmd = ["java", "-jar", cfg._ws_unified_agent_jar_path,
        "-apiKey", org_token,
        "-d", sp._code_path,
        "-noconfig", "true"
    ]
    cp = run(cmd, env=env, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if cp.returncode != 0:
        print(f"""{prj._name}/{sp._name}: WS unified agent failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        return False
    else:
        print(f"{prj._name}/{sp._name}: WS unified agent call succeeded")
        return True
