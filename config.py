# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json
import os
from pathlib import Path
from shutil import copyfile

import yaml

from datatypes import Config, Finding, JiraSecret, MatchText, Priority, Project, ProjectRepoType, Secrets, SLMCategoryConfig, SLMLicenseConfig, SLMPolicy, Status, Subproject, TicketType

def getConfigFilename(scaffoldHome, month):
    return os.path.join(scaffoldHome, month, "config.json")

def getMatchesProjectFilename(scaffoldHome, month, prj_name):
    return os.path.join(scaffoldHome, month, f"matches-{prj_name}.json")

def getFindingsProjectFilename(scaffoldHome, month, prj_name):
    return os.path.join(scaffoldHome, month, f"findings-{prj_name}.yaml")

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

# parses findings template file and returns arrays, first with findings and
# second with flagged categories
def loadFindings(findingsFilename):
    try:
        with open(findingsFilename, "r") as f:
            yd = yaml.safe_load(f)

            # expecting object with findings array
            findings_arr = yd.get("findings", [])
            if findings_arr == []:
                print(f'No findings specified in {findingsFilename}')
                return []

            findings = []
            count = 0
            for fd in findings_arr:
                count += 1
                finding = Finding()
                finding._id = fd.get('id', [])
                finding._text = fd.get('text', "")
                finding._title = fd.get('title', "")
                finding._matches_path = fd.get('matches-path', [])
                finding._matches_license = fd.get('matches-license', [])
                finding._matches_subproject = fd.get('matches-subproject', [])
                if finding._matches_path == [] and finding._matches_license == [] and finding._matches_subproject == []:
                    print(f'Finding {count} in {findingsFilename} has no entries for either matches-path, matches-license or matches-subproject')
                    return []
                prstr = fd.get("priority", "")
                try:
                    finding._priority = Priority[prstr.upper()]
                except KeyError:
                    print(f'Invalid priority value for finding {count} in {findingsFilename} with paths {finding._matches_path}, licenses {finding._matches_license}, subprojects {finding._matches_subproject}, ')
                    return []

                findings.append(finding)

            return findings

    except yaml.YAMLError as e:
        print(f'Error loading or parsing {findingsFilename}: {str(e)}')
        return []

# parses secrets file; always looks in ~/.scaffold-secrets.json
def loadSecrets():
    secretsFile = os.path.join(Path.home(), ".scaffold-secrets.json")
    try:
        with open(secretsFile, 'r') as f:
            js = json.load(f)

            # expecting mapping of prj name to JiraSecret data
            secrets = Secrets()
            for prj, jira_dict in js.items():
                jira_secret = JiraSecret()

                jira_secret._project_name = prj
                jira_secret._jira_project = jira_dict.get("board", "")
                jira_secret._server = jira_dict.get("server", "")
                jira_secret._username = jira_dict.get("username", "")
                jira_secret._password = jira_dict.get("password", "")

                secrets._jira[prj] = jira_secret

        return secrets

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {secretsFile}: {str(e)}')
        return None

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

            # load web server data
            cfg._web_server = config_dict.get('webServer', "")
            if cfg._web_server == "":
                print(f"No valid webServer found in config section")
                return cfg
            cfg._web_reports_path = config_dict.get('webReportsPath', "")
            if cfg._web_reports_path == "":
                print(f"No valid webReportsPath found in config section")
                return cfg
            cfg._web_reports_url = config_dict.get('webReportsUrl', "")
            if cfg._web_reports_url == "":
                print(f"No valid webReportsUrl found in config section")
                return cfg

            # load secrets
            cfg._secrets = loadSecrets()

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

                # get project ticket type
                ticket_type = prj_dict.get('ticket-type', '')
                if ticket_type == "jira":
                    prj._ticket_type = TicketType.JIRA
                else:
                    prj._ticket_type = TicketType.NONE

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

                    # now load project web data, where applicable
                    parseProjectWebConfig(prj_dict, prj)

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
                                sp._code_repos = {}
                            else:
                                sp._code_pulled = code_dict.get('pulled', "")
                                sp._code_path = code_dict.get('path', "")
                                sp._code_anyfiles = code_dict.get('anyfiles', "")
                                sp._code_repos = code_dict.get('repos', {})

                            # get web data
                            web_dict = sp_dict.get('web', {})
                            if web_dict == {}:
                                sp._web_uuid = ""
                                sp._web_html_url = ""
                                sp._web_xlsx_url = ""
                            else:
                                sp._web_uuid = web_dict.get('uuid', "")
                                sp._web_html_url = web_dict.get('htmlurl', "")
                                sp._web_xlsx_url = web_dict.get('xlsxurl', "")

                            # now load SLM subproject data
                            parseSubprojectSLMConfig(sp_dict, prj, sp)

                            sp_gerrit_dict = sp_dict.get('gerrit', {})
                            if sp_gerrit_dict == {}:
                                sp._repos = []
                            else:
                                # if repos is absent, that's fine
                                sp._repos = sp_gerrit_dict.get('repos', [])
                                sp._repo_dirs_delete = sp_gerrit_dict.get('repo-dirs-delete', {})

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

                    # now load project web data, where applicable
                    parseProjectWebConfig(prj_dict, prj)

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
                                sp._code_repos = {}
                            else:
                                sp._code_pulled = code_dict.get('pulled', "")
                                sp._code_path = code_dict.get('path', "")
                                sp._code_anyfiles = code_dict.get('anyfiles', "")
                                sp._code_repos = code_dict.get('repos', {})

                            # get web data
                            web_dict = sp_dict.get('web', {})
                            if web_dict == {}:
                                sp._web_uuid = ""
                                sp._web_html_url = ""
                                sp._web_xlsx_url = ""
                            else:
                                sp._web_uuid = web_dict.get('uuid', "")
                                sp._web_html_url = web_dict.get('htmlurl', "")
                                sp._web_xlsx_url = web_dict.get('xlsxurl', "")

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
                                sp._repo_dirs_delete = gs_sp_shared_dict.get('repo-dirs-delete', {})

                            # and add subprojects to the project's dictionary
                            prj._subprojects[sp_name] = sp

                elif pt == "github":
                    prj._repotype = ProjectRepoType.GITHUB

                    # now load SLM project data
                    parseProjectSLMConfig(prj_dict, prj)

                    # now load project web data, where applicable
                    parseProjectWebConfig(prj_dict, prj)

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
                                sp._code_repos = {}
                            else:
                                sp._code_pulled = code_dict.get('pulled', "")
                                sp._code_path = code_dict.get('path', "")
                                sp._code_anyfiles = code_dict.get('anyfiles', "")
                                sp._code_repos = code_dict.get('repos', {})

                            # get web data
                            web_dict = sp_dict.get('web', {})
                            if web_dict == {}:
                                sp._web_uuid = ""
                                sp._web_html_url = ""
                                sp._web_xlsx_url = ""
                            else:
                                sp._web_uuid = web_dict.get('uuid', "")
                                sp._web_html_url = web_dict.get('htmlurl', "")
                                sp._web_xlsx_url = web_dict.get('xlsxurl', "")

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
                                sp._repo_dirs_delete = github_dict.get('repo-dirs-delete', {})
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

                # also add in findings templates if a findings-{prj_name}.json file exists
                findingsFilename = getFindingsProjectFilename(scaffoldHome, cfg._month, prj._name)
                if os.path.isfile(findingsFilename):
                    prj._findings = loadFindings(findingsFilename)
                else:
                    prj._findings = []

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
        prj._slm_combined_report = prj_slm_dict.get('combinedReport', False)
        prj._slm_extensions_skip = prj_slm_dict.get('extensions-skip', [])
        prj._slm_thirdparty_dirs = prj_slm_dict.get('thirdparty-dirs', [])

        # build policies
        prj._slm_policies = {}
        policies = prj_slm_dict.get('policies', {})
        for policy_name, policy_dict in policies.items():
            policy = SLMPolicy()
            policy._name = policy_name
            # for each policy, build category configs
            policy._category_configs = []
            categories = policy_dict.get('categories', [])
            for category_dict in categories:
                cat = SLMCategoryConfig()
                cat._name = category_dict.get('name', "")
                if cat._name == "":
                    print(f'SLM category in project {prj._name}, policy {policy_name} has no name')
                    prj._ok = False
                cat._license_configs = []
                licenses = category_dict.get('licenses', [])
                for license_dict in licenses:
                    lic = SLMLicenseConfig()
                    lic._name = license_dict.get('name', "")
                    if lic._name == "":
                        print(f'SLM license in project {prj._name}, policy {policy_name}, category {cat._name} has no name')
                        prj._ok = False
                    lic._aliases = license_dict.get('aliases', [])
                    cat._license_configs.append(lic)
                policy._category_configs.append(cat)
            # also get list of categories that are flagged
            policy._flag_categories = policy_dict.get('flagged', [])
            prj._slm_policies[policy_name] = policy

        # check that there's at least one policy
        if len(prj._slm_policies) < 1:
            print(f'Project {prj._name} has no slm policies')
            prj._ok = False
        # check that there's no more than one policy if this project needs
        # a combined report
        if len(prj._slm_policies) > 1 and prj._slm_combined_report == True:
            print(f'Project {prj._name} has more than one slm policy, but wants a combined report; invalid')
            prj._ok = False

def parseProjectWebConfig(prj_dict, prj):
    prj_web_dict = prj_dict.get('web', {})
    # it's okay if there's no web report data; possible we just haven't created it yet
    # but if there is data for a project without a combined report, that's wrong
    if prj._slm_combined_report == False and prj_web_dict != {}:
        print(f'Project {prj._name} has web report data but has slm:combinedReport == False')
        prj._ok = False
        return

    # load data -- fine if it's missing or empty, since we might not
    # be at the report creation stage yet
    prj._web_combined_uuid = prj_web_dict.get('uuid', "")
    prj._web_combined_html_url = prj_web_dict.get('htmlurl', "")
    prj._web_combined_xlsx_url = prj_web_dict.get('xlsxurl', "")

def parseSubprojectSLMConfig(sp_dict, prj, sp):
    sp_slm_dict = sp_dict.get('slm', {})
    if sp_slm_dict == {}:
        sp._slm_policy_name = ""
        sp._slm_report_xlsx = []
        sp._slm_report_json = []
        sp._slm_pending_lics = []
    else:
        # we did get an slm section, so we'll parse it
        sp._slm_policy_name = sp_slm_dict.get('policy', "")
        sp._slm_report_xlsx = sp_slm_dict.get('report-xlsx', "")
        sp._slm_report_json = sp_slm_dict.get('report-json', "")
        sp._slm_pending_lics = sp_slm_dict.get('licenses-pending', [])

        # check whether there's only one slm policy, if no name is given
        # or check whether slm policy name is known, if one is given
        if sp._slm_policy_name == "":
            if len(prj._slm_policies) > 1:
                print(f'Project {prj._name} has multiple slm policies but no policy is specified for subproject {sp._name}')
                sp._ok = False
                prj._ok = False
        else:
            if sp._slm_policy_name not in prj._slm_policies:
                print(f'Project {prj._name} does not have slm policy named "{sp._slm_policy_name}", specified for subproject {sp._name}')
                sp._ok = False
                prj._ok = False


class ConfigJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, Config):
            return {
                "config": {
                    "storepath": o._storepath,
                    "month": o._month,
                    "version": o._version,
                    "spdxGithubOrg": o._spdx_github_org,
                    "spdxGithubSignoff": o._spdx_github_signoff,
                    "webServer": o._web_server,
                    "webReportsPath": o._web_reports_path,
                    "webReportsUrl": o._web_reports_url,
                },
                "projects": o._projects,
                # DO NOT OUTPUT _GH_OAUTH_TOKEN TO CONFIG.JSON
            }

        elif isinstance(o, Project):
            retval = {}

            # build ticket data, if any
            if o._ticket_type == TicketType.JIRA:
                retval["ticket-type"] = "jira"

            # build SLM data
            slm_section = {
                "policies": o._slm_policies,
                "combinedReport": o._slm_combined_report,
                "extensions-skip": o._slm_extensions_skip,
                "thirdparty-dirs": o._slm_thirdparty_dirs,
            }
            retval["slm"] = slm_section

            if o._slm_combined_report == True:
                if o._web_combined_uuid != "" or o._web_combined_html_url != "" or o._web_combined_xlsx_url!= "":
                    web_section = {
                        "uuid": o._web_combined_uuid,
                        "htmlurl": o._web_combined_html_url,
                        "xlsxurl": o._web_combined_xlsx_url,
                    }
                    retval["web"] = web_section

            if o._repotype == ProjectRepoType.GITHUB:
                retval["type"] = "github"
                retval["subprojects"] = o._subprojects
                return retval
            elif o._repotype == ProjectRepoType.GERRIT:
                retval["type"] = "gerrit"
                retval["status"] = o._status.name
                retval["gerrit"] = {
                    "apiurl": o._gerrit_apiurl,
                    "subproject-config": o._gerrit_subproject_config,
                    "repos-ignore": o._gerrit_repos_ignore,
                    "repos-pending": o._gerrit_repos_pending,
                }
                retval["subprojects"] = o._subprojects
                return retval
            elif o._repotype == ProjectRepoType.GITHUB_SHARED:
                retval["type"] = "github-shared"
                retval["status"] = o._status.name
                retval["github-shared"] = {
                    "org": o._github_shared_org,
                    "repos-ignore": o._github_shared_repos_ignore,
                    "repos-pending": o._github_shared_repos_pending,
                }
                retval["subprojects"] = o._subprojects
                return retval
            else:
                return {
                    "type": "unknown"
                }

        elif isinstance(o, Subproject):
            # build SLM data
            slm_section = {}
            if o._slm_policy_name != "":
                slm_section["policy"] = o._slm_policy_name
            if o._slm_report_json != "":
                slm_section["report-json"] = o._slm_report_json
            if o._slm_report_xlsx != "":
                slm_section["report-xlsx"] = o._slm_report_xlsx
            if o._slm_pending_lics != []:
                slm_section["licenses-pending"] = o._slm_pending_lics

            if o._repotype == ProjectRepoType.GITHUB:
                js = {
                    "status": o._status.name,
                    "slm": slm_section,
                    "code": {
                        "anyfiles": o._code_anyfiles,
                    },
                    "web": {},
                    "github": {
                        "org": o._github_org,
                        "ziporg": o._github_ziporg,
                        "repo-dirs-delete": o._repo_dirs_delete,
                        "repos": sorted(o._repos),
                        "repos-ignore": sorted(o._github_repos_ignore),
                    }
                }
                if o._code_pulled != "":
                    js["code"]["pulled"] = o._code_pulled
                if o._code_path != "":
                    js["code"]["path"] = o._code_path
                if o._code_repos != {}:
                    js["code"]["repos"] = o._code_repos
                if o._web_html_url != "":
                    js["web"]["htmlurl"] = o._web_html_url
                if o._web_xlsx_url != "":
                    js["web"]["xlsxurl"] = o._web_xlsx_url
                if o._web_uuid != "":
                    js["web"]["uuid"] = o._web_uuid
                if len(o._github_repos_pending) > 0:
                    js["github"]["repos-pending"] = sorted(o._github_repos_pending)
                return js
            elif o._repotype == ProjectRepoType.GITHUB_SHARED:
                js = {
                    "status": o._status.name,
                    "slm": slm_section,
                    "web": {},
                    "code": {
                        "anyfiles": o._code_anyfiles,
                    },
                    "github-shared": {
                        "repo-dirs-delete": o._repo_dirs_delete,
                        "repos": sorted(o._repos),
                    }
                }
                if o._code_pulled != "":
                    js["code"]["pulled"] = o._code_pulled
                if o._code_path != "":
                    js["code"]["path"] = o._code_path
                if o._code_repos != {}:
                    js["code"]["repos"] = o._code_repos
                if o._web_html_url != "":
                    js["web"]["htmlurl"] = o._web_html_url
                if o._web_xlsx_url != "":
                    js["web"]["xlsxurl"] = o._web_xlsx_url
                if o._web_uuid != "":
                    js["web"]["uuid"] = o._web_uuid
                return js
            elif o._repotype == ProjectRepoType.GERRIT:
                js = {
                    "status": o._status.name,
                    "slm": slm_section,
                    "web": {},
                    "code": {
                        "anyfiles": o._code_anyfiles,
                    },
                    "gerrit": {
                        "repo-dirs-delete": o._repo_dirs_delete,
                        "repos": sorted(o._repos),
                    }
                }
                if o._code_pulled != "":
                    js["code"]["pulled"] = o._code_pulled
                if o._code_path != "":
                    js["code"]["path"] = o._code_path
                if o._code_repos != {}:
                    js["code"]["repos"] = o._code_repos
                if o._web_html_url != "":
                    js["web"]["htmlurl"] = o._web_html_url
                if o._web_xlsx_url != "":
                    js["web"]["xlsxurl"] = o._web_xlsx_url
                if o._web_uuid != "":
                    js["web"]["uuid"] = o._web_uuid
                return js
            else:
                return {
                    "type": "unknown"
                }

        elif isinstance(o, SLMPolicy):
            return {
                "categories": o._category_configs,
                "flagged": o._flag_categories,
            }

        elif isinstance(o, SLMCategoryConfig):
            return {
                "name": o._name,
                "licenses": o._license_configs,
            }

        elif isinstance(o, SLMLicenseConfig):
            return {
                "name": o._name,
                "aliases": o._aliases,
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
