# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from subprocess import run, PIPE
import sys
import zipfile
import tempfile
from pdb import set_trace

def runUnifiedAgent(cfg, prj, sp):
    # make sure that the code to upload actually exists!
    set_trace()
    if not sp._code_path:
        print(f"{prj._name}/{sp._name}: No code path found; can not run Trivy")
        return False
    if not os.path.exists(sp._code_path):
        print(f"{prj._name}/{sp._name}: Nothing found at code path {sp._code_path}; can not run Trivy")
        return False
    if not os.path.isfile(sp._code_path):
        print(f"{prj._name}/{sp._name}: Code path {sp._code_path} exists but is not a file; can not run Trivy")
        return False
    with tempfile.TemporaryDirectory() as tempdir:
        # Unzip file to a temporary directory
        analysisdir = os.path.join(tempdir, "code")
        os.mkdir(analysisdir)
        with zipfile.ZipFile(sp._code_path, mode='r') as zip:
            zip.extractall(analysisdir)
        cmd = ["trivy", "fs", "--scanners", "license,vuln", "--format", "spdx-json", analysisdir]
        result = os.path.join(tempdir, f"{prj._name}-{sp._name}-spdx.json")
        with open(result, 'w') as outfile:
            cp = run(cmd, stdout=outfile, stderr=PIPE, universal_newlines=True, shell=True)
            if cp.returncode != 0:
                print(f"""{prj._name}/{sp._name}: Trivy failed with error code {cp.returncode}:
----------
output:
{cp.stdout}
----------
errors:
{cp.stderr}
----------
""")
                return False
        # TODO - Fixupt the output file
        # TODO - Upload the result to GitHub
        # TODO - Generate xls report
        # TODO - put the report in the report directory
        print(f"{prj._name}/{sp._name}: Trivy successfully run")
        return True

