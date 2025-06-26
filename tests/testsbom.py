import pdb
import unittest
import os
import tempfile
import shutil
import time
import git
import zipfile

from spdx_tools.spdx import document_utils, spdx_element_utils
from spdx_tools.spdx.model import RelationshipType, Package, File
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document

from scaffold.manualsbom import runManualSbomAgent
from scaffold.sbomagent import installNpm
from scaffold.config import loadConfig
from scaffold.datatypes import Status, ProjectRepoType
from spdx_tools.spdx.parser.parse_anything import parse_file
from scaffold.spdx.spdxutil import mergeSpdxDocs

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
TEST_SUBPROJECT_NAME2 = "sp2"
GITHUB_ORG = 'lfscanning'
TEST_SBOM_FILE = os.path.join(os.path.dirname(__file__), "testresources", "testsbom.json")
TEST_FOSSOLOGY_FILE = os.path.join(os.path.dirname(__file__), "testresources", "testfossology.spdx")

def is_npm_available():
    return shutil.which("npm") is not None

@unittest.skipIf(not is_npm_available(), "npm is not available in PATH")
class TestSbom(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)
        self.repo_dir = os.path.join(self.scaffold_home_dir, "spdxrepos")
        os.mkdir(self.repo_dir)
        # setup the git repo
        self.repoName = f"spdx-{TEST_PROJECT_NAME}"
        self.project_repo_dir = os.path.join(self.repo_dir, self.repoName)
        self.git_url = f"https://github.com/{GITHUB_ORG}/{self.repoName}.git"
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
        sp._code_pulled = "2024-08-21"
        sp._code_anyfiles = True
        sp._code_repos = {self.repoName: "153a803c46181319fd782ef8426ff58a2e885d82"}
        
        result = runManualSbomAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        uploadedfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{prj._name}-{sp._name}-spdx.json")
        self.assertTrue(os.path.isfile(uploadedfile))
        reportfile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{prj._name}-{sp._name}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile))
        # TODO: Check if the file is committed and pushed to the repo
        
    def test_sbom_copyright(self):
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
        sp._copyright = "Copyright (c) 2025 The Linux Foundation"

        result = runManualSbomAgent(cfg, TEST_PROJECT_NAME, TEST_SUBPROJECT_NAME)
        self.assertTrue(result)
        uploadedfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{prj._name}-{sp._name}-spdx.json")
        self.assertTrue(os.path.isfile(uploadedfile))

        # Check for copyright in SPDX file
        sbom = parse_file(uploadedfile)
        describes = None
        for relationship in sbom.relationships:
            if relationship.relationship_type == RelationshipType.DESCRIBES and relationship.spdx_element_id == 'SPDXRef-DOCUMENT':
                describes = document_utils.get_element_from_spdx_id(sbom, relationship.related_spdx_element_id)
        self.assertIsNotNone(describes)
        self.assertEqual(describes.copyright_text, "Copyright (c) 2025 The Linux Foundation")

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
        uploadedfile = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME, TEST_MONTH, f"{prj._name}-{sp._name}-spdx.json")
        self.assertTrue(os.path.isfile(uploadedfile))
        reportfile = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{prj._name}-{sp._name}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile))
        uploadedfile2 = os.path.join(self.project_repo_dir, TEST_SUBPROJECT_NAME2, TEST_MONTH, f"{prj._name}-{sp2._name}-spdx.json")
        self.assertTrue(os.path.isfile(uploadedfile))
        reportfile2 = os.path.join(self.scaffold_home_dir, TEST_MONTH, "report", TEST_PROJECT_NAME, f"{prj._name}-{sp2._name}-dependencies.xlsx")
        self.assertTrue(os.path.isfile(reportfile))

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
        cfg._month = "2024-09"
        prj = cfg._projects[TEST_PROJECT_NAME]
        prj._name = "lfenergy"
        sp = prj._subprojects[TEST_SUBPROJECT_NAME]
        sp._name = "flexmeasures"
        sbom = parse_file(TEST_SBOM_FILE)
        fossology = parse_file(TEST_FOSSOLOGY_FILE)
        result = mergeSpdxDocs(fossology, sbom, cfg, prj, sp)
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

if __name__ == '__main__':
    unittest.main()
        