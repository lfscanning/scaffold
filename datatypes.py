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
    UPLOADEDCODE = 5
    RANAGENTS = 6
    CLEARED = 7
    GOTSPDX = 8
    IMPORTEDSCAN = 9
    CREATEDREPORTS = 10
    MADEDRAFTFINDINGS = 11
    APPROVEDFINDINGS = 12
    MADEFINALFINDINGS = 13
    UPLOADEDSPDX = 14
    UPLOADEDREPORTS = 15
    DELIVERED = 16
    STOPPED = 90
    MAX = 99

class Priority(Enum):
    UNKNOWN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERYHIGH = 4

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
        self._priority = Priority.UNKNOWN
        self._matches_path = []
        self._matches_license = []
        self._text = ""

class FindingsInstance:

    def __init__(self):
        super(FindingsInstance, self).__init__()

        # parent Finding that this refers to
        self._finding = Finding()

        # determined based on analysis
        self._files = []

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
        self._findingsInstances = []
        self._flag_categories = []

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
        self._slm_shared = True
        self._slm_prj = ""
        self._slm_combined_report = False
    
    def __repr__(self):
        is_ok = "OK"
        if self._ok == False:
            is_ok = "NOT OK"

        if self._repotype == ProjectRepoType.GERRIT:
            return f"{self._name} ({is_ok}): {self._repotype.name}, {self._gerrit_apiurl}, IGNORE: {self._gerrit_repos_ignore}, SUBPROJECTS: {self._subprojects}"
        elif self._repotype == ProjectRepoType.GITHUB_SHARED:
            return f"{self._name} ({is_ok}): {self._repotype.name}, {self._github_shared_org}, IGNORE: {self._github_shared_repos_ignore}, PENDING: {self._github_shared_repos_pending}, SUBPROJECTS: {self._subprojects}"
        else:
            return f"{self._name} ({is_ok}): {self._repotype.name}, SUBPROJECTS: {self._subprojects}"


class Subproject:

    def __init__(self):
        super(Subproject, self).__init__()

        self._ok = False
        self._name = ""
        self._repotype = ProjectRepoType.UNKNOWN
        self._status = Status.UNKNOWN
        self._repos = []

        self._findingsInstances = []

        self._code_pulled = ""
        self._code_path = ""
        self._code_anyfiles = False
        # mapping of repo name to pulled commit hash
        self._code_repos = {}

        # only if GitHub
        self._github_org = ""
        self._github_ziporg = ""
        self._github_repos_ignore = []
        self._github_repos_pending = []

        # SLM vars
        self._slm_prj = ""  # only if project's _slm_shared == False
        self._slm_sp = ""
        self._slm_scan_id = -1
        self._slm_pending_lics = []

        # web upload vars
        self._web_uuid = ""
        self._web_html_url = ""
        self._web_xlsx_url = ""

    def __repr__(self):
        is_ok = "OK"
        if self._ok == False:
            is_ok = "NOT OK"

        if self._repotype == ProjectRepoType.GITHUB:
            return f"{self._name} ({is_ok}): {self._repotype.name}, {self._github_org}, {self._github_ziporg}, {self._repos}, IGNORE: {self._github_repos_ignore}, PENDING: {self._github_repos_pending}"
        elif self._repotype == ProjectRepoType.GERRIT:
            return f"{self._name} ({is_ok}): STATUS: {self._status}, {self._repotype.name}, {self._repos}"
        else:
            return f"{self._name} ({is_ok}): {self._repotype.name}, {self._repos}"

class Config:

    def __init__(self):
        super(Config, self).__init__()

        self._ok = False
        self._storepath = ""
        self._projects = {}
        self._month = ""
        self._version = 0
        self._slm_home = ""
        self._spdx_github_org = ""
        self._spdx_github_signoff = ""
        self._web_server = ""
        self._web_reports_path = ""
        self._web_reports_url = ""
        # DO NOT OUTPUT THIS TO CONFIG.JSON
        self._gh_oauth_token = ""

    def __repr__(self):
        is_ok = "OK"
        if self._ok == False:
            is_ok = "NOT OK"

        return f"Config ({is_ok}): {self._storepath}, PROJECTS: {self._projects}"
