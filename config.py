# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json
import os
from shutil import copyfile

from datatypes import Config, Project, ProjectRepoType, Status, Subproject

def getConfigFilename(scaffoldHome, month):
    return os.path.join(scaffoldHome, month, "config.json")

def loadConfig(configFilename):
    cfg = Config()

    try:
        with open(configFilename, 'r') as f:
            js = json.load(f)

            # load global config
            config_dict = js.get('config', {})
            if config_dict == {}:
                print(f'No config section found in config file')
                return cfg
            cfg._month = config_dict.get('month', "")
            if cfg._month == "":
                print(f'No valid month found in config section')
                return cfg
            cfg._version = config_dict.get('version', -1)
            if cfg._version == -1:
                print(f'No valid version found in config section')
                return cfg
            cfg._storepath = config_dict.get('storepath', "")
            if cfg._storepath == "":
                print(f'No valid storepath found in config section')
                return cfg
            cfg._ok = True

            # load projects
            projects_dict = js.get('projects', {})
            if projects_dict == {}:
                print(f'No projects found in config file')
                return cfg

            for prj_name, prj_dict in projects_dict.items():
                prj = Project()
                prj._name = prj_name
                prj._ok = True

                # get project status
                status_str = prj_dict.get('status', '')
                if status_str == '':
                    prj._status = Status.UNKNOWN
                else:
                    prj._status = Status[status_str]

                pt = prj_dict.get('type', '')
                if pt == "gerrit":
                    prj._repotype = ProjectRepoType.GERRIT
                    gerrit_dict = prj_dict.get('gerrit', {})
                    if gerrit_dict == {}:
                        print(f'Project {prj_name} has no gerrit data')
                        prj._ok = False
                    else:
                        prj._gerrit_apiurl = gerrit_dict.get('apiurl', '')
                        if prj._gerrit_apiurl == '':
                            print(f'Project {prj_name} has no apiurl data')
                            prj._ok = False
                        # if subproject-config is absent, treat it as manual
                        prj._gerrit_subproject_config = gerrit_dict.get('subproject-config', "manual")
                        # if repos-ignore is absent, that's fine
                        prj._gerrit_repos_ignore = gerrit_dict.get('repos-ignore', [])
                        # if repos-pending is absent, that's fine
                        prj._gerrit_repos_pending = gerrit_dict.get('repos-pending', [])
                    # now load subprojects, if any are listed; it's okay if none are
                    sps = prj_dict.get('subprojects', {})
                    if sps != {}:
                        for sp_name, sp_dict in sps.items():
                            sp = Subproject()
                            sp._name = sp_name
                            sp._repotype = ProjectRepoType.GERRIT
                            sp._ok = True

                            # get subproject status
                            status_str = sp_dict.get('status', '')
                            if status_str == '':
                                sp._status = Status.UNKNOWN
                            else:
                                sp._status = Status[status_str]
                            
                            sp_gerrit_dict = sp_dict.get('gerrit', {})
                            if sp_gerrit_dict == {}:
                                sp._repos = []
                            else:
                                # if repos is absent, that's fine
                                sp._repos = sp_gerrit_dict.get('repos', [])

                            # and add subprojects to the project's dictionary
                            prj._subprojects[sp_name] = sp

                elif pt == "github-shared":
                    prj._repotype = ProjectRepoType.GITHUB_SHARED
                    github_shared_dict = prj_dict.get('github-shared', {})
                    if github_shared_dict == {}:
                        print(f'Project {prj_name} has no github-shared data')
                        prj._ok = False
                    else:
                        prj._github_shared_org = github_shared_dict.get('org', '')
                        if prj._github_shared_org == '':
                            print(f'Project {prj_name} has no org data')
                            prj._ok = False
                        # if repos-ignore is absent, that's fine
                        prj._github_shared_repos_ignore = github_shared_dict.get('repos-ignore', [])
                        # if repos-pending is absent, that's fine
                        prj._github_shared_repos_pending = github_shared_dict.get('repos-pending', [])
                    # now load subprojects, if any are listed; it's okay if none are
                    sps = prj_dict.get('subprojects', {})
                    if sps != {}:
                        for sp_name, sp_dict in sps.items():
                            sp = Subproject()
                            sp._name = sp_name
                            sp._repotype = ProjectRepoType.GITHUB_SHARED
                            sp._ok = True

                            # get subproject status
                            status_str = sp_dict.get('status', '')
                            if status_str == '':
                                sp._status = Status.UNKNOWN
                            else:
                                sp._status = Status[status_str]

                            # get subproject github-shared details, including repos
                            gs_sp_shared_dict = sp_dict.get('github-shared', {})
                            if gs_sp_shared_dict == {}:
                                print(f'Subproject {sp_name} in project {prj_name} has no github-shared data')
                                prj._ok = False
                            else:
                                # if no repos specified, that's fine, we'll find them later
                                sp._repos = gs_sp_shared_dict.get('repos', [])

                            # and add subprojects to the project's dictionary
                            prj._subprojects[sp_name] = sp

                elif pt == "github":
                    prj._repotype = ProjectRepoType.GITHUB
                    sps = prj_dict.get('subprojects', {})
                    if sps == {}:
                        print(f'Project {prj_name} has no subprojects specified')
                        prj._ok = False
                    else:
                        for sp_name, sp_dict in sps.items():
                            sp = Subproject()
                            sp._name = sp_name
                            sp._repotype = ProjectRepoType.GITHUB
                            sp._ok = True

                            # get subproject status
                            status_str = sp_dict.get('status', '')
                            if status_str == '':
                                sp._status = Status.UNKNOWN
                            else:
                                sp._status = Status[status_str]

                            # get subproject github details
                            github_dict = sp_dict.get('github', {})
                            if github_dict == {}:
                                print(f'Project {prj_name} has no github data')
                                prj._ok = False
                            else:
                                sp._github_org = github_dict.get('org', '')
                                if sp._github_org == '':
                                    print(f'Subproject {sp_name} in project {prj_name} has no org specified')
                                    sp._ok = False
                                # if no ziporg specified, that's fine, use the org name
                                sp._github_ziporg = github_dict.get('ziporg', sp._github_org)
                                # if no repos specified, that's fine, we'll find them later
                                sp._repos = github_dict.get('repos', [])
                                # and if no repos-ignore specified, that's fine too
                                sp._github_repos_ignore = github_dict.get('repos-ignore', [])
                                # and if no repos-pending specified, that's fine too
                                sp._github_repos_pending = github_dict.get('repos-pending', [])

                            # and add subprojects to the project's dictionary
                            prj._subprojects[sp_name] = sp

                else:
                    print(f'Project {prj_name} has invalid or no repo type')
                    prj._repotype = ProjectRepoType.UNKNOWN
                    prj._ok = False

                # and add project to the dictionary
                cfg._projects[prj_name] = prj
            
            return cfg

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {configFilename}: {str(e)}')
        return {}

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
                        "subproject-config": o._gerrit_subproject_config,
                        "repos-ignore": o._gerrit_repos_ignore,
                        "repos-pending": o._gerrit_repos_pending,
                    },
                    "subprojects": o._subprojects,
                }
            elif o._repotype == ProjectRepoType.GITHUB_SHARED:
                return {
                    "type": "github-shared",
                    "status": o._status.name,
                    "github-shared": {
                        "org": o._github_shared_org,
                        "repos-ignore": o._github_shared_repos_ignore,
                        "repos-pending": o._github_shared_repos_pending,
                    },
                    "subprojects": o._subprojects,
                }
            else:
                return {
                    "type": "unknown"
                }

        elif isinstance(o, Subproject):
            if o._repotype == ProjectRepoType.GITHUB:
                js = {
                    "status": o._status.name,
                    "github": {
                        "org": o._github_org,
                        "ziporg": o._github_ziporg,
                        "repos": sorted(o._repos),
                        "repos-ignore": sorted(o._github_repos_ignore),
                    }
                }
                if len(o._github_repos_pending) > 0:
                    js["github"]["repos-pending"] = sorted(o._github_repos_pending)
                return js
            elif o._repotype == ProjectRepoType.GITHUB_SHARED:
                return {
                    "status": o._status.name,
                    "github-shared": {
                        "repos": sorted(o._repos),
                    }
                }
            elif o._repotype == ProjectRepoType.GERRIT:
                return {
                    "status": o._status.name,
                    "gerrit": {
                        "repos": sorted(o._repos),
                    }
                }
            else:
                return {
                    "type": "unknown"
                }

        else:
            return {'__{}__'.format(o.__class__.__name__): o.__dict__}

def saveBackupConfig(scaffoldHome, cfg):
    configFilename = getConfigFilename(scaffoldHome, cfg._month)

    # if existing file is present, copy to backup
    if os.path.isfile(configFilename):
        backupDir = os.path.join(scaffoldHome, cfg._month, "backup")
        backupFilename = os.path.join(backupDir, f"config-{cfg._version}.json")

        if not os.path.exists(backupDir):
            os.makedirs(backupDir)
        copyfile(configFilename, backupFilename)

    # now, increment the config version
    cfg._version += 1

    # don't save it back to disk yet -- we'll do that later (repeatedly)

def saveConfig(scaffoldHome, cfg):
    configFilename = getConfigFilename(scaffoldHome, cfg._month)

    # don't increment the config version -- we should have done that
    # by saving a backup

    # save the config file out as json
    with open(configFilename, "w") as f:
        json.dump(cfg, f, indent=4, cls=ConfigJSONEncoder)
