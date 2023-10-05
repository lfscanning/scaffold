# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import json
import os
from pathlib import Path
from shutil import copyfile
from datetime import date

import yaml

from datatypes import Config, Finding, JiraSecret, MatchText, Priority, Project, ProjectRepoType, Secrets, SLMCategoryConfig, SLMLicenseConfig, SLMPolicy, Status, Subproject, TicketType, WSSecret

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

def updateFossologyToken(token, expiration, secrets_file_name = ".scaffold-secrets.json"):
    '''
    Update the fossology token in the secrets file
    '''
    secretsFile = os.path.join(Path.home(), secrets_file_name)
    
    js = {}
    with open(secretsFile, 'r') as f:
        js = json.load(f)

    js['fossology_token'] = token
    js['fossology_token_expiration'] = expiration.strftime('%Y-%m-%d')
    with open(secretsFile, "w") as f:
        json.dump(js, f, indent=4)


# parses secrets file
def loadSecrets(secrets_file_name = ".scaffold-secrets.json"):
    secretsFile = os.path.join(Path.home(), secrets_file_name)
    try:
        with open(secretsFile, 'r') as f:
            js = json.load(f)

            secrets = Secrets()
            default_oauth = js.get("default_github_oauth", "")
            secrets._default_oauth = default_oauth
            secrets._fossology_server = js.get("fossology_server")
            if not secrets._fossology_server:
                print('Missing fossology server in ~/.scaffold-secrets.json')
                return None
            secrets._fossology_username = js.get("fossology_username")
            if not secrets._fossology_username:
                print('Missing fossology username in ~/.scaffold-secrets.json')
                return None
            secrets._fossology_password = js.get("fossology_password")
            if not secrets._fossology_password:
                print('Missing fossology password in ~/.scaffold-secrets.json')
                return None
            secrets._fossology_token = js.get("fossology_token")
            expiration = js.get("fossology_token_expiration")
            if not expiration:
                secrets._fossology_token_expiration = date.today()
            else:
                secrets._fossology_token_expiration = date.fromisoformat(js.get("fossology_token_expiration"))
            
            # expecting mapping of prj name to JiraSecret data
            project_data = js.get("projects", {})
            for prj, prj_dict in project_data.items():
                jira_dict = prj_dict.get("jira", {})
                if jira_dict != {}:
                    jira_secret = JiraSecret()
                    jira_secret._project_name = prj
                    jira_secret._jira_project = jira_dict.get("board", "")
                    jira_secret._server = jira_dict.get("server", "")
                    jira_secret._username = jira_dict.get("username", "")
                    jira_secret._password = jira_dict.get("password", "")
                    secrets._jira[prj] = jira_secret

                ws_dict = prj_dict.get("whitesource", {})
                if ws_dict != {}:
                    ws_secret = WSSecret()
                    ws_secret._project_name = prj
                    ws_secret._ws_api_key = ws_dict.get("apikey", "")
                    ws_secret._ws_user_key = ws_dict.get("userkey", "")
                    secrets._ws[prj] = ws_secret
                    
                secrets._gitoauth[prj] = prj_dict.get("github_oauth", default_oauth)

        return secrets

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {secretsFile}: {str(e)}')
        return None

def loadConfig(configFilename, scaffoldHome, secrets_file_name = '.scaffold-secrets.json'):
    cfg = Config()

    try:
        with open(configFilename, 'r') as f:
            js = json.load(f)

            # Save the secret file name
            cfg._secrets_file = secrets_file_name
            # load global config
            config_dict = js.get('config', {})
            if config_dict == {}:
                print(f'No config section found in config file')
                raise RuntimeError(f'No config section found in config file')
            cfg._month = config_dict.get('month', "")
            if cfg._month == "":
                print(f'No valid month found in config section')
                raise RuntimeError(f'No valid month found in config section')
            cfg._version = config_dict.get('version', -1)
            if cfg._version == -1:
                print(f'No valid version found in config section')
                raise RuntimeError(f'No valid version found in config section')
            cfg._storepath = config_dict.get('storepath', "")
            if cfg._storepath == "":
                print(f'No valid storepath found in config section')
                raise RuntimeError(f'No valid storepath found in config section')
            cfg._zippath = config_dict.get('zippath', cfg._storepath)
            cfg._spdx_github_org = config_dict.get('spdxGithubOrg', "")
            if cfg._spdx_github_org == "":
                print(f'No valid spdxGithubOrg found in config section')
                raise RuntimeError(f'No valid spdxGithubOrg found in config section')
            cfg._spdx_github_signoff = config_dict.get('spdxGithubSignoff', "")
            if cfg._spdx_github_signoff == "":
                print(f'No valid spdxGithubSignoff found in config section')
                raise RuntimeError(f'No valid spdxGithubSignoff found in config section')

            # load web server data
            cfg._web_server_use_scp = config_dict.get('webServerUseScp', False)
            cfg._web_server = config_dict.get('webServer', "")
            if cfg._web_server == "":
                print(f"No valid webServer found in config section")
                raise RuntimeError(f"No valid webServer found in config section")
            cfg._web_server_username = config_dict.get('webServerUsername', "")
            if cfg._web_server_username == "" and cfg._web_server_use_scp:
                print(f"No valid webServerUsername found in config section")
                raise RuntimeError(f"No valid webServerUsername found in config section")
            cfg._web_reports_path = config_dict.get('webReportsPath', "")
            if cfg._web_reports_path == "":
                print(f"No valid webReportsPath found in config section")
                raise RuntimeError(f"No valid webReportsPath found in config section")
            cfg._web_reports_url = config_dict.get('webReportsUrl', "")
            if cfg._web_reports_url == "":
                print(f"No valid webReportsUrl found in config section")
                raise RuntimeError(f"No valid webReportsUrl found in config section")

            # load config-wide WhiteSource data
            cfg._ws_server_url = config_dict.get('wsServerUrl', "")
            if cfg._ws_server_url == "":
                print(f"No valid wsServerUrl found in config section")
                raise RuntimeError(f"No valid wsServerUrl found in config section")
            cfg._ws_unified_agent_jar_path = config_dict.get('wsUnifiedAgentJarPath', "")
            if cfg._ws_unified_agent_jar_path == "":
                print(f"No valid wsUnifiedAgentJarPath found in config section")
                raise RuntimeError(f"No valid wsUnifiedAgentJarPath found in config section")
            # default_env does not need to exist
            cfg._ws_default_env = config_dict.get('wsDefaultEnv', {})
            
            # load FOSSOlogy job specified
            defaultJobSpec = {
                                "analysis": {
                                    "bucket": False,
                                    "copyright_email_author": True,
                                    "ecc": False,
                                    "keyword": False,
                                    "mime": False,
                                    "monk": True,
                                    "nomos": True,
                                    "ojo": False,
                                    "package": False,
                                    "specific_agent": False,
                                },
                                "decider": {
                                    "nomos_monk": False,
                                    "bulk_reused": True,
                                    "new_scanner": False,
                                    "ojo_decider": False,
                                },
                            }
            cfg._fossology_job_spec = config_dict.get('fossologyJobSpec', defaultJobSpec)

            # load secrets
            cfg._secrets = loadSecrets(secrets_file_name)

            # if we get here, main config is at least valid
            cfg._ok = True

            # load projects
            projects_dict = js.get('projects', {})
            if projects_dict == {}:
                print(f'No projects found in config file')
                raise RuntimeError(f'No projects found in config file')

            for prj_name, prj_dict in projects_dict.items():
                #TODO: Refactor this function - cognative and cyclomatic complexity is high
                prj = Project()
                prj._name = prj_name
                prj._ok = True
                if not prj_name in cfg._secrets._gitoauth:
                # Update the secrets for any missing project data
                    cfg._secrets._gitoauth[prj_name] = cfg._secrets._default_oauth
                
                prj._cycle = prj_dict.get('cycle', 99)

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

                    # now load WS project data
                    parseProjectWSConfig(prj_dict, prj)

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

                            sp._cycle = sp_dict.get('cycle', 99)
                            if prj._cycle != 99 and sp._cycle != 99:
                                print(f"Project {prj_name} and subproject {sp_name} both have cycles specified; invalid")
                                prj._ok = False
                                sp._ok = False
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

                            # now load WS subproject data
                            parseSubprojectWSConfig(sp_dict, prj, sp)

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

                    # now load WS project data
                    parseProjectWSConfig(prj_dict, prj)

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

                            sp._cycle = sp_dict.get('cycle', 99)
                            if prj._cycle != 99 and sp._cycle != 99:
                                print(f"Project {prj_name} and subproject {sp_name} both have cycles specified; invalid")
                                prj._ok = False
                                sp._ok = False

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

                            # now load WS subproject data
                            parseSubprojectWSConfig(sp_dict, prj, sp)

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

                    # now load WS project data
                    parseProjectWSConfig(prj_dict, prj)

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

                            sp._cycle = sp_dict.get('cycle', 99)
                            if prj._cycle != 99 and sp._cycle != 99:
                                print(f"Project {prj_name} and subproject {sp_name} both have cycles specified; invalid")
                                prj._ok = False
                                sp._ok = False

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

                            # now load WS subproject data
                            parseSubprojectWSConfig(sp_dict, prj, sp)

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
                                # if no branch specified, that's fine
                                sp._github_branch = github_dict.get('branch', "")
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

def parseProjectWSConfig(prj_dict, prj):
    prj_ws_dict = prj_dict.get('ws', {})
    if prj_ws_dict == {}:
        return

    # load data -- fine if missing or empty, since we might not
    # have WhiteSource configured for this project
    prj._ws_enabled = prj_ws_dict.get("enabled", False)
    prj._ws_env = prj_ws_dict.get("env", {})

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
        sp._slm_report_xlsx = ""
        sp._slm_report_json = ""
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

def parseSubprojectWSConfig(sp_dict, prj, sp):
    sp_ws_dict = sp_dict.get('ws', {})
    if sp_ws_dict == {}:
        return

    # load data -- fine if missing or empty, since we might not
    # have WhiteSource configured for this project
    sp._ws_override_disable_anyway = sp_ws_dict.get("override-disable-anyway", False)
    sp._ws_override_product = sp_ws_dict.get("override-product", "")
    sp._ws_override_project = sp_ws_dict.get("override-project", "")
    sp._ws_env = sp_ws_dict.get("env", {})

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
                    "webServerUsername": o._web_server_username,
                    "webReportsPath": o._web_reports_path,
                    "webReportsUrl": o._web_reports_url,
                    "wsServerUrl": o._ws_server_url,
                    "wsUnifiedAgentJarPath": o._ws_unified_agent_jar_path,
                    "wsDefaultEnv": o._ws_default_env,
                    "fossologyJobSpec": o._fossology_job_spec,
                },
                "projects": o._projects,
            }

        elif isinstance(o, Project):
            retval = {}

            if o._cycle != 99:
                retval["cycle"] = o._cycle

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

            # build WS data
            ws_section = {"enabled": o._ws_enabled}
            if o._ws_env != {}:
                ws_section["env"] = o._ws_env
            if ws_section != {"enabled": False}:
                retval["ws"] = ws_section

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

            # build WS data
            ws_section = {}
            if o._ws_override_disable_anyway != False:
                ws_section["override-disable-anyway"] = o._ws_override_disable_anyway
            if o._ws_override_product != "":
                ws_section["override-product"] = o._ws_override_product
            if o._ws_override_project != "":
                ws_section["override-project"] = o._ws_override_project
            if o._ws_env != {}:
                ws_section["env"] = o._ws_env

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
                if o._github_branch != "":
                    js["github"]["branch"] = o._github_branch
                if ws_section != {}:
                    js["ws"] = ws_section
                if o._cycle != 99:
                    js["cycle"] = o._cycle
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
                if ws_section != {}:
                    js["ws"] = ws_section
                if o._cycle != 99:
                    js["cycle"] = o._cycle
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
                if ws_section != {}:
                    js["ws"] = ws_section
                if o._cycle != 99:
                    js["cycle"] = o._cycle
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

def isInThisCycle(cfg, prj, sp):
    cycle = 99
    # shouldn't have both prj._cycle and sp._cycle set at the same time;
    # JSON loader validates this so we'll ignore it here (not sure how
    # to best handle here)
    if prj._cycle != 99:
        cycle = prj._cycle
    if sp is not None and sp._cycle != 99:
        cycle = sp._cycle
    if cycle == 0 or cycle == 99:
        return True

    mth = cfg._month[5:7]
    if cycle == 1 and mth in ['01', '04', '07', '10']:
        return True
    if cycle == 2 and mth in ['02', '05', '08', '11']:
        return True
    if cycle == 3 and mth in ['03', '06', '09', '10']:
        return True
    return False
