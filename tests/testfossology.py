import unittest
import os
import tempfile
import shutil
from scaffold import fossologySetup
from config import loadSecrets, loadConfig
from uploadcode import doUploadCodeForSubproject, doUploadCodeForProject
from datatypes import Status, ProjectRepoType
from runagents import getUploadFolder, doRunAgentsForSubproject, getUpload, uploadExists
from getspdx import doGetSPDXForSubproject
from newmonth import copyToNextMonth
from getcode import doGetRepoCodeForSubproject

UPLOAD_FILE_FRAGMENT = "sp1-2023-07"
UPLOAD_FILE_NAME = UPLOAD_FILE_FRAGMENT + "-09.zip"
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_CODE = os.path.join(os.path.dirname(__file__), "testresources", UPLOAD_FILE_NAME)
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
TEST_NEXT_MONTH = "2023-08"
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, TEST_MONTH)

'''
Tests FOSSOlogy python API and configuration
'''
class TestFossology(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        shutil.copytree(TEST_SCAFFOLD_HOME, self.scaffold_home_dir)
        self.config_month_dir = os.path.join(self.scaffold_home_dir, TEST_MONTH)

    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_config(self):
        secrets = loadSecrets(SECRET_FILE_NAME)
        self.assertIsNotNone(secrets)
        fossologyServer = None
        try:
            fossologyServer = fossologySetup(secrets, SECRET_FILE_NAME)
            self.assertIsNotNone(fossologyServer)
        finally:
            if fossologyServer:
                fossologyServer.close()

    def test_upload_code_subproject(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        self.assertIsNotNone(cfg)
        fossologyServer = None
        result = None
        prj = cfg._projects['prj1']
        sp = prj._subprojects['sp1']
        sp._code_path = TEST_SCAFFOLD_CODE
        sp._status = Status.UPLOADEDWS
        project_folder = None
        folder = None
        uploads = []
        try:
            fossologyServer = fossologySetup(cfg._secrets, SECRET_FILE_NAME)
            self.assertIsNotNone(fossologyServer)
            result = doUploadCodeForSubproject(cfg, fossologyServer, prj, sp)
            self.assertTrue(result)
            project_folder = fossologyServer.create_folder(fossologyServer.rootFolder, prj._name)
            self.assertIsNotNone(project_folder)
            dstFolder = f"{prj._name}-{cfg._month}"
            folder = fossologyServer.create_folder(project_folder, dstFolder)
            self.assertIsNotNone(folder)
            uploads = fossologyServer.list_uploads(folder=folder)[0]
            found = False
            for upload in uploads:
                if upload.uploadname == UPLOAD_FILE_NAME:
                    found = True
            self.assertTrue(found)
        finally:
            if fossologyServer:
                if result:
                    # Delete the uploaded file and project folders
                    
                    if project_folder:
                        if folder:
                            for upload in uploads:
                                fossologyServer.delete_upload(upload)
                            fossologyServer.delete_folder(folder)
                        fossologyServer.delete_folder(project_folder)
                fossologyServer.close()

    def test_upload_code_project(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        self.assertIsNotNone(cfg)
        fossologyServer = None
        result = None
        prj = cfg._projects['prj1']
        sp = prj._subprojects['sp1']
        sp._code_path = TEST_SCAFFOLD_CODE
        sp._status = Status.UPLOADEDWS
        project_folder = None
        folder = None
        uploads = []
        try:
            fossologyServer = fossologySetup(cfg._secrets, SECRET_FILE_NAME)
            self.assertIsNotNone(fossologyServer)
            result = doUploadCodeForProject(cfg, fossologyServer, prj)
            self.assertTrue(result)
            project_folder = fossologyServer.create_folder(fossologyServer.rootFolder, prj._name)
            self.assertIsNotNone(project_folder)
            dstFolder = f"{prj._name}-{cfg._month}"
            folder = fossologyServer.create_folder(project_folder, dstFolder)
            self.assertIsNotNone(folder)
            uploads = fossologyServer.list_uploads(folder=folder)[0]
            found = False
            for upload in uploads:
                if upload.uploadname == UPLOAD_FILE_NAME:
                    found = True
            self.assertTrue(found)
        finally:
            if fossologyServer:
                if result:
                    # Delete the uploaded file and project folders
                    if project_folder:
                        if folder:
                            for upload in uploads:
                                fossologyServer.delete_upload(upload)
                            fossologyServer.delete_folder(folder)
                        fossologyServer.delete_folder(project_folder)
                fossologyServer.close()

    def test_get_prior_upload_folder(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        test_folder_name = "test_get_prior_upload_projects"
        test_project_folder_name = "prj_test"
        test_folder = None
        test_project_folder = None
        fossologyServer = None
        try:
            fossologyServer = fossologySetup(cfg._secrets, SECRET_FILE_NAME)
            result = getUploadFolder(fossologyServer, test_project_folder_name)
            self.assertIsNone(result)
            result = getUploadFolder(fossologyServer, test_folder_name)
            self.assertIsNone(result)
            test_project_folder = fossologyServer.create_folder(fossologyServer.rootFolder, test_project_folder_name)
            result = getUploadFolder(fossologyServer, test_project_folder_name)
            self.assertIsNotNone(result)
            result = getUploadFolder(fossologyServer, test_folder_name)
            self.assertIsNone(result)
            test_folder = fossologyServer.create_folder(test_project_folder, test_folder_name)
            result = getUploadFolder(fossologyServer, test_project_folder_name)
            self.assertIsNotNone(result)
            result = getUploadFolder(fossologyServer, test_folder_name)
            self.assertIsNotNone(result)
            
        finally:
            if fossologyServer:
                if test_folder:
                    fossologyServer.delete_folder(test_folder)
                if test_project_folder:
                    fossologyServer.delete_folder(test_project_folder)
                fossologyServer.close()        

    def test_get_prior_upload(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        test_folder_name = "test_get_prior_upload_projects"
        test_project_folder_name = "prj_test"
        test_folder = None
        test_project_folder = None
        test_upload = None
        fossologyServer = None
        upload_name = UPLOAD_FILE_FRAGMENT
        upload = None
        try:
            fossologyServer = fossologySetup(cfg._secrets, SECRET_FILE_NAME)
            test_project_folder = fossologyServer.create_folder(fossologyServer.rootFolder, test_project_folder_name)
            test_folder = fossologyServer.create_folder(test_project_folder, test_folder_name)
            result = getUpload(fossologyServer, test_folder, upload_name)
            self.assertIsNone(result)
            upload = fossologyServer.upload_file(test_folder, file=TEST_SCAFFOLD_CODE, wait_time=10)
            self.assertIsNotNone(upload)
            result = getUpload(fossologyServer, test_folder, upload_name)
            self.assertIsNotNone(result)
        finally:
            if fossologyServer:
                if upload:
                    fossologyServer.delete_upload(upload)
                if test_folder:
                    fossologyServer.delete_folder(test_folder)
                if test_project_folder:
                    fossologyServer.delete_folder(test_project_folder)
                fossologyServer.close()        
        
    def test_prior_upload_exists(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        test_folder_name = "test_get_prior_upload_projects"
        test_project_folder_name = "prj_test"
        test_folder = None
        test_project_folder = None
        test_upload = None
        fossologyServer = None
        upload_name = UPLOAD_FILE_FRAGMENT
        upload = None
        try:
            fossologyServer = fossologySetup(cfg._secrets, SECRET_FILE_NAME)
            test_project_folder = fossologyServer.create_folder(fossologyServer.rootFolder, test_project_folder_name)
            test_folder = fossologyServer.create_folder(test_project_folder, test_folder_name)
            result = uploadExists(fossologyServer, test_folder, upload_name)
            self.assertFalse(result)
            result = uploadExists(fossologyServer, test_folder_name, upload_name)
            self.assertFalse(result)
            upload = fossologyServer.upload_file(test_folder, file=TEST_SCAFFOLD_CODE, wait_time=10)
            result = uploadExists(fossologyServer, test_folder, upload_name)
            self.assertTrue(result)
            result = uploadExists(fossologyServer, test_folder_name, upload_name)
            self.assertTrue(result)
        finally:
            if fossologyServer:
                if upload:
                    fossologyServer.delete_upload(upload)
                if test_folder:
                    fossologyServer.delete_folder(test_folder)
                if test_project_folder:
                    fossologyServer.delete_folder(test_project_folder)
                fossologyServer.close()        

    def test_do_run_agents_for_subproject(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects['prj1']
        sp = prj._subprojects['sp1']
        sp._code_path = TEST_SCAFFOLD_CODE
        sp._status = Status.UPLOADEDWS
        test_folder = None
        test_reuse_folder = None
        test_project_folder = None
        test_upload = None
        fossologyServer = None
        upload_name = UPLOAD_FILE_NAME
        upload = None
        reuse_upload = None
        reuseFile = os.path.join(self.temp_dir.name, "sp1-2023-10-10.zip")
        shutil.copyfile(TEST_SCAFFOLD_CODE, reuseFile)
        try:
            fossologyServer = fossologySetup(cfg._secrets, SECRET_FILE_NAME)
            test_project_folder = fossologyServer.create_folder(fossologyServer.rootFolder, prj._name)
            self.assertIsNotNone(test_project_folder)
            dstFolder = f"{prj._name}-{cfg._month}"
            test_folder = fossologyServer.create_folder(test_project_folder, dstFolder)
            self.assertIsNotNone(test_folder)
            upload = fossologyServer.upload_file(test_folder, file=TEST_SCAFFOLD_CODE, wait_time=10)
            self.assertIsNotNone(upload)
            result = doRunAgentsForSubproject(cfg, fossologyServer, prj, sp)
            self.assertTrue(result)
            jobs = fossologyServer.list_jobs(upload=upload)[0]
            for job in jobs:
                self.assertEqual(job.status, "Completed")
            # Test reuse
            cfg._month = "2023-10"
            sp._code_path = "sp1-2023-10-10.zip"
            reuseDstFolder = f"{prj._name}-{cfg._month}"
            test_reuse_folder = fossologyServer.create_folder(test_project_folder, reuseDstFolder)
            self.assertIsNotNone(test_reuse_folder)
            reuse_upload = fossologyServer.upload_file(test_reuse_folder, file=reuseFile, wait_time=10)
            self.assertIsNotNone(reuse_upload)
            result = doRunAgentsForSubproject(cfg, fossologyServer, prj, sp)
            self.assertTrue(result)
            jobs = fossologyServer.list_jobs(upload=reuse_upload)[0]
            for job in jobs:
                self.assertEqual(job.status, "Completed")
        finally:
            os.remove(reuseFile)
            if fossologyServer:
                if upload:
                    fossologyServer.delete_upload(upload)
                if reuse_upload:
                    fossologyServer.delete_upload(reuse_upload)
                if test_folder:
                    fossologyServer.delete_folder(test_folder)
                if test_reuse_folder:
                    fossologyServer.delete_folder(test_reuse_folder)
                if test_project_folder:
                    fossologyServer.delete_folder(test_project_folder)
                fossologyServer.close()        

    def test_newmonth(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        cfg._fossology_job_spec["analysis"]["bucket"] = True
        copyToNextMonth(self.scaffold_home_dir, cfg)
        next_month_dir = os.path.join(self.scaffold_home_dir, TEST_NEXT_MONTH)
        next_cfg_file = os.path.join(next_month_dir, "config.json")
        next_cfg = loadConfig(next_cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        self.assertTrue(next_cfg._fossology_job_spec["analysis"]["bucket"])
    
    def test_spdx_report(self):
        cfg_file = os.path.join(self.config_month_dir, "config.json")       
        cfg = loadConfig(cfg_file, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects['prj1']
        sp = prj._subprojects['sp1']
        sp._code_path = TEST_SCAFFOLD_CODE
        sp._status = Status.UPLOADEDWS
        test_folder = None
        test_project_folder = None
        test_upload = None
        fossologyServer = None
        upload_name = UPLOAD_FILE_NAME
        upload = None
        cfg._storepath = self.scaffold_home_dir
        spdxFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
        spdxFilename = f"{sp._name}-{sp._code_pulled}.spdx"
        spdxFile = os.path.join(spdxFolder, spdxFilename)
        try:
            # Setup and scan a project
            fossologyServer = fossologySetup(cfg._secrets, SECRET_FILE_NAME)
            test_project_folder = fossologyServer.create_folder(fossologyServer.rootFolder, prj._name)
            self.assertIsNotNone(test_project_folder)
            dstFolder = f"{prj._name}-{cfg._month}"
            test_folder = fossologyServer.create_folder(test_project_folder, dstFolder)
            self.assertIsNotNone(test_folder)
            upload = fossologyServer.upload_file(test_folder, file=TEST_SCAFFOLD_CODE, wait_time=10)
            self.assertIsNotNone(upload)
            result = doRunAgentsForSubproject(cfg, fossologyServer, prj, sp)
            self.assertTrue(result)
            jobs = fossologyServer.list_jobs(upload=upload)[0]
            for job in jobs:
                self.assertEqual(job.status, "Completed")
                
            # Test spdx file generation
            result = doGetSPDXForSubproject(cfg, fossologyServer, prj, sp)
            self.assertTrue(result)
            self.assertTrue(os.path.isfile(spdxFile))
        finally:
            if fossologyServer:
                if upload:
                    fossologyServer.delete_upload(upload)
                if test_folder:
                    fossologyServer.delete_folder(test_folder)
                if test_project_folder:
                    fossologyServer.delete_folder(test_project_folder)
                fossologyServer.close()

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

        
if __name__ == '__main__':
    unittest.main()
        