# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json

from datatypes import Instance, SPInstanceSet

def loadInstances(instancesFilename):
    # hash of subproject names to SPInstanceSets
    spInstances = {}

    try:
        with open(instancesFilename, 'r') as f:
            js = json.load(f)

            # expecting mapping of subproject names to SPInstanceSet data
            for spname, spinst in js.items():
                spis = SPInstanceSet()
                # add the flagged instances
                flagged = spinst.get("flagged", [])
                for i in flagged:
                    inst = Instance()
                    inst._finding_id = i.get("id", -1)
                    inst._files = i.get("files", [])
                    inst._first = i.get("first", "")
                    inst._isnew = i.get("new", True)
                    inst._jira_id = i.get("jira", "")
                    spis._flagged.append(inst)
                # and add the unflagged files
                unflagged = spinst.get("unflagged", [])
                for u in unflagged:
                    spis._unflagged.append(u)

                # add it to what we've seen
                spInstances[spname] = spis
            
            # and return
            return spInstances

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {instancesFilename}: {str(e)}')
        return []

class SPInstancesJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, SPInstanceSet):
            return {
                "flagged": o._flagged,
                "unflagged": o._unflagged,
            }

        elif isinstance(o, Instance):
            retval = {
                "id": o._finding_id,
                "files": o._files,
                "first": o._first,
                "new": o._isnew,
            }
            if o._jira_id != "":
                retval["jira"] = o._jira_id
            return retval

        else:
            return {'__{}__'.format(o.__class__.__name__): o.__dict__}

def saveInstances(instancesFilename, spInstances):
    with open(instancesFilename, "w") as f:
        json.dump(spInstances, f, indent=4, cls=SPInstancesJSONEncoder)
