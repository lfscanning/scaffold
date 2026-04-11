import os
import shutil
import tempfile
import unittest
import json
import urllib.request
from pathlib import Path

from findings import filesToFileDisplayInfoSp, makeFindingsForSubproject, makeFindingsForProject
from config import loadConfig
from datatypes import ProjectRepoType

SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
TEST_NEXT_MONTH = "2023-08"
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, TEST_MONTH)
GITHUB_ORG = 'lfscanning'
SCAFFOLD_REPO = 'scaffold'
TEST_DEP_REPO = 'spdx-TEST-DEPENDENCIES'
ORAN_REPO = 'spdx-o-ran'
SCAFFOLD_BRANCH = 'findupload'
TEST_SCAFFOLD_COMMIT = 'd50d60dc7c73c4582feb006424ca86ca03225692'
TEST_DEP_COMMIT = 'b2597ca6cae371143950bb207e946330d022b56f'
SCAFFOLD_FILENAME = 'README.md'
TEST_DEP_FILENAME = 'sp1/2023-07/TEST-DEPENDENCIES-sp1-spdx-v2.json'
ORAN_FILENAME = 'aal/2021-05/aal-2021-05-25.spdx'
SUBPROJECT_NAME = 'sp1'
SUBPROJECT2_NAME = 'sp2'
PROJECT_NAME = 'prj1'
ZIPFILE_NAME = f'{SUBPROJECT_NAME}-{TEST_MONTH}.zip'

class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_to_display_info_no_branch(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[PROJECT_NAME]
        prj._name = PROJECT_NAME
        prj._repotype = ProjectRepoType.GITHUB
        sp = prj._subprojects[SUBPROJECT_NAME]
        sp._name = SUBPROJECT_NAME
        sp._github_org = GITHUB_ORG
        sp._code_repos = {
            SCAFFOLD_REPO: '',
            TEST_DEP_REPO: TEST_DEP_COMMIT
        }
        files = [
            f'{ZIPFILE_NAME}/{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}',  # No commit
            f'{ZIPFILE_NAME}/{TEST_DEP_REPO}/{TEST_DEP_FILENAME}',  # associated commit
            f'{ZIPFILE_NAME}/{ORAN_REPO}/{ORAN_FILENAME}'   # not in repos list
        ]
        results = filesToFileDisplayInfoSp(files, sp)
        expected_scaffold_filename = f'{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}'
        expected_scaffold_url = f'https://github.com/{GITHUB_ORG}/{SCAFFOLD_REPO}/blob/HEAD/{SCAFFOLD_FILENAME}'
        expected_scaffold_haslink = True
        found_scaffold = False
        expected_test_dep_filename = f'{TEST_DEP_REPO}/{TEST_DEP_FILENAME}'
        expected_test_dep_url = f'https://github.com/{GITHUB_ORG}/{TEST_DEP_REPO}/blob/{TEST_DEP_COMMIT}/{TEST_DEP_FILENAME}'
        expected_test_dep_haslink = True
        found_test_dep = False
        expected_oran_filename = f'{ORAN_REPO}/{ORAN_FILENAME}'
        expected_oran_url = f'https://github.com/{GITHUB_ORG}/{ORAN_REPO}/blob/HEAD/{ORAN_FILENAME}'
        expected_oran_haslink = True
        found_oran = False

        for display_info in results:
            if display_info["filename"] == expected_scaffold_filename:
                self.assertEqual(expected_scaffold_url, display_info["link"])
                self.assertEqual(expected_scaffold_haslink, display_info["haslink"])
                self.assertEqual(200, urllib.request.urlopen(display_info["link"]).getcode())
                found_scaffold = True
            elif display_info["filename"] == expected_test_dep_filename:
                self.assertEqual(expected_test_dep_url, display_info["link"])
                self.assertEqual(expected_test_dep_haslink, display_info["haslink"])
                self.assertEqual(200, urllib.request.urlopen(display_info["link"]).getcode())
                found_test_dep = True
            elif display_info["filename"] == expected_oran_filename:
                self.assertEqual(expected_oran_url, display_info["link"])
                self.assertEqual(expected_oran_haslink, display_info["haslink"])
                self.assertEqual(200, urllib.request.urlopen(display_info["link"]).getcode())
                found_oran = True
            else:
                self.fail(f'Uexpected result filename {display_info["filename"]}')
        self.assertTrue(found_scaffold)
        self.assertTrue(found_oran)
        self.assertTrue(found_test_dep)

    def test_file_to_display_info_branch(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[PROJECT_NAME]
        prj._name = PROJECT_NAME
        prj._repotype = ProjectRepoType.GITHUB
        sp = prj._subprojects[SUBPROJECT_NAME]
        sp._name = SUBPROJECT_NAME
        sp._github_org = GITHUB_ORG
        sp._github_branch = SCAFFOLD_BRANCH
        sp._code_repos = {
            SCAFFOLD_REPO: '',
            TEST_DEP_REPO: TEST_DEP_COMMIT
        }
        files = [
            f'{ZIPFILE_NAME}/{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}',  # No commit
            f'{ZIPFILE_NAME}/{TEST_DEP_REPO}/{TEST_DEP_FILENAME}',  # associated commit
            f'{ZIPFILE_NAME}/{ORAN_REPO}/{ORAN_FILENAME}'   # not in repos list
        ]
        results = filesToFileDisplayInfoSp(files, sp)
        expected_scaffold_filename = f'{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}'
        expected_scaffold_url = f'https://github.com/{GITHUB_ORG}/{SCAFFOLD_REPO}/blob/{SCAFFOLD_BRANCH}/{SCAFFOLD_FILENAME}'
        expected_scaffold_haslink = True
        found_scaffold = False
        expected_test_dep_filename = f'{TEST_DEP_REPO}/{TEST_DEP_FILENAME}'
        expected_test_dep_url = f'https://github.com/{GITHUB_ORG}/{TEST_DEP_REPO}/blob/{TEST_DEP_COMMIT}/{TEST_DEP_FILENAME}'
        expected_test_dep_haslink = True
        found_test_dep = False
        expected_oran_filename = f'{ORAN_REPO}/{ORAN_FILENAME}'
        expected_oran_url = f'https://github.com/{GITHUB_ORG}/{ORAN_REPO}/blob/{SCAFFOLD_BRANCH}/{ORAN_FILENAME}'
        expected_oran_haslink = True
        found_oran = False

        for display_info in results:
            if display_info["filename"] == expected_scaffold_filename:
                self.assertEqual(expected_scaffold_url, display_info["link"])
                self.assertEqual(expected_scaffold_haslink, display_info["haslink"])
                self.assertEqual(200, urllib.request.urlopen(display_info["link"]).getcode())
                found_scaffold = True
            elif display_info["filename"] == expected_test_dep_filename:
                self.assertEqual(expected_test_dep_url, display_info["link"])
                self.assertEqual(expected_test_dep_haslink, display_info["haslink"])
                self.assertEqual(200, urllib.request.urlopen(display_info["link"]).getcode())
                found_test_dep = True
            elif display_info["filename"] == expected_oran_filename:
                self.assertEqual(expected_oran_url, display_info["link"])
                self.assertEqual(expected_oran_haslink, display_info["haslink"])
                # - the branch doesn't exist on oran self.assertEqual(200, urllib.request.urlopen(display_info["link"]).getcode())
                found_oran = True
            else:
                self.fail(f'Uexpected result filename {display_info["filename"]}')
        self.assertTrue(found_scaffold)
        self.assertTrue(found_oran)
        self.assertTrue(found_test_dep)

    def test_file_to_display_info_no_github(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[PROJECT_NAME]
        prj._name = PROJECT_NAME
        prj._repotype = ProjectRepoType.GERRIT
        sp = prj._subprojects[SUBPROJECT_NAME]
        sp._name = SUBPROJECT_NAME
        sp._github_org = ''
        sp._code_repos = {
            SCAFFOLD_REPO: '',
            TEST_DEP_REPO: TEST_DEP_COMMIT
        }
        files = [
            f'{ZIPFILE_NAME}/{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}',  # No commit
            f'{ZIPFILE_NAME}/{TEST_DEP_REPO}/{TEST_DEP_FILENAME}',  # associated commit
            f'{ZIPFILE_NAME}/{ORAN_REPO}/{ORAN_FILENAME}'   # not in repos list
        ]
        results = filesToFileDisplayInfoSp(files, sp)
        expected_scaffold_filename = f'{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}'
        expected_scaffold_url = ''
        expected_scaffold_haslink = False
        found_scaffold = False
        expected_test_dep_filename = f'{TEST_DEP_REPO}/{TEST_DEP_FILENAME}'
        expected_test_dep_url = ''
        expected_test_dep_haslink = False
        found_test_dep = False
        expected_oran_filename = f'{ORAN_REPO}/{ORAN_FILENAME}'
        expected_oran_url = ''
        expected_oran_haslink = False
        found_oran = False

        for display_info in results:
            if display_info["filename"] == expected_scaffold_filename:
                self.assertEqual(expected_scaffold_url, display_info["link"])
                self.assertEqual(expected_scaffold_haslink, display_info["haslink"])
                found_scaffold = True
            elif display_info["filename"] == expected_test_dep_filename:
                self.assertEqual(expected_test_dep_url, display_info["link"])
                self.assertEqual(expected_test_dep_haslink, display_info["haslink"])
                found_test_dep = True
            elif display_info["filename"] == expected_oran_filename:
                self.assertEqual(expected_oran_url, display_info["link"])
                self.assertEqual(expected_oran_haslink, display_info["haslink"])
                found_oran = True
            else:
                self.fail(f'Uexpected result filename {display_info["filename"]}')
        self.assertTrue(found_scaffold)
        self.assertTrue(found_oran)
        self.assertTrue(found_test_dep)

    def test_subproject(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[PROJECT_NAME]
        prj._name = PROJECT_NAME
        prj._repotype = ProjectRepoType.GITHUB
        sp = prj._subprojects[SUBPROJECT_NAME]
        sp._name = SUBPROJECT_NAME
        sp._github_org = GITHUB_ORG
        sp._code_pulled = '2026-04-10'
        sp._code_repos = {
            SCAFFOLD_REPO: TEST_SCAFFOLD_COMMIT,
            TEST_DEP_REPO: TEST_DEP_COMMIT
        }
        expected_scaffold_link = f'https://github.com/{GITHUB_ORG}/{SCAFFOLD_REPO}/blob/{TEST_SCAFFOLD_COMMIT}/{SCAFFOLD_FILENAME}'
        expected_test_dep_link = f'https://github.com/{GITHUB_ORG}/{TEST_DEP_REPO}/blob/{TEST_DEP_COMMIT}/{TEST_DEP_FILENAME}'

        with tempfile.TemporaryDirectory() as localtemp:
            cfg._storepath = localtemp
            cfg._month = TEST_MONTH
            reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
            Path(reportFolder).mkdir(parents=True, exist_ok=True)
            slmJsonPath = os.path.join(reportFolder, f"{sp._name}-{sp._code_pulled}.json")
            slmData = [{
                "name": "Project Licenses",
                "numFiles": 1,
                "licenses": [
                    {
                        "name": "GPL-2.0",
                        "numFiles": 2,
                        "files": [
                            {
                                "path": f'{ZIPFILE_NAME}/{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}'
                            },
                            {
                                "path": f'{ZIPFILE_NAME}/{TEST_DEP_REPO}/{TEST_DEP_FILENAME}'
                            }
                        ]
                    }
                ]
            }]
            with open(slmJsonPath, "w") as slmJsonFile:
                json.dump(slmData, slmJsonFile)
            htmlPath = os.path.join(reportFolder, f"{sp._name}-{sp._code_pulled}.html")
            makeFindingsForSubproject(cfg, prj, sp, False)
            html = Path(htmlPath).read_text()
            self.assertTrue(expected_scaffold_link in html)
            self.assertTrue(expected_test_dep_link in html)

    def test_project(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects[PROJECT_NAME]
        prj._name = PROJECT_NAME
        prj._repotype = ProjectRepoType.GITHUB
        sp1 = prj._subprojects[SUBPROJECT_NAME]
        sp1._name = SUBPROJECT_NAME
        sp1._github_org = GITHUB_ORG
        sp1._code_pulled = '2026-04-10'
        sp1._code_repos = {
            SCAFFOLD_REPO: TEST_SCAFFOLD_COMMIT
        }
        sp2 = prj._subprojects[SUBPROJECT2_NAME]
        sp2._name = SUBPROJECT2_NAME
        sp2._github_org = GITHUB_ORG
        sp2._code_pulled = '2026-04-10'
        sp2._code_repos = {
            TEST_DEP_REPO: TEST_DEP_COMMIT
        }

        expected_scaffold_link = f'https://github.com/{GITHUB_ORG}/{SCAFFOLD_REPO}/blob/{TEST_SCAFFOLD_COMMIT}/{SCAFFOLD_FILENAME}'
        expected_test_dep_link = f'https://github.com/{GITHUB_ORG}/{TEST_DEP_REPO}/blob/{TEST_DEP_COMMIT}/{TEST_DEP_FILENAME}'

        with tempfile.TemporaryDirectory() as localtemp:
            cfg._storepath = localtemp
            cfg._month = TEST_MONTH
            reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
            Path(reportFolder).mkdir(parents=True, exist_ok=True)
            slmJsonPath = os.path.join(reportFolder, f"{prj._name}-{TEST_MONTH}.json")
            slmData = [{
                "name": "Project Licenses",
                "numFiles": 1,
                "licenses": [
                    {
                        "name": "GPL-2.0",
                        "numFiles": 2,
                        "files": [
                            {
                                "path": f'{ZIPFILE_NAME}/{SCAFFOLD_REPO}/{SCAFFOLD_FILENAME}'
                            },
                            {
                                "path": f'{ZIPFILE_NAME}/{TEST_DEP_REPO}/{TEST_DEP_FILENAME}'
                            }
                        ]
                    }
                ]
            }]
            with open(slmJsonPath, "w") as slmJsonFile:
                json.dump(slmData, slmJsonFile)
            htmlPath = os.path.join(reportFolder, f"{prj._name}-{TEST_MONTH}.html")
            makeFindingsForProject(cfg, prj, False)
            html = Path(htmlPath).read_text()
            self.assertTrue(expected_scaffold_link in html)
            self.assertTrue(expected_test_dep_link in html)

if __name__ == '__main__':
    unittest.main()
