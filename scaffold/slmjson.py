# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import json
import os
from pathlib import Path

from scaffold.datatypes import SLMCategory, SLMFile, SLMLicense

# returns list of SLMCategories
# sp only used for ._name, use sp == None for combined reports
def loadSLMCategories(prj, sp, jsonFilename):
    if sp == None:
        spname = "COMBINED"
    else:
        spname = sp._name

    try:
        with open(jsonFilename, 'r') as f:
            js = json.load(f)

            # expecting array of category objects
            categories = []
            for cat_dict in js:
                cat = SLMCategory()
                cat._name = cat_dict.get("name", "")
                if cat._name == "":
                    print(f'{prj._name}/{spname}: SLM category has no name')
                    return []
                cat._numfiles = cat_dict.get("numFiles", 0)
                cat._licenses = []
                lics = cat_dict.get("licenses", [])
                for lic_dict in lics:
                    lic = SLMLicense()
                    lic._name = lic_dict.get("name", "")
                    if lic._name == "":
                        print(f'{prj._name}/{spname}: SLM license in category {cat._name} has no name')
                        return []
                    lic._numfiles = lic_dict.get("numFiles", 0)
                    lic._files = []
                    files = lic_dict.get("files", [])
                    for file_dict in files:
                        fi = SLMFile()
                        fi._path = file_dict.get("path")
                        if fi._path == "":
                            print(f'{prj._name}/{spname}: SLM file in license {lic._name} has no path')
                            return []
                        fi._findings = file_dict.get("findings", {})
                        lic._files.append(fi)
                    cat._licenses.append(lic)
                categories.append(cat)
            return categories

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {jsonFilename}: {str(e)}')
        return []

# call with list of SLMCategories
def saveSLMCategories(categories, jsonFilename):
    with open(jsonFilename, "w") as f:
        json.dump(categories, f, indent=4, cls=SLMPrimaryJSONEncoder)

class SLMPrimaryJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, SLMCategory):
            return {
                "name": o._name,
                "numFiles": o._numfiles,
                "licenses": o._licenses,
            }

        elif isinstance(o, SLMLicense):
            return {
                "name": o._name,
                "numFiles": o._numfiles,
                "files": o._files,
            }

        elif isinstance(o, SLMFile):
            file_obj = {"path": o._path}
            if o._findings != {}:
                file_obj["findings"] = o._findings
            return file_obj

        else:
            return {'__{}__'.format(o.__class__.__name__): o.__dict__}
