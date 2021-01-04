# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

class ProjectRepoType(Enum):
    UNKNOWN = 0
    GERRIT = 1
    GITHUB = 2
    GITHUB_SHARED = 3

class Status(Enum):
    UNKNOWN = 0
    START = 1
    GOTLISTING = 2
    GOTCODE = 3
    ZIPPEDCODE = 4
    UPLOADEDWS = 5
    UPLOADEDCODE = 6
    RANAGENTS = 7
    CLEARED = 8
    GOTSPDX = 9
    PARSEDSPDX = 10
    CREATEDREPORTS = 11
    MADEDRAFTFINDINGS = 12
    APPROVEDFINDINGS = 13
    MADEFINALFINDINGS = 14
    UPLOADEDSPDX = 15
    UPLOADEDREPORTS = 16
    FILEDTICKETS = 17
    DELIVERED = 18
    STOPPED = 90
    MAX = 99

class Priority(Enum):
    UNKNOWN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERYHIGH = 4

class TicketType(Enum):
    NONE = 0
    JIRA = 1

class MatchText:

    def __init__(self):
        super(MatchText, self).__init__()

        self._text = ""
        self._comment = ""
        self._actions = []

class Finding:

    def __init__(self):
        super(Finding, self).__init__()

        # loaded from findings file
        self._id = -1
        self._priority = Priority.UNKNOWN
        self._matches_path = []
        self._matches_license = []
        self._matches_subproject = []
        self._title = ""
        self._text = ""

class Instance:

    def __init__(self):
        super(Instance, self).__init__()

        # ID of parent Finding that this refers to
        self._finding_id = -1

        # Priority of finding
        # FIXME this is temporary, for purposes of sorting in findings.py
        # FIXME should find a different solution
        self._priority = Priority.UNKNOWN

        # determined based on analysis
        self._files = []

        # determined based on analysis, for subprojects w/out specific files
        self._subprojects = []

        # year-month where this instance was first reported for this project
        self._first = ""

        # is this a new instance (true) or a repeat instance (false)?
        self._isnew = True

        # if not new, did the list of files change? ignore if new
        self._files_changed = False

        # if using JIRA, what is the JIRA ticket ID?
        self._jira_id = ""


class InstanceSet:

    def __init__(self):
        super(InstanceSet, self).__init__()

        # list of instances that are flagged
        self._flagged = []

        # list of files that are unflagged
        self._unflagged = []


# represents a set of metrics for a single subproject in one monthly pull
class Metrics:

    def __init__(self):
        super(Metrics, self).__init__()

        # project name
        self._prj_name = ""

        # subproject name
        self._sp_name = ""

        # categorized state
        # one of "inproc", "analyzed", "uploaded", "delivered", "stopped", "unknown"
        self._state_category = ""

        # total number of unpacked files
        self._unpacked_files = 0

        # total number of repos
        self._num_repos = 0

        # total number of instances by priority
        self._instances_veryhigh = 0
        self._instances_high = 0
        self._instances_medium = 0
        self._instances_low = 0
        # and corresponding file counts
        self._files_veryhigh = 0
        self._files_high = 0
        self._files_medium = 0
        self._files_low = 0


class SLMLicenseConfig:

    def __init__(self):
        super(SLMLicenseConfig, self).__init__()

        self._name = ""
        self._aliases = []


class SLMCategoryConfig:

    def __init__(self):
        super(SLMCategoryConfig, self).__init__()

        self._name = ""
        self._license_configs = []


class SLMFile:

    def __init__(self):
        super(SLMFile, self).__init__()

        self._path = ""
        self._findings = {}


class SLMLicense:

    def __init__(self):
        super(SLMLicense, self).__init__()

        self._name = ""
        self._files = []
        self._numfiles = 0


class SLMCategory:

    def __init__(self):
        super(SLMCategory, self).__init__()

        self._name = ""
        self._licenses = []
        self._numfiles = 0


class SLMPolicy:

    def __init__(self):
        super(SLMPolicy, self).__init__()

        self._name = ""
        # list of SLMCategoryConfigs for this policy
        self._category_configs = []
        self._flag_categories = []


class Project:

    def __init__(self):
        super(Project, self).__init__()

        self._ok = False
        self._name = ""
        self._repotype = ProjectRepoType.UNKNOWN
        self._status = Status.UNKNOWN

        self._subprojects = {}

        self._matches = []
        self._findings = []

        # cycle to run scans
        # 0 = every month, 1 = first month in each calendar quarter, 2 = second month, etc.
        self._cycle = 0

        # only if Gerrit
        self._gerrit_apiurl = ""
        self._gerrit_subproject_config = "manual"
        self._gerrit_repos_ignore = []
        self._gerrit_repos_pending = []

        # only if GITHUB_SHARED
        self._github_shared_org = ""
        self._github_shared_repos_ignore = []
        self._github_shared_repos_pending = []

        # SLM vars
        self._slm_combined_report = False
        # map of names to SLMPolicies
        self._slm_policies = {}
        self._slm_extensions_skip = []
        self._slm_thirdparty_dirs = []

        # WhiteSource vars
        self._ws_enabled = False
        self._ws_env = {}
        ## NOT SAVED, refreshed on each run
        self._ws_product_tokens = {}
        self._ws_project_tokens = {}

        # web upload vars, only for combined reports
        self._web_combined_uuid = ""
        self._web_combined_html_url = ""
        self._web_combined_xlsx_url = ""

        # ticketing type
        self._ticket_type = TicketType.NONE

    def resetNewMonth(self):
        self._status = Status.START

        # reset this-month-only variables
        self._web_combined_uuid = ""
        self._web_combined_html_url = ""
        self._web_combined_xlsx_url = ""

        # tell subprojects to reset
        for sp in self._subprojects.values():
            sp.resetNewMonth()


class Subproject:

    def __init__(self):
        super(Subproject, self).__init__()

        self._ok = False
        self._name = ""
        self._repotype = ProjectRepoType.UNKNOWN
        self._status = Status.UNKNOWN
        self._repos = []
        # mapping of repo name to list of directories to delete
        self._repo_dirs_delete = {}

        # cycle to run scans
        # 0 = every month, 1 = first month in each calendar quarter, 2 = second month, etc.
        self._cycle = 0

        self._code_pulled = ""
        self._code_path = ""
        self._code_anyfiles = False
        # mapping of repo name to pulled commit hash
        self._code_repos = {}

        # only if GitHub
        self._github_org = ""
        self._github_ziporg = ""
        self._github_branch = ""
        self._github_repos_ignore = []
        self._github_repos_pending = []

        # SLM vars
        self._slm_policy_name = ""
        self._slm_report_xlsx = ""
        self._slm_report_json = ""
        self._slm_pending_lics = []

        # WS vars
        self._ws_env = {}
        self._ws_override_disable_anyway = False
        self._ws_override_product = ""
        self._ws_override_project = ""

        # web upload vars
        self._web_uuid = ""
        self._web_html_url = ""
        self._web_xlsx_url = ""

    def resetNewMonth(self):
        self._status = Status.START

        # reset code retrieval vars
        self._code_pulled = ""
        self._code_path = ""
        self._code_anyfiles = False
        self._code_repos = {}

        # reset scan-dependent SLM vars
        self._slm_report_xlsx = ""
        self._slm_report_json = ""
        self._slm_pending_lics = []

        # reset web upload vars
        self._web_uuid = ""
        self._web_html_url = ""
        self._web_xlsx_url = ""


class JiraSecret:

    def __init__(self):
        super(JiraSecret, self).__init__()

        self._project_name = ""
        self._jira_project = ""
        self._server = ""
        self._username = ""
        self._password = ""


class WSSecret:

    def __init__(self):
        super(WSSecret, self).__init__()

        self._project_name = ""
        self._ws_api_key = ""
        self._ws_user_key = ""
        # overrides of API key for particular subprojects
        # hash of sp name to API key
        self._ws_api_key_overrides = {}


class Secrets:

    def __init__(self):
        super(Secrets, self).__init__()

        # mapping of project name to jira server details
        self._jira = {}

        # mapping of project name to WhiteSource server details
        self._ws = {}


class Config:

    def __init__(self):
        super(Config, self).__init__()

        self._ok = False
        self._storepath = ""
        self._projects = {}
        self._month = ""
        self._version = 0
        self._spdx_github_org = ""
        self._spdx_github_signoff = ""
        self._web_server = ""
        self._web_reports_path = ""
        self._web_reports_url = ""
        self._ws_server_url = ""
        self._ws_unified_agent_jar_path = ""
        self._ws_default_env = {}
        # DO NOT OUTPUT THESE TO CONFIG.JSON
        self._gh_oauth_token = ""
        self._secrets = None

    def __repr__(self):
        is_ok = "OK"
        if self._ok == False:
            is_ok = "NOT OK"

        return f"Config ({is_ok}): {self._storepath}, PROJECTS: {self._projects}"
