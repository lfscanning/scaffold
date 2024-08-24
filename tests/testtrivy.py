import unittest
import os
import tempfile
import shutil
from datetime import datetime
from manualtrivy import runManualTrivyAgent
from config import loadConfig, saveConfig
from datatypes import Status, ProjectRepoType
from zipcode import doZipRepoCodeForSubproject

ANALYSIS_FILE_FRAGMENT = "sp1-2023-07"
ANALYSIS_FILE_NAME = ANALYSIS_FILE_FRAGMENT + "-09.zip"
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_CODE = os.path.join(os.path.dirname(__file__), "testresources", ANALYSIS_FILE_NAME)
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
TEST_NEXT_MONTH = "2023-08"
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, TEST_MONTH)

'''
Tests Trivy manual agent commands
'''
class TestTrivy(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_trivy(self):
        repoName = 'TEST-Empty'
        githubOrg = 'lfscanning'
        subProjectName = 'sp1'
        projectName = 'prj1'
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._zippath = self.temp_dir.name
        prj = cfg._projects[projectName]
        prj._name = projectName
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = [repoName]
        sp._repotype = ProjectRepoType.GITHUB
        sp._github_org = githubOrg
        sp._github_ziporg = githubOrg
        sp._github_branch = ""
        sp._status = Status.ZIPPEDCODE
        sp._code_path = TEST_SCAFFOLD_CODE
        runManualTrivyAgent(cfg, projectName, subProjectName) 
        
if __name__ == '__main__':
    unittest.main()
        