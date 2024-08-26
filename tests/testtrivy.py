import unittest
import os
import tempfile
import shutil
import git
from datetime import datetime
from manualtrivy import runManualTrivyAgent
from config import loadConfig, saveConfig
from datatypes import Status, ProjectRepoType
from zipcode import doZipRepoCodeForSubproject
from pdb import set_trace

ANALYSIS_FILE_FRAGMENT = "sp1-2023-07"
ANALYSIS_FILE_NAME = ANALYSIS_FILE_FRAGMENT + "-09.zip"
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_CODE = os.path.join(os.path.dirname(__file__), "testresources", ANALYSIS_FILE_NAME)
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
TEST_NEXT_MONTH = "2023-08"
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, TEST_MONTH)
TEST_PROJECT_NAME = "TEST-DEPENDENCIES"
TEST_SUBPROJECT_NAME = "sp1"
GITHUB_ORG = 'lfscanning'

'''
Tests Trivy manual agent commands
'''
class TestTrivy(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)
        self.repo_dir = os.path.join(self.scaffold_home_dir, "spdxrepos")
        # setup the git repo
        self.repoName = f"spdx-{TEST_PROJECT_NAME}"
        self.project_repo_dir = os.path.join(self.repo_dir, self.repoName)
        self.git_url = f"git@github.com:{GITHUB_ORG}/{self.repoName}.git"
        git.Git(self.repo_dir).clone(self.git_url, depth=1)
        self._cleanGitClone(self.project_repo_dir)
        
    def _cleanGitClone(self, repo):
        if len(os.listdir(repo)) > 1:
            # the .git directory would be one - any added files would be > 1
            content = []
            for fileName in os.listdir(repo):
                if fileName != '.git':
                    p = os.path.join(repo, fileName)
                    if (os.path.isfile(p)):
                        os.remove(p)
                        content.append(p)
                    elif (os.path.isdir(p)):
                        shutil.rmtree(p)
                        content.append(p)
            # Push the changes to the github repo
            repo = git.Repo(self.project_repo_dir)
            origin = repo.remote(name="origin")
            repo.index.remove(content, r=True)
            commitMsg = "Cleaning up after TestTrivy run"
            repo.index.commit(commitMsg)
            origin.push()

    def tearDown(self):
        self._cleanGitClone(self.project_repo_dir)
        self.temp_dir.cleanup()

    def test_trivy(self):
        
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._zippath = self.temp_dir.name
        cfg._storepath = self.scaffold_home_dir
        cfg._spdx_github_org = GITHUB_ORG
        prj = cfg._projects[TEST_PROJECT_NAME]
        prj._name = TEST_PROJECT_NAME
        sp = prj._subprojects[TEST_SUBPROJECT_NAME]
        sp._name = TEST_SUBPROJECT_NAME
        sp._repos = [self.repoName]
        sp._repotype = ProjectRepoType.GITHUB
        sp._github_org = GITHUB_ORG
        sp._github_ziporg = GITHUB_ORG
        sp._github_branch = ""
        sp._status = Status.ZIPPEDCODE
        sp._code_path = TEST_SCAFFOLD_CODE
        result = runManualTrivyAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        uploadedfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{prj._name}-{sp._name}-spdx.json")
        set_trace()
        self.assertTrue(os.path.isfile(uploadedfile))
        # TODO: Check if the file is committed and pushed to the repo
        
if __name__ == '__main__':
    unittest.main()
        