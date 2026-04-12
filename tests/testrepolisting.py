import unittest
import os
import tempfile
import shutil
from config import loadConfig
from datatypes import ProjectRepoType
from repolisting import doRepoListingForSubproject, doRepoListingForProject

SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
TEST_NEXT_MONTH = "2023-08"
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, TEST_MONTH)
GITHUB_ORG = 'lfscanning'
ARCHIVED_LFSCANNING_REPO = 'TEST-Archived'
ARCHIVED_LFSCANNING_REPO2 = 'TEST-Archived-2'
EXISTING_LFSCANNING_REPOS = ['scaffold', 'spdx-TEST-DEPENDENCIES', 'spdx-o-ran']
IGNORED_OTHER_LFSCANNING_REPOS = ['spdx-omp', 'spdx-OWF', 'spdx-lfenergy']
LFSCANNING_REPOS_NOT_IN_CONFIG = ['spdx-lfai', 'spdx-cncf']

class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_repo_listing_for_project(self):
        subProjectName = 'sp1'
        projectName = 'prj1'
        pendingToRemove = 'pendingRepoToRemove'
        ignoreToRemove = 'ignoreToRepoToRemove'
        repoToRemove = 'repoToRemove'
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[projectName]
        prj._name = projectName
        prj._repotype = ProjectRepoType.GITHUB_SHARED
        prj._github_shared_org = GITHUB_ORG
        prj._github_shared_repos_ignore = IGNORED_OTHER_LFSCANNING_REPOS
        prj._github_shared_repos_ignore.append(ignoreToRemove)
        prj._github_shared_repos_pending = [pendingToRemove]
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = EXISTING_LFSCANNING_REPOS
        sp._repos.append(ARCHIVED_LFSCANNING_REPO)
        self.assertFalse(doRepoListingForProject(cfg,prj))
        self.assertTrue(set(EXISTING_LFSCANNING_REPOS).issubset(sp._repos))
        self.assertFalse(repoToRemove in sp._repos)
        self.assertFalse(ARCHIVED_LFSCANNING_REPO in sp._repos)
        self.assertTrue(ARCHIVED_LFSCANNING_REPO in prj._github_shared_repos_ignore)
        self.assertFalse(ARCHIVED_LFSCANNING_REPO2 in sp._repos)
        self.assertTrue(ARCHIVED_LFSCANNING_REPO2 in prj._github_shared_repos_ignore)
        self.assertTrue(set(LFSCANNING_REPOS_NOT_IN_CONFIG).issubset(prj._github_shared_repos_pending))
        self.assertTrue(set(EXISTING_LFSCANNING_REPOS).isdisjoint(prj._github_shared_repos_pending))
        self.assertTrue(set(IGNORED_OTHER_LFSCANNING_REPOS).isdisjoint(prj._github_shared_repos_pending))
        self.assertGreater(len(prj._github_shared_repos_pending), 15)
        self.assertFalse(ignoreToRemove in prj._github_shared_repos_ignore)

    def test_missing_repo_project(self):
        subProjectName = 'sp1'
        projectName = 'prj1'
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[projectName]
        prj._name = projectName
        prj._repotype = ProjectRepoType.GITHUB_SHARED
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = EXISTING_LFSCANNING_REPOS
        sp._repotype = ProjectRepoType.GITHUB
        not_a_github_org = "ThisIsNotAGitHubOrg"
        prj._github_shared_org = not_a_github_org
        sp._github_org = not_a_github_org
        sp._github_ziporg = not_a_github_org
        sp._github_branch = ""
        self.assertFalse(doRepoListingForProject(cfg,prj))
        self.assertEqual(0, len(sp._github_repos_pending))

    def test_repo_listing_for_subproject(self):
        subProjectName = 'sp1'
        projectName = 'prj1'
        pendingToRemove = 'pendingRepoToRemove'
        ignoreToRemove = 'ignoreToRepoToRemove'
        repoToRemove = 'repoToRemove'
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[projectName]
        prj._name = projectName
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = EXISTING_LFSCANNING_REPOS
        sp._repos.append(ARCHIVED_LFSCANNING_REPO)
        sp._repos.append(repoToRemove)
        sp._github_repos_ignore = IGNORED_OTHER_LFSCANNING_REPOS
        sp._github_repos_ignore.append(ignoreToRemove)
        sp._github_repos_pending = [pendingToRemove]
        sp._repotype = ProjectRepoType.GITHUB
        sp._github_org = GITHUB_ORG
        sp._github_ziporg = GITHUB_ORG
        sp._github_branch = ""
        self.assertFalse(doRepoListingForSubproject(cfg,prj,sp))
        self.assertTrue(set(EXISTING_LFSCANNING_REPOS).issubset(sp._repos))
        self.assertFalse(repoToRemove in sp._repos)
        self.assertFalse(ARCHIVED_LFSCANNING_REPO in sp._repos)
        self.assertTrue(ARCHIVED_LFSCANNING_REPO in sp._github_repos_ignore)
        self.assertFalse(ARCHIVED_LFSCANNING_REPO2 in sp._repos)
        self.assertTrue(ARCHIVED_LFSCANNING_REPO2 in sp._github_repos_ignore)
        self.assertTrue(set(LFSCANNING_REPOS_NOT_IN_CONFIG).issubset(sp._github_repos_pending))
        self.assertTrue(set(EXISTING_LFSCANNING_REPOS).isdisjoint(sp._github_repos_pending))
        self.assertTrue(set(IGNORED_OTHER_LFSCANNING_REPOS).isdisjoint(sp._github_repos_pending))
        self.assertGreater(len(sp._github_repos_pending), 15)
        self.assertFalse(ignoreToRemove in sp._github_repos_ignore)

    def test_missing_repo_subproject(self):
        subProjectName = 'sp1'
        projectName = 'prj1'
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[projectName]
        prj._name = projectName
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = EXISTING_LFSCANNING_REPOS
        sp._repotype = ProjectRepoType.GITHUB
        not_a_github_org = "ThisIsNotAGitHubOrg"
        sp._github_org = not_a_github_org
        sp._github_ziporg = not_a_github_org
        sp._github_branch = ""
        self.assertFalse(doRepoListingForSubproject(cfg,prj,sp))
        self.assertEqual(0, len(sp._github_repos_pending))

if __name__ == '__main__':
    unittest.main()
