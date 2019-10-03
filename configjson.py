# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json

from datatypes import Config, Project, ProjectRepoType, Status, Subproject

class ConfigJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, Config):
            return {
                "config": {
                    "storepath": o._storepath,
                    "month": o._month,
                    "version": o._version,
                },
                "projects": o._projects,
            }
        
        elif isinstance(o, Project):
            if o._repotype == ProjectRepoType.GITHUB:
                return {
                    "type": "github",
                    "subprojects": o._subprojects,
                }
            elif o._repotype == ProjectRepoType.GERRIT:
                return {
                    "type": "gerrit",
                    "status": o._status.name,
                    "gerrit": {
                        "apiurl": o._gerrit_apiurl,
                        "repos-ignore": o._gerrit_repos_ignore,
                    },
                    "subprojects": o._subprojects,
                }
            else:
                return {
                    "type": "unknown"
                }
        
        elif isinstance(o, Subproject):
            if o._repotype == ProjectRepoType.GITHUB:
                return {
                    "status": o._status.name,
                    "github": {
                        "org": o._github_org,
                        "ziporg": o._github_ziporg,
                        "repos": o._repos,
                        "repos-ignore": o._github_repos_ignore,
                    }
                }
            elif o._repotype == ProjectRepoType.GERRIT:
                return {
                    "status": o._status.name,
                    "gerrit": {
                        "repos": o._repos,
                    }
                }
            else:
                return {
                    "type": "unknown"
                }
        
        else:
            return {'__{}__'.format(o.__class__.__name__): o.__dict__}
