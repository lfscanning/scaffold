# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE
import sys

from . import wscfg

def runUnifiedAgent(cfg, prj, sp):
    # make sure that the code to upload actually exists!
    if not sp._code_path:
        print(f"{prj._name}/{sp._name}: No code path found; not uploading to WS")
        return False
    if not os.path.exists(sp._code_path):
        print(f"{prj._name}/{sp._name}: Nothing found at code path {sp._code_path}; not uploading to WS")
        return False
    if not os.path.isfile(sp._code_path):
        print(f"{prj._name}/{sp._name}: Code path {sp._code_path} exists but is not a file; not uploading to WS")
        return False

    # get environment, including necessary values
    env = wscfg.getWSEnv(cfg, prj, sp)
    env["WS_WSS_URL"] = cfg._ws_server_url + "/agent"
    org_token = wscfg.getWSOrgToken(cfg, prj, sp)
    #env["WS_API_KEY"] = org_token
    product_name = wscfg.getWSProductName(cfg, prj, sp)
    env["WS_PRODUCTNAME"] = product_name
    project_name = wscfg.getWSProjectName(cfg, prj, sp)
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
