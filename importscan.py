# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from subprocess import run, PIPE

from datatypes import Status

def doImportScanForSubproject(cfg, prj, sp):
    # make sure we're at the right stage
    if sp._status != Status.GOTSPDX:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't import scan now")
        return False
    
    # set up environment variables
    os.environ["SLM_HOME"] = cfg._slm_home
    if prj._slm_shared == True:
        os.environ["SLM_PROJECT"] = prj._slm_prj
    else:
        os.environ["SLM_PROJECT"] = sp._slm_prj
    os.environ["SLM_SUBPROJECT"] = sp._slm_sp

    # prep SPDX path
    spdxPath = os.path.join(
        cfg._storepath,
        cfg._month,
        "spdx",
        prj._name,
        f"{sp._name}-{sp._code_pulled}.spdx",
    )
    
    # prep args
    cmd = [
        "slm",
        "import-scan",
        f"--scan_date={sp._code_pulled}",
        f"--desc={sp._slm_sp} {cfg._month} scan",
        spdxPath,
    ]

    # run the command
    cp = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    # was it successful?
    if cp.returncode != 0:
        # check if failed because needs licenses added
        if "The following unknown licenses were detected" in cp.stderr:
            # parse out section between lines
            lics_split = cp.stderr.split("=====")
            if len(lics_split) == 3:
                licset = set()
                for line in lics_split[1].splitlines():
                    if line != "":
                        licset.add(line)
                sp._slm_pending_lics = sorted(list(licset))
                print(f"{prj._name}/{sp._name}: need to add licenses to slm, see licenses-pending")
                return False

        # if didn't meet above reqs but got an error code, fail out
        print(f"""{prj._name}/{sp._name}: import scan failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        return False
    
    # if it was successful, parse output to get the scan ID number
    scan_id = -1
    output_split = cp.stdout.split("Scan ID is ")
    if len(output_split) == 2:
        scan_id = int(output_split[1])

    if scan_id <= 0:
        print(f"""{prj._name}/{sp._name}: scan imported but unable to detect scan ID
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
        return False
    
    # success!
    sp._slm_scan_id = scan_id
    print(f"{prj._name}/{sp._name}: scan imported with scan ID {scan_id}")

    # once we get here, the scan has been imported
    sp._status = Status.IMPORTEDSCAN
    
    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
