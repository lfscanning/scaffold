import pdb
import unittest
import os
import tempfile
import shutil
import time
import contextlib
import io
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

import git
import zipfile

from spdx_tools.spdx import document_utils, spdx_element_utils
from spdx_tools.spdx.model import RelationshipType, Package, File
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document

from manualsbom import runManualSbomAgent
import gradle_lockfiles
from sbomagent import installNpm, mergeSourceAndSbom, generateGradleLockFiles
from config import loadConfig
from datatypes import Status, ProjectRepoType, Project, Subproject
from spdx_tools.spdx.parser.parse_anything import parse_file
from uploadspdx import UPLOAD_SPDX_SUFFIX, UPLOAD_SPDX_V3_SUFFIX, MERGED_SBOM_SUFFIX, MERGED_SBOM_V3_SUFFIX

from spdx.spdxutil import mergeSpdxDocs

ANALYSIS_FILE_FRAGMENT = "sp1-2023-07"
ANALYSIS_FILE_NAME = ANALYSIS_FILE_FRAGMENT + "-09.zip"
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_CODE = os.path.join(os.path.dirname(__file__), "testresources", ANALYSIS_FILE_NAME)
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
SIMPLE_NPM_ZIP = os.path.join(os.path.dirname(__file__), "testresources", "simplenpm.zip")
SIMPLE_GRADLE_ZIP = os.path.join(os.path.dirname(__file__), "testresources", "simplegradle.zip")
GRADLE_EXEC_PATH = os.environ.get('GRADLE_EXEC_PATH', 'gradle')  # default
requires_gradle = unittest.skipUnless(shutil.which(GRADLE_EXEC_PATH), f"Gradle not found at '{GRADLE_EXEC_PATH}' - set GRADLE_EXEC_PATH to run this test")
TEST_MONTH = "2023-07"
TEST_NEXT_MONTH = "2023-08"
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, TEST_MONTH)
TEST_PROJECT_NAME = "TEST-DEPENDENCIES"
TEST_SUBPROJECT_NAME = "sp1"
TEST_SUBPROJECT_NAME2 = "sp2"
GITHUB_ORG = 'lfscanning'
TEST_SBOM_FILE = os.path.join(os.path.dirname(__file__), "testresources", "testsbom.json")
TEST_FOSSOLOGY_FILE = os.path.join(os.path.dirname(__file__), "testresources", "testfossology.spdx")
TEST_FOSSOLOGY_FILE_ZIP = os.path.join(os.path.dirname(__file__), "testresources", "testfossology.spdx.zip")
FOSSOLOGY_TEST_MONTH = "2024-09"
FOSSOLOGY_TEST_PROJECT = "lfenergy"
FOSSOLOGY_TEST_SUBPROJECT = "flexmeasures"
FOSSOLOGY_TEST_CODE_PULLED = "2024-08-21"
LARGE_SBOM_ZIP_FILE  = os.path.join(os.path.dirname(__file__), "testresources", "large-sbom.zip")
LARGE_FOSSOLOGY_SBOM_FILENAME = "large-fossology-sbom.json"
LARGE_DEPENDENCY_SBOM_FILENAME = "large-dependency-sbom.json"
'''
Tests sbom manual agent commands
'''
class TestSbom(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)
        self.repo_dir = os.path.join(self.scaffold_home_dir, "spdxrepos")
        os.mkdir(self.repo_dir)
        self.fossology_test_dir_path = os.path.join(self.repo_dir, f"spdx-{FOSSOLOGY_TEST_PROJECT}", FOSSOLOGY_TEST_SUBPROJECT, FOSSOLOGY_TEST_MONTH)
        os.makedirs(self.fossology_test_dir_path)
        # setup the git repo
        self.repoName = f"spdx-{TEST_PROJECT_NAME}"
        self.project_repo_dir = os.path.join(self.repo_dir, self.repoName)
        self.git_url = f"git@github.com:{GITHUB_ORG}/{self.repoName}.git"
        git.Git(self.repo_dir).clone(self.git_url, depth=1)
        self._cleanGitClone(self.project_repo_dir)
        self.trivy_env_set = 'TRIVY_EXEC_PATH' in os.environ
        if not self.trivy_env_set:
            os.environ['TRIVY_EXEC_PATH'] = 'trivy' # default
        self.npm_env_set = 'NPM_EXEC_PATH' in os.environ
        if not self.npm_env_set:
            os.environ['NPM_EXEC_PATH'] = 'npm' # default
        self.npm_path = os.path.join(self.temp_dir.name, 'simplenpm')
        self.parlay_env_set = 'PARLAY_EXEC_PATH' in os.environ
        if not self.parlay_env_set:
            os.environ['PARLAY_EXEC_PATH'] = 'parlay' # default
        self.cdsbom_env_set = 'CDSBOM_EXEC_PATH' in os.environ
        if not self.cdsbom_env_set:
            os.environ['CDSBOM_EXEC_PATH'] = 'cdsbom' # default
        self.tools_java_env_set = 'TOOLS_JAVA_PATH' in os.environ
        if not self.tools_java_env_set:
            os.environ['TOOLS_JAVA_PATH'] = '~/tools-java.jar' # default
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

        if not self.trivy_env_set:
            del os.environ['TRIVY_EXEC_PATH']
        if not self.npm_env_set:
            del os.environ['NPM_EXEC_PATH']
        if not self.parlay_env_set:
            del os.environ['PARLAY_EXEC_PATH']
        if not self.cdsbom_env_set:
            del os.environ['CDSBOM_EXEC_PATH']
        if not self.tools_java_env_set:
            del os.environ['TOOLS_JAVA_PATH']
            

    def test_sbom(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._zippath = self.temp_dir.name
        cfg._storepath = self.scaffold_home_dir
        cfg._spdx_github_org = GITHUB_ORG
        cfg._web_server = "lfscanning.org"
        cfg._web_server_use_scp = False
        cfg._web_reports_path = os.path.join(self.temp_dir.name, 'outputreports')
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
        sp._code_pulled = FOSSOLOGY_TEST_CODE_PULLED
        sp._code_anyfiles = True
        sp._code_repos = {self.repoName: "153a803c46181319fd782ef8426ff58a2e885d82"}
        
        result = runManualSbomAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        uploadedfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_SUFFIX}.json")
        self.assertTrue(os.path.isfile(uploadedfile))
        reportfile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile))
        reportUploadFile = os.path.join(self.temp_dir.name, cfg._web_reports_path, TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies-{sp._web_uuid}.xlsx")
        self.assertTrue(os.path.isfile(reportUploadFile))
        spdxv3file = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_V3_SUFFIX}.json")
        self.assertTrue(os.path.isfile(spdxv3file))
        dependenciesHtmlFile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies.html")
        self.assertTrue(os.path.isfile(dependenciesHtmlFile))
        dependenciesHtmlUploadFile = os.path.join(self.temp_dir.name, cfg._web_reports_path, TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies-{sp._web_uuid}.html")
        self.assertTrue(os.path.isfile(dependenciesHtmlUploadFile))
        # TODO: Check if the file is committed and pushed to the repo
        
    def test_npm_install(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._zippath = self.temp_dir.name
        prj = cfg._projects[TEST_PROJECT_NAME]
        prj._name = TEST_PROJECT_NAME
        sp = prj._subprojects[TEST_SUBPROJECT_NAME]
        sp._name = TEST_SUBPROJECT_NAME
        self.assertFalse(os.path.isdir(self.node_modules_path))
        installNpm(self.npm_path, cfg, prj, sp)
        self.assertTrue(os.path.isdir(self.node_modules_path))
        self.assertTrue(os.path.isfile(self.uuid_package_json_path))
        
    def test_project(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._zippath = self.temp_dir.name
        cfg._storepath = self.scaffold_home_dir
        cfg._spdx_github_org = GITHUB_ORG
        cfg._web_server = "lfscanning.org"
        cfg._web_server_use_scp = False
        cfg._web_reports_path = os.path.join(self.temp_dir.name, 'outputreports')
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

        sp2 = prj._subprojects[TEST_SUBPROJECT_NAME2]
        sp2._name = TEST_SUBPROJECT_NAME2
        sp2._repos = [self.repoName]
        sp2._repotype = ProjectRepoType.GITHUB
        sp2._github_org = GITHUB_ORG
        sp2._github_ziporg = GITHUB_ORG
        sp2._github_branch = ""
        sp2._status = Status.ZIPPEDCODE
        sp2._code_path = TEST_SCAFFOLD_CODE
        sp2._code_pulled = "2024-08-21"
        sp2._code_anyfiles = True
        sp2._code_repos = {self.repoName: "153a803c46181319fd782ef8426ff58a2e885d82"}

        result = runManualSbomAgent(cfg, TEST_PROJECT_NAME, "")
        self.assertTrue(result)
        uploadedfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_SUFFIX}.json")
        self.assertTrue(os.path.isfile(uploadedfile))
        reportfile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile))
        reportUploadFile = os.path.join(self.temp_dir.name, cfg._web_reports_path, TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies-{sp._web_uuid}.xlsx")
        self.assertTrue(os.path.isfile(reportUploadFile))
        uploadedfile2 = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME2, TEST_MONTH, f"{sp2._name}-{sp._code_pulled}-{UPLOAD_SPDX_SUFFIX}.json")
        self.assertTrue(os.path.isfile(uploadedfile2))
        reportfile2 = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp2._name}-{sp._code_pulled}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile2))
        reportUploadFile2 = os.path.join(self.temp_dir.name, cfg._web_reports_path, TEST_PROJECT_NAME, f"{sp2._name}-{sp2._code_pulled}-dependencies-{sp2._web_uuid}.xlsx")
        self.assertTrue(os.path.isfile(reportUploadFile2))
        spdxv3file = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_V3_SUFFIX}.json")
        self.assertTrue(os.path.isfile(spdxv3file))
        dependenciesHtmlFile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies.html")
        self.assertTrue(os.path.isfile(dependenciesHtmlFile))
        dependenciesHtmlUploadFile = os.path.join(self.temp_dir.name, cfg._web_reports_path, TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies-{sp._web_uuid}.html")
        self.assertTrue(os.path.isfile(dependenciesHtmlUploadFile))

    def test_sbom_config(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._zippath = self.temp_dir.name
        cfg._storepath = self.scaffold_home_dir
        cfg._spdx_github_org = GITHUB_ORG
        cfg._web_server = "lfscanning.org"
        cfg._web_server_use_scp = False
        cfg._web_reports_path = os.path.join(self.temp_dir.name, 'outputreports')
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
        result = runManualSbomAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        saved_trivy = sp._trivy_exec_path
        sp._trivy_exec_path = 'somegarbage'
        try:
            result = runManualSbomAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
            self.assertFalse(result) # More likely to case an exception, but a false return is also OK
        except:
            pass  # expected
        finally:
            os.environ['TRIVY_EXEC_PATH'] = saved_trivy
            
    def test_merged_sbom(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._month = FOSSOLOGY_TEST_MONTH
        prj = cfg._projects[TEST_PROJECT_NAME]
        prj._name = FOSSOLOGY_TEST_PROJECT
        sp = prj._subprojects[TEST_SUBPROJECT_NAME]
        sp._name = FOSSOLOGY_TEST_SUBPROJECT
        cfg._storepath = self.scaffold_home_dir
        sp._code_pulled = FOSSOLOGY_TEST_CODE_PULLED
        fossology_dir_path = os.path.join(self.scaffold_home_dir, cfg._month, "spdx", prj._name)
        os.makedirs(fossology_dir_path)
        fossology_file_path = os.path.join(fossology_dir_path, f"{FOSSOLOGY_TEST_SUBPROJECT}-{FOSSOLOGY_TEST_CODE_PULLED}.spdx")
        shutil.copyfile(TEST_FOSSOLOGY_FILE, fossology_file_path)
        sbom = parse_file(TEST_SBOM_FILE)
        try:
            with tempfile.TemporaryDirectory() as localtemp:
                result = mergeSourceAndSbom(cfg, prj, sp, localtemp, sbom)
        finally:
            os.remove(fossology_file_path)
        self.assertIsNotNone(result)
        describes = None
        # Check root describes
        for relationship in result.relationships:
            if relationship.relationship_type == RelationshipType.DESCRIBES and relationship.spdx_element_id == 'SPDXRef-DOCUMENT':
                describes = document_utils.get_element_from_spdx_id(result, relationship.related_spdx_element_id)
        self.assertIsNotNone(describes)
        self.assertEqual(describes.name, "lfenergy.flexmeasures", "Wrong document describes")
        # Check creation Info
        self.assertTrue(result.creation_info.document_namespace.startswith("https://github.com/lfscanning/spdx-lfenergy/flexmeasures/2024-09/"))
        foundToolScaffold = False
        foundToolFossology = False
        foundToolTrivy = False
        foundLfCreator = False
        for creator in result.creation_info.creators:
            if creator.name.startswith("Scaffold"):
                foundToolScaffold = True
            if creator.name.startswith("trivy"):
                foundToolTrivy = True
            if creator.name.startswith("Linux Foundation"):
                foundLfCreator = True
            if creator.name.startswith("fossology"):
                foundToolFossology = True
        self.assertTrue(foundToolScaffold)
        self.assertTrue(foundToolFossology)
        self.assertTrue(foundToolTrivy)
        self.assertTrue(foundLfCreator)
        # Check source files merged
        # Check dependencies merged
        for relationship in result.relationships:
            if relationship.relationship_type == RelationshipType.CONTAINS and relationship.spdx_element_id == describes.spdx_id:
                foundDepRelationship = False
                foundSourceRelationship = False
                for repoRelationship in result.relationships:
                    if repoRelationship.relationship_type == RelationshipType.CONTAINS and repoRelationship.spdx_element_id == relationship.related_spdx_element_id:
                        if spdx_element_utils.get_element_type_from_spdx_id(repoRelationship.related_spdx_element_id, result) == Package:
                            foundDepRelationship = True
                        if spdx_element_utils.get_element_type_from_spdx_id(repoRelationship.related_spdx_element_id, result) == File:
                            foundSourceRelationship = True
                if relationship.related_spdx_element_id == "SPDXRef-lfenergy-flexmeasures-flexmeasures":
                    self.assertTrue(foundDepRelationship)
                    # Note that other repos don't contain dependencies
                self.assertTrue(foundSourceRelationship)
        validation = validate_full_spdx_document(result)
        self.assertTrue(not validation)

    def test_merge_large_sbom(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._month = "2026-02"
        prj = Project()
        sp = Subproject()
        prj._name = "cncf-3"
        sp._name = "kubeflow"
        with tempfile.TemporaryDirectory() as localtemp:
            with zipfile.ZipFile(LARGE_SBOM_ZIP_FILE, 'r') as zip:
                zip.extractall(localtemp)
            print(f"Parsing FOSSOlogy SBOM {datetime.now()}")
            large_fossology_sbom = parse_file(os.path.join(localtemp, LARGE_FOSSOLOGY_SBOM_FILENAME))
            print(f"Parsing dependency SBOM {datetime.now()}")
            large_dependency_sbom = parse_file(os.path.join(localtemp, LARGE_DEPENDENCY_SBOM_FILENAME))
            print(f"Merging SBOM {datetime.now()}")
            result = mergeSpdxDocs(large_fossology_sbom, large_dependency_sbom, cfg, prj, sp)
            print(f"SBOM Merged {datetime.now()}")
            # Check root describes
            for relationship in result.relationships:
                if relationship.relationship_type == RelationshipType.DESCRIBES and relationship.spdx_element_id == 'SPDXRef-DOCUMENT':
                    describes = document_utils.get_element_from_spdx_id(result, relationship.related_spdx_element_id)
            self.assertIsNotNone(describes)
            self.assertEqual(describes.name, "cncf-3.kubeflow", "Wrong document describes")

    def test_private_reports_config(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        self.assertFalse(cfg._projects["prj1"]._reports_private)
        self.assertFalse(cfg._projects["prj1"]._subprojects["sp1"]._reports_private)
        self.assertTrue(cfg._projects["prj-private-sbom"]._reports_private)
        self.assertFalse(cfg._projects["prj-private-sbom"]._subprojects["sp-public-sbom"]._reports_private)
        self.assertTrue(cfg._projects["prj-private-sbom"]._subprojects["sp-default-sbom"]._reports_private)

    def test_private_sbom(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._zippath = self.temp_dir.name
        cfg._storepath = self.scaffold_home_dir
        cfg._spdx_github_org = GITHUB_ORG
        cfg._web_server = "lfscanning.org"
        cfg._web_server_use_scp = False
        cfg._web_reports_path = os.path.join(self.temp_dir.name, 'outputreports')
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
        sp._code_pulled = FOSSOLOGY_TEST_CODE_PULLED
        sp._code_anyfiles = True
        sp._code_repos = {self.repoName: "153a803c46181319fd782ef8426ff58a2e885d82"}
        sp._reports_private = True

        result = runManualSbomAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        uploadedfile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_SUFFIX}.json")
        self.assertTrue(os.path.isfile(uploadedfile))
        gitfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_SUFFIX}.json")
        self.assertFalse(os.path.isfile(gitfile))
        reportfile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile))
        reportUploadFile = os.path.join(self.temp_dir.name, cfg._web_reports_path, TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies-{sp._web_uuid}.xlsx")
        self.assertTrue(os.path.isfile(reportUploadFile))
        spdxv3gitFile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_V3_SUFFIX}.json")
        self.assertFalse(os.path.isfile(spdxv3gitFile))
        spdxv3file = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-{UPLOAD_SPDX_V3_SUFFIX}.json")
        self.assertTrue(os.path.isfile(spdxv3file))
        dependenciesHtmlFile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies.html")
        self.assertTrue(os.path.isfile(dependenciesHtmlFile))
        dependenciesHtmlUploadFile = os.path.join(self.temp_dir.name, cfg._web_reports_path, TEST_PROJECT_NAME, f"{sp._name}-{sp._code_pulled}-dependencies-{sp._web_uuid}.html")
        self.assertTrue(os.path.isfile(dependenciesHtmlUploadFile))
        self.assertTrue(f"-{UPLOAD_SPDX_V3_SUFFIX}" in sp._web_sbom_spdxv3)
        self.assertTrue(f"-{UPLOAD_SPDX_SUFFIX}" in sp._web_sbom_spdxv2)
        # TODO: Test merged SBOM

'''
Tests the generation of missing Gradle lock files

These have their own light setup rather than extending TestSbom, whose setUp clones (and whose tearDown pushes to)
a GitHub repo.  generateGradleLockFiles only uses cfg._zippath and cfg._gradle_exec_path, so a simple stand-in
config is enough.

testresources/simplegradle.zip is a small build with a root project plus "app" and "lib" projects.  Its one
dependency comes from a repository inside the zip, so the tests need no network access.  The build does not
configure dependency locking, and the "lib" project already contains a lock file.
'''
class TestGradleLockfiles(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        with zipfile.ZipFile(SIMPLE_GRADLE_ZIP, mode='r') as zip:
            zip.extractall(self.temp_dir.name)
        self.gradle_path = os.path.join(self.temp_dir.name, 'simplegradle')
        self.root_lockfile = os.path.join(self.gradle_path, 'gradle.lockfile')
        self.app_lockfile = os.path.join(self.gradle_path, 'app', 'gradle.lockfile')
        self.lib_lockfile = os.path.join(self.gradle_path, 'lib', 'gradle.lockfile')
        self.gradle_cache_dir = os.path.join(self.temp_dir.name, 'gradlecache')
        self.cfg = SimpleNamespace(_zippath=self.temp_dir.name, _gradle_exec_path=GRADLE_EXEC_PATH)
        self.prj = Project()
        self.prj._name = TEST_PROJECT_NAME
        self.sp = Subproject()
        self.sp._name = TEST_SUBPROJECT_NAME
        # Normally an extra init script downloads the Foojay toolchain resolver plugin from the Gradle plugin
        # portal.  The test build doesn't need a JDK download, so replace it with a no-op to stay offline.
        patcher = mock.patch.object(gradle_lockfiles, "INIT_SCRIPT_TOOLCHAINS", "// Foojay disabled for tests\n")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _read(self, path):
        with open(path, 'rb') as f:
            return f.read()

    def _snapshot(self):
        # The content of every file except lock files and Gradle's own working directories
        snapshot = {}
        for dirpath, dirs, files in os.walk(self.gradle_path):
            dirs[:] = [d for d in dirs if d not in ('.gradle', 'build')]
            for fileName in files:
                if fileName != 'gradle.lockfile':
                    path = os.path.join(dirpath, fileName)
                    snapshot[path] = self._read(path)
        return snapshot

    @requires_gradle
    def test_generate_lockfiles(self):
        lib_lockfile_before = self._read(self.lib_lockfile)
        snapshot_before = self._snapshot()
        self.assertFalse(os.path.exists(self.app_lockfile))
        generateGradleLockFiles(self.gradle_path, self.cfg, self.prj, self.sp)
        # The missing lock file is created and locks the dependency
        self.assertTrue(os.path.isfile(self.app_lockfile))
        self.assertIn('org.example:testlib:1.0.0=', self._read(self.app_lockfile).decode())
        # The lock file that was already there is left alone
        self.assertEqual(lib_lockfile_before, self._read(self.lib_lockfile))
        # The root project applies no plugins so it has nothing to lock and Gradle writes no file for it
        self.assertFalse(os.path.exists(self.root_lockfile))
        # The build itself is never modified, even though it doesn't configure locking
        self.assertEqual(snapshot_before, self._snapshot())
        # Gradle used its own cache directory under cfg._zippath
        self.assertTrue(os.path.isdir(self.gradle_cache_dir))

    @requires_gradle
    def test_generate_lockfiles_result(self):
        messages = []
        env = {'GRADLE_USER_HOME': self.gradle_cache_dir}
        # A dry run reports what is missing without running Gradle
        result = gradle_lockfiles.generate_lockfiles(self.gradle_path, dry_run=True, log=messages.append)
        self.assertEqual(3, result.projects)
        self.assertEqual(1, result.already_present)
        self.assertEqual(2, result.missing)
        self.assertEqual(0, result.created)
        self.assertFalse(os.path.exists(self.app_lockfile))
        self.assertFalse(os.path.exists(self.gradle_cache_dir))
        # The real run creates the lock file for "app".  Nothing is created for the root project (see above).
        result = gradle_lockfiles.generate_lockfiles(self.gradle_path, gradle_exe=GRADLE_EXEC_PATH, env=env, log=messages.append)
        self.assertEqual(1, result.created)
        self.assertEqual(1, result.no_lockfile)
        self.assertEqual(0, result.failed)
        self.assertTrue(os.path.isfile(self.app_lockfile))
        # Running again doesn't touch the lock file that now exists
        app_lockfile_before = self._read(self.app_lockfile)
        result = gradle_lockfiles.generate_lockfiles(self.gradle_path, gradle_exe=GRADLE_EXEC_PATH, env=env, log=messages.append)
        self.assertEqual(2, result.already_present)
        self.assertEqual(0, result.created)
        self.assertEqual(app_lockfile_before, self._read(self.app_lockfile))

    def test_gradle_failure_is_not_fatal(self):
        # Like installNpm, a failure is reported but doesn't stop the SBOM run.  The test project has no gradlew,
        # so the Gradle from the config is used - point it at one that doesn't exist.
        self.cfg._gradle_exec_path = os.path.join(self.temp_dir.name, 'no-such-gradle')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            generateGradleLockFiles(self.gradle_path, self.cfg, self.prj, self.sp)  # must not raise
        self.assertFalse(os.path.exists(self.app_lockfile))
        self.assertIn('could not start Gradle', output.getvalue())
        self.assertIn(f"{TEST_PROJECT_NAME}/{TEST_SUBPROJECT_NAME}: Gradle lock file generation incomplete", output.getvalue())

if __name__ == '__main__':
    unittest.main()
        