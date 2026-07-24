import filecmp
import time

import git
import os
import shutil
import tempfile
import unittest
from config import loadConfig
from uploadspdx import doUploadSPDXForSubproject

GITHUB_ORG = 'lfscanning'
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
SUBPROJECT_NAME = 'sp1'
PROJECT_NAME = 'TEST-DEPENDENCIES'
CODE_PULLED = TEST_MONTH + '-10'
TEST_SPDX_FILE = os.path.join(os.path.dirname(__file__), "testresources", "testfossology.spdx")

class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)
        self.spdx_dir = os.path.join(self.config_month_dir, "spdx")
        self.spdx_dir_path = os.path.join(self.spdx_dir, PROJECT_NAME)
        self.spdx_file_name = f"{SUBPROJECT_NAME}-{CODE_PULLED}.spdx"
        self.spdx_file_path = os.path.join(self.spdx_dir_path, self.spdx_file_name)
        os.makedirs(self.spdx_dir_path)
        shutil.copyfile(TEST_SPDX_FILE, self.spdx_file_path)
        self.repo_dir = os.path.join(self.scaffold_home_dir, "spdxrepos")
        os.mkdir(self.repo_dir)
        # setup the git repo
        self.repoName = f"spdx-{PROJECT_NAME}"
        self.project_repo_dir = os.path.join(self.repo_dir, self.repoName)
        self.git_url = f"git@github.com:{GITHUB_ORG}/{self.repoName}.git"
        git.Git(self.repo_dir).clone(self.git_url, depth=1)
        self._cleanGitClone(self.project_repo_dir)
        self.reports_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report")
        os.makedirs(self.reports_dir)

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
            commitMsg = "Cleaning up after TestSbom run"
            repo.index.commit(commitMsg)
            origin.push()
            del repo

    def tearDown(self):
        self._cleanGitClone(self.project_repo_dir)
        done = False
        iterations = 0
        while not done and iterations < 10:
            try:
                self.temp_dir.cleanup()
                done = True
            except Exception as e:
                # This seems to be caused by Git not going away - see https://github.com/gitpython-developers/GitPython/issues/287
                print("Clean up failed - retrying...")
                time.sleep(1)
                iterations = iterations + 1

    def test_private_sbom(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[PROJECT_NAME]
        prj._name = PROJECT_NAME
        sp = prj._subprojects[SUBPROJECT_NAME]
        sp._name = SUBPROJECT_NAME
        sp._code_pulled = CODE_PULLED
        sp._reports_private = True
        cfg._storepath = self.scaffold_home_dir
        self.assertTrue(doUploadSPDXForSubproject(cfg, prj, sp))
        report_spdx_file_path = os.path.join(self.reports_dir, PROJECT_NAME, self.spdx_file_name)
        self.assertTrue(filecmp.cmp(self.spdx_file_path, report_spdx_file_path, shallow=False))

    def test_public_sbom(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[PROJECT_NAME]
        prj._name = PROJECT_NAME
        sp = prj._subprojects[SUBPROJECT_NAME]
        sp._name = SUBPROJECT_NAME
        sp._code_pulled = CODE_PULLED
        sp._reports_private = False
        cfg._storepath = self.scaffold_home_dir
        cfg._spdx_github_org = GITHUB_ORG
        self.assertTrue(doUploadSPDXForSubproject(cfg, prj, sp))
        repo_spdx_file_path = os.path.join(self.repo_dir, self.repoName, SUBPROJECT_NAME, TEST_MONTH, self.spdx_file_name)
        self.assertTrue(filecmp.cmp(self.spdx_file_path, repo_spdx_file_path, shallow=False))
        pass