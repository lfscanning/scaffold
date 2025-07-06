# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from scaffold.datatypes import Status
from scaffold.manualws import wsAgentForSubproject
from scaffold.ws.wscfg import isWSEnabled

def doUploadWSForSubproject(cfg, prj, sp):
    # make sure the subproject has not already had its code uploaded to WS
    # even though wsAgentForSubproject permits a broader range of statuses
    # for manual runs
    if sp._status != Status.ZIPPEDCODE:
        print(f"{prj._name}/{sp._name}: skipping, status is {sp._status.name}, expected ZIPPEDCODE")
        return True

    if not isWSEnabled(cfg, prj, sp):
        print(f"{prj._name}/{sp._name}: skipping, WhiteSource is disabled")
        sp._status = Status.UPLOADEDWS
        return True

    retval = wsAgentForSubproject(cfg, prj, sp)
    if not retval:
        return False

    # once we get here, the WhiteSource agent has run
    sp._status = Status.UPLOADEDWS

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True
