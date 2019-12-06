# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json
import os
from shutil import copyfile

from datatypes import Config, MatchText, Project, ProjectRepoType, Status, Subproject

def getConfigFilename(scaffoldHome, month):
    return os.path.join(scaffoldHome, month, "config.json")

def getMatchesProjectFilename(scaffoldHome, month, prj_name):
    return os.path.join(scaffoldHome, month, f"matches-{prj_name}.json")

def loadMatches(matchesFilename):
    matches = []

    try:
        with open(matchesFilename, 'r') as f:
            js = json.load(f)

            # expecting array of match objects
            for j in js:
                m = MatchText()
                m._text = j.get('text', "")
                if m._text == "":
                    print(f'No text value found in match section')
                    return []
                # comments can be empty string or absent
                m._comment = j.get('comment', "")
                actions = j.get('actions', [])
                if actions == []:
                    if m._comment == "":
                        print(f'No actions found in match section')
                    else:
                        print(f'No actions found in match section with comment {m._comment}')
                    return []
                # parse and add actions
                m._actions = []
                for a in actions:
                    ac = a.get('action', "")
                    if ac != "add" and ac != "remove":
                        print(f'Invalid action type {ac} in match')
                        return []
                    lic = a.get('license', "")
                    if lic == "":
                        print(f'Invalid empty string for license in match')
                        return []
                    actionTup = (ac, lic)
                    m._actions.append(actionTup)
                # and now add it in
                matches.append(m)
        return matches

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {matchesFilename}: {str(e)}')
        return []

def loadConfig(configFilename, scaffoldHome):
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
            cfg._spdx_github_org = config_dict.get('spdxGithubOrg', "")
            if cfg._spdx_github_org == "":
                print(f'No valid spdxGithubOrg found in config section')
                return cfg
            cfg._spdx_github_signoff = config_dict.get('spdxGithubSignoff', "")
            if cfg._spdx_github_signoff == "":
                print(f'No valid spdxGithubSignoff found in config section')
                return cfg

            # load slm data
            slm_dict = config_dict.get('slm', {})
            if slm_dict == {}:
                print(f'No slm section found in config section')
                return cfg
            cfg._slm_home = slm_dict.get('home', "")
            if cfg._slm_home == "":
                print(f'No valid home found in slm section')
                return cfg

            # if we get here, main config is at least valid
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

                    # now load SLM project data
                    parseProjectSLMConfig(prj_dict, prj)

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
                            
                            # get code section
                            code_dict = sp_dict.get('code', {})
                            if code_dict == {}:
                                sp._code_pulled = ""
                                sp._code_path = ""
                                sp._code_anyfiles = False
                            else:
                                sp._code_pulled = code_dict.get('pulled', "")
                                sp._code_path = code_dict.get('path', "")
                                sp._code_anyfiles = code_dict.get('anyfiles', "")

                            # now load SLM subproject data
                            parseSubprojectSLMConfig(sp_dict, prj, sp)

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

                    # now load SLM project data
                    parseProjectSLMConfig(prj_dict, prj)

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

                            # get code section
                            code_dict = sp_dict.get('code', {})
                            if code_dict == {}:
                                sp._code_pulled = ""
                                sp._code_path = ""
                                sp._code_anyfiles = False
                            else:
                                sp._code_pulled = code_dict.get('pulled', "")
                                sp._code_path = code_dict.get('path', "")
                                sp._code_anyfiles = code_dict.get('anyfiles', "")

                            # now load SLM subproject data
                            parseSubprojectSLMConfig(sp_dict, prj, sp)

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

                    # now load SLM project data
                    parseProjectSLMConfig(prj_dict, prj)

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

                            # get code section
                            code_dict = sp_dict.get('code', {})
                            if code_dict == {}:
                                sp._code_pulled = ""
                                sp._code_path = ""
                                sp._code_anyfiles = False
                            else:
                                sp._code_pulled = code_dict.get('pulled', "")
                                sp._code_path = code_dict.get('path', "")
                                sp._code_anyfiles = code_dict.get('anyfiles', "")

                            # now load SLM subproject data
                            parseSubprojectSLMConfig(sp_dict, prj, sp)

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

                # also add in matches if a matches-{prj_name}.json file exists
                matchesFilename = getMatchesProjectFilename(scaffoldHome, cfg._month, prj._name)
                if os.path.isfile(matchesFilename):
                    prj._matches = loadMatches(matchesFilename)
                else:
                    prj._matches = []

                # and add project to the dictionary
                cfg._projects[prj_name] = prj
            
            return cfg

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {configFilename}: {str(e)}')
        return {}

def parseProjectSLMConfig(prj_dict, prj):
    prj_slm_dict = prj_dict.get('slm', {})
    if prj_slm_dict == {}:
        print(f'Project {prj._name} has no slm data')
        prj._ok = False
    else:
        prj._slm_shared = prj_slm_dict.get('shared', True)

        prj._slm_prj = prj_slm_dict.get('prj', None)
        if prj._slm_shared == False:
            if prj._slm_prj != None:
                print(f"Project {prj._name} has slm:shared == False but also specifies slm:prj")
                prj._ok = False
        else:
            if prj._slm_prj == "" and prj._slm_shared == True:
                print(f"Project {prj._name} has slm:shared == True but explicitly has empty string for slm:prj")
                prj._ok = False
            # default to using project name if none was specified
            if prj._slm_prj == None:
                prj._slm_prj = prj._name

        prj._slm_combined_report = prj_slm_dict.get('combinedReport', False)
        if prj._slm_combined_report == True and prj._slm_shared == False:
            print(f"Project {prj._name} has slm:shared == False but also has slm:combinedReport == True")
            prj._ok = False

def parseSubprojectSLMConfig(sp_dict, prj, sp):
    sp_slm_dict = sp_dict.get('slm', {})
    if sp_slm_dict == {}:
        # if project IS NOT shared SLM, then we assume _slm_prj is the sp name
        # if project IS shared SLM, then we ignore _slm_prj
        if prj._slm_shared == False:
            sp._slm_prj = sp._name
        # and either way we assume defaults for the other values
        sp._slm_sp = sp._name
        sp._slm_scan_id = -1
        sp._slm_pending_lics = []
    else:
        # we did get an slm section, so we'll parse it
        sp._slm_prj = sp_slm_dict.get('prj', "")
        if prj._slm_shared == True:
            if sp._slm_prj != "":
                print(f'Project {prj._name} has slm:shared == True but subproject {sp._name} specifies slm:prj')
                sp._ok = False
        else:
            if sp._slm_prj == "":
                sp._slm_prj = sp._name
        sp._slm_sp = sp_slm_dict.get('sp', sp._name)
        sp._slm_scan_id = sp_slm_dict.get('scan_id', -1)
        sp._slm_pending_lics = sp_slm_dict.get('licenses-pending', [])

class ConfigJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, Config):
            return {
                "config": {
                    "storepath": o._storepath,
                    "month": o._month,
                    "version": o._version,
                    "slm": {
                        "home": o._slm_home,
                    },
                    "spdxGithubOrg": o._spdx_github_org,
                    "spdxGithubSignoff": o._spdx_github_signoff,
                },
                "projects": o._projects,
            }

        elif isinstance(o, Project):
            # build SLM data
            slm_section = {}
            if o._slm_shared == True:
                slm_section = {
                    "shared": True,
                    "prj": o._slm_prj,
                    "combinedReport": o._slm_combined_report,
                }
            else:
                slm_section = {
                    "shared": False,
                }

            if o._repotype == ProjectRepoType.GITHUB:
                return {
                    "type": "github",
                    "slm": slm_section,
                    "subprojects": o._subprojects,
                }
            elif o._repotype == ProjectRepoType.GERRIT:
                return {
                    "type": "gerrit",
                    "slm": slm_section,
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
                    "slm": slm_section,
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
            # build SLM data
            slm_section = {"sp": o._slm_sp}
            if o._slm_prj != "":
                slm_section["prj"] = o._slm_prj
            if o._slm_scan_id != -1:
                slm_section["scan_id"] = o._slm_scan_id
            if o._slm_pending_lics != []:
                slm_section["licenses-pending"] = o._slm_pending_lics

            if o._repotype == ProjectRepoType.GITHUB:
                js = {
                    "status": o._status.name,
                    "slm": slm_section,
                    "code": {
                        "anyfiles": o._code_anyfiles,
                    },
                    "github": {
                        "org": o._github_org,
                        "ziporg": o._github_ziporg,
                        "repos": sorted(o._repos),
                        "repos-ignore": sorted(o._github_repos_ignore),
                    }
                }
                if o._code_pulled != "":
                    js["code"]["pulled"] = o._code_pulled
                if o._code_path != "":
                    js["code"]["path"] = o._code_path
                if len(o._github_repos_pending) > 0:
                    js["github"]["repos-pending"] = sorted(o._github_repos_pending)
                return js
            elif o._repotype == ProjectRepoType.GITHUB_SHARED:
                js = {
                    "status": o._status.name,
                    "slm": slm_section,
                    "code": {
                        "anyfiles": o._code_anyfiles,
                    },
                    "github-shared": {
                        "repos": sorted(o._repos),
                    }
                }
                if o._code_pulled != "":
                    js["code"]["pulled"] = o._code_pulled
                if o._code_path != "":
                    js["code"]["path"] = o._code_path
                return js
            elif o._repotype == ProjectRepoType.GERRIT:
                js = {
                    "status": o._status.name,
                    "slm": slm_section,
                    "code": {
                        "anyfiles": o._code_anyfiles,
                    },
                    "gerrit": {
                        "repos": sorted(o._repos),
                    }
                }
                if o._code_pulled != "":
                    js["code"]["pulled"] = o._code_pulled
                if o._code_path != "":
                    js["code"]["path"] = o._code_path
                return js
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

def updateProjectStatusToSubprojectMin(cfg, prj):
    minStatus = Status.MAX
    for sp in prj._subprojects.values():
        if sp._status.value < minStatus.value:
            minStatus = sp._status
    if minStatus == Status.MAX:
        minStatus = Status.START
    prj._status = minStatus
