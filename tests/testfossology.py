import unittest
import pdb
import os
from scaffold import fossologySetup
from config import loadSecrets, loadConfig

SECRET_FILE_NAME = ".test-scaffold-secrets.json"
TEST_SCAFFOLD_HOME = os.path.join(os.path.dirname(__file__), "testresources", "scaffoldhome")
TEST_MONTH_DIR = os.path.join(TEST_SCAFFOLD_HOME, "2023-07")

'''
Tests FOSSOlogy python API and configuration
'''
class TestFossology(unittest.TestCase):

    def test_config(self):
        pdb.set_trace()
        secrets = loadSecrets(SECRET_FILE_NAME)
        self.assertIsNotNone(secrets)
        fossologyServer = None
        try:
            fossologyServer = fossologySetup(secrets, SECRET_FILE_NAME)
            self.assertIsNotNone(fossologyServer)
        finally:
            if fossologyServer:
                fossologyServer.close()

'''
    def test_upload_code(self):
        pdb.set_trace()
        cfg_file = os.path.join(TEST_MONTH_DIR, "config.json")
        
        cfg = loadConfig(cfg_file, TEST_SCAFFOLD_HOME, SECRET_FILE_NAME)
        self.assertIsNotNone(cfg)
        try:
            fossologyServer = fossologySetup(cfg._secrets)
            self.assertIsNotNone(fossologyServer)
            pbd.set_trace()
            
        finally:
            if fossologyServer:
                fossologyServer.close()
'''

if __name__ == '__main__':
    unittest.main()
        