# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import json

from .datatypes import Instance, InstanceSet

def loadInstances(instancesFilename):
    try:
        with open(instancesFilename, 'r') as f:
            js = json.load(f)

            instSet = InstanceSet()
            # add the flagged instances
            flagged = js.get("flagged", [])
            for i in flagged:
                inst = Instance()
                inst._finding_id = i.get("id", -1)
                inst._files = i.get("files", [])
                inst._subprojects = i.get("subprojects", [])
                inst._first = i.get("first", "")
                inst._isnew = i.get("new", True)
                inst._files_changed = i.get("filesChanged", False)
                inst._jira_id = i.get("jira", "")
                instSet._flagged.append(inst)
            # and add the unflagged files
            unflagged = js.get("unflagged", [])
            for u in unflagged:
                instSet._unflagged.append(u)

            return instSet

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {instancesFilename}: {str(e)}')
        return None

class InstanceSetJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, InstanceSet):
            return {
                "flagged": o._flagged,
                "unflagged": o._unflagged,
            }

        elif isinstance(o, Instance):
            retval = {
                "id": o._finding_id,
                "files": o._files,
                "subprojects": o._subprojects,
                "first": o._first,
                "new": o._isnew,
            }
            if not o._isnew:
                retval["filesChanged"] = o._files_changed
            if o._jira_id != "":
                retval["jira"] = o._jira_id
            return retval

        else:
            return {'__{}__'.format(o.__class__.__name__): o.__dict__}

def saveInstances(instancesFilename, instSet):
    with open(instancesFilename, "w") as f:
        json.dump(instSet, f, indent=4, cls=InstanceSetJSONEncoder)
