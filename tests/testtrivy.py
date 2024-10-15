import unittest
import os
import tempfile
import shutil
import git
import zipfile
from datetime import datetime
from manualtrivy import runManualTrivyAgent
from trivyagent import installNpm
from config import loadConfig, saveConfig
from datatypes import Status, ProjectRepoType
from zipcode import doZipRepoCodeForSubproject

ANALYSIS_FILE_FRAGMENT = "sp1-2023-07"
ANALYSIS_FILE_NAME = ANALYSIS_FILE_FRAGMENT + "-09.zip"
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_CODE = os.path.join(os.path.dirname(__file__), "testresources", ANALYSIS_FILE_NAME)
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
SIMPLE_NPM_ZIP = os.path.join(os.path.dirname(__file__), "testresources", "simplenpm.zip")
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
        if 'TRIVY_EXEC_PATH' in os.environ:
            self.saved_trivy = os.environ['TRIVY_EXEC_PATH']
        else:
            self.saved_trivy = None
            os.environ['TRIVY_EXEC_PATH'] = 'trivy' # default
        if 'NPM_EXEC_PATH' in os.environ:
            self.saved_npm = os.environ['NPM_EXEC_PATH']
        else:
            self.saved_npm = None
            os.environ['NPM_EXEC_PATH'] = 'npm' # default
        self.npm_path = os.path.join(self.temp_dir.name, 'simplenpm')
        with zipfile.ZipFile(SIMPLE_NPM_ZIP, mode='r') as zip:
            zip.extractall(self.temp_dir.name)
        self.node_modules_path = os.path.join(self.npm_path, 'node_modules')
        self.uuid_package_json_path = os.path.join(self.node_modules_path, 'uuid/package.json')
        
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
            if self.saved_trivy is None:
                del os.environ['TRIVY_EXEC_PATH']
            else:
                os.environ['TRIVY_EXEC_PATH'] = self.saved_trivy

    def tearDown(self):
        self._cleanGitClone(self.project_repo_dir)
        self.temp_dir.cleanup()
        if self.saved_trivy:
            os.environ['TRIVY_EXEC_PATH'] = self.saved_trivy
        elif 'TRIVY_EXEC_PATH' in os.environ:
            del os.environ['TRIVY_EXEC_PATH']
        if self.saved_npm:
            os.environ['NPM_EXEC_PATH'] = self.saved_npm
        elif 'NPM_EXEC_PATH' in os.environ:
            del os.environ['NPM_EXEC_PATH']
            

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
        sp._code_pulled = "2024-08-21"
        sp._code_anyfiles = True
        sp._code_repos = {self.repoName: "153a803c46181319fd782ef8426ff58a2e885d82"}
        
        result = runManualTrivyAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        uploadedfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{prj._name}-{sp._name}-spdx.json")
        self.assertTrue(os.path.isfile(uploadedfile))
        reportfile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{prj._name}-{sp._name}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile))
        # TODO: Check if the file is committed and pushed to the repo
        
    def test_npm_install(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[TEST_PROJECT_NAME]
        prj._name = TEST_PROJECT_NAME
        sp = prj._subprojects[TEST_SUBPROJECT_NAME]
        sp._name = TEST_SUBPROJECT_NAME
        self.assertFalse(os.path.isdir(self.node_modules_path))
        installNpm(self.npm_path, cfg, prj, sp)
        self.assertTrue(os.path.isdir(self.node_modules_path))
        self.assertTrue(os.path.isfile(self.uuid_package_json_path))
        
    
    def test_trivy_config(self):
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
        sp._code_pulled = "2024-08-21"
        sp._code_anyfiles = True
        sp._code_repos = {self.repoName: "153a803c46181319fd782ef8426ff58a2e885d82"}
        sp._trivy_exec_path = os.environ['TRIVY_EXEC_PATH']
        os.environ['TRIVY_EXEC_PATH'] = 'somegarbage'
        result = runManualTrivyAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        saved_trivy = sp._trivy_exec_path
        sp._trivy_exec_path = 'somegarbage'
        try:
            result = runManualTrivyAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
            self.assertFalse(result) # More likely to case an exception, but a false return is also OK
        except:
            pass  # expected
        finally:
            os.environ['TRIVY_EXEC_PATH'] = saved_trivy
            
        
if __name__ == '__main__':
    unittest.main()
        