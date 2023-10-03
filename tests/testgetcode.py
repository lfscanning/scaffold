import unittest
import os
import tempfile
import shutil
from getcode import doGetRepoCodeForSubproject
from config import loadConfig
from datatypes import Status, ProjectRepoType

UPLOAD_FILE_FRAGMENT = "sp1-2023-07"
UPLOAD_FILE_NAME = UPLOAD_FILE_FRAGMENT + "-09.zip"
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_CODE = os.path.join(os.path.dirname(__file__), "testresources", UPLOAD_FILE_NAME)
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
TEST_NEXT_MONTH = "2023-08"
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, TEST_MONTH)

'''
Tests GetCode methods - such as fetching from git
'''
class TestGetCode(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_github(self):
        # Regression test for fetching an empty Github repo - issue #49
        repoName = 'TEST-Empty'
        githubOrg = 'lfscanning'
        subProjectName = 'sp1'
        projectName = 'prj1'
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._storepath = self.temp_dir.name
        prj = cfg._projects[projectName]
        prj._name = projectName
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = [repoName]
        sp._repotype = ProjectRepoType.GITHUB
        sp._github_org = githubOrg
        sp._github_ziporg = githubOrg
        sp._github_branch = ""
        
        doGetRepoCodeForSubproject(cfg, prj, sp)
        codePath = os.path.join(cfg._storepath, cfg._month, "code", prj._name, sp._name, githubOrg, repoName)
        dirContents = os.listdir(codePath)
        self.assertEqual(len(dirContents), 1)
        self.assertEqual(dirContents[0], '.git')      

    def test_shallow_clone(self):
        # Test that only depth = 1 is cloned
        repoName = 'TEST-Branches'
        githubOrg = 'lfscanning'
        subProjectName = 'sp1'
        projectName = 'prj1'
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._storepath = self.temp_dir.name
        prj = cfg._projects[projectName]
        prj._name = projectName
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = [repoName]
        sp._repotype = ProjectRepoType.GITHUB
        sp._github_org = githubOrg
        sp._github_ziporg = githubOrg
        sp._github_branch = ""
        
        doGetRepoCodeForSubproject(cfg, prj, sp)
        codePath = os.path.join(cfg._storepath, cfg._month, "code", prj._name, sp._name, githubOrg, repoName)
        shallowPath = os.path.join(codePath, '.git', 'shallow')
        self.assertTrue(os.path.isfile(shallowPath))
        mainPath = os.path.join(codePath, 'main.txt')
        self.assertTrue(os.path.isfile(mainPath))
        with open(shallowPath, 'r') as shallowFile:
            commit = shallowFile.read()
            # Note the following must the the latest commit from https://github.com/lfscanning/TEST-Branches/commits/main
            self.assertEqual(commit, 'd0d03e3c7b58456beb1c2584577d1db8fd19ce74\n')

    def test_get_branch(self):
        # Test that only depth = 1 is cloned
        repoName = 'TEST-Branches'
        branchName = 'test-branch'
        githubOrg = 'lfscanning'
        subProjectName = 'sp1'
        projectName = 'prj1'
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._storepath = self.temp_dir.name
        prj = cfg._projects[projectName]
        prj._name = projectName
        sp = prj._subprojects[subProjectName]
        sp._name = subProjectName
        sp._repos = [repoName]
        sp._repotype = ProjectRepoType.GITHUB
        sp._github_org = githubOrg
        sp._github_ziporg = githubOrg
        sp._github_branch = branchName
        
        doGetRepoCodeForSubproject(cfg, prj, sp)
        codePath = os.path.join(cfg._storepath, cfg._month, "code", prj._name, sp._name, githubOrg, repoName)
        shallowPath = os.path.join(codePath, '.git', 'shallow')
        self.assertTrue(os.path.isfile(shallowPath))
        branchPath = os.path.join(codePath, 'branch.txt')
        self.assertTrue(os.path.isfile(branchPath))
        with open(shallowPath, 'r') as shallowFile:
            commit = shallowFile.read()
            # Note the following must the the latest commit from https://github.com/lfscanning/TEST-Branches/commits/test-branch
            self.assertEqual(commit, '1b4dee764404a9fd8df2005ba585386b143649b2\n')        
if __name__ == '__main__':
    unittest.main()
        