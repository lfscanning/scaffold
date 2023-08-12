import unittest
import pdb
from scaffold import fossologySetup
from config import loadSecrets

SECRET_FILE_NAME = '.test-scaffold-secrets.json'

'''
Tests FOSSOlogy python API and configuration
'''
class TestFossology(unittest.TestCase):

    def test_config(self):
        pdb.set_trace()
        secrets = loadSecrets(SECRET_FILE_NAME)
        self.assertIsNotNone(secrets)
        try:
            fossologyServer = fossologySetup(secrets)
            self.assertIsNotNone(fossologyServer)
        finally:
            if fossologyServer:
                fossologyServer.close()

if __name__ == '__main__':
    unittest.main()
        