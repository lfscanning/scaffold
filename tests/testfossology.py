import unittest
import pdb
import os
import tempfile
import shutil
from scaffold import fossologySetup
from config import loadSecrets, loadConfig
from uploadcode import doUploadCodeForSubproject, doUploadCodeForProject
from datatypes import Status

SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_CODE = os.path.join(os.path.dirname(__file__), "testresources", "testuploads.zip")
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH = "2023-07"
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
        cfg_file = os.path.join(TEST_MONTH_DIR, "config.json")
        
        cfg = loadConfig(cfg_file, TEST_SCAFFOLD_HOME, SECRET_FILE_NAME)
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
                if upload.uploadname == "testuploads.zip":
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
        cfg_file = os.path.join(TEST_MONTH_DIR, "config.json")
        
        cfg = loadConfig(cfg_file, TEST_SCAFFOLD_HOME, SECRET_FILE_NAME)
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
                if upload.uploadname == "testuploads.zip":
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

if __name__ == '__main__':
    unittest.main()
        