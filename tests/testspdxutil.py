import unittest
import os
import tempfile
import shutil
import spdx.spdxutil as spdxutil
import spdx.xlsx as xlsx
import pdb

TRIVY_SPDX_FILENAME = "test-trivy-spdx.json"
TEST_TRIVY_SPDX_PATH = os.path.join(os.path.dirname(__file__), "testresources", TRIVY_SPDX_FILENAME)
LARGE_SPDX_FILENAME = "cncf-3-keycloak-spdx.json"
TEST_LARGE_SPDX_PATH = os.path.join(os.path.dirname(__file__), "testresources", LARGE_SPDX_FILENAME)

TEST_PACKAGES = {
    "pom.xml" : {
        "spdxId": "SPDXRef-Application-f8f4c07e63afadde",
        "licenseConcluded": "",
        "licenseDeclared": "",
        "version": "",
        "purl": "",
        "dependency": "Spdx-Java-Library CONTAINS"
    },
    "com.google.code.findbugs:jsr305": {
        "spdxId": "SPDXRef-Package-a5a3d0c814baaf49",
        "licenseConcluded": "Apache-2.0",
        "licenseDeclared": "Apache-2.0",
        "version": "3.0.2",
        "purl": "pkg:maven/com.google.code.findbugs/jsr305@3.0.2",
        "dependency": "org.spdx:java-spdx-library DEPENDS_ON"
    },
    "Spdx-Java-Library": {
        "spdxId": "SPDXRef-Filesystem-19f216bbde3b8f09",
        "licenseConcluded": "",
        "licenseDeclared": "",
        "version": "",
        "purl": "",
        "dependency": "SPDXRef-DOCUMENT DESCRIBES"
    },
    "com.google.code.gson:gson": {
        "spdxId": "SPDXRef-Package-6cc7d905fac3347c",
        "licenseConcluded": "Apache-2.0",
        "licenseDeclared": "Apache-2.0",
        "version": "2.8.9",
        "purl": "pkg:maven/com.google.code.gson/gson@2.8.9",
        "dependency": "org.spdx:java-spdx-library DEPENDS_ON"
    },
    "org.apache.commons:commons-lang3": {
        "spdxId": "SPDXRef-Package-9d14d5f84f12114a",
        "version": "3.5",
        "licenseConcluded": "Apache-2.0",
        "licenseDeclared": "Apache-2.0",
        "purl": "pkg:maven/org.apache.commons/commons-lang3@3.5",
        "dependency": "org.spdx:java-spdx-library DEPENDS_ON"
    },
    "org.jsoup:jsoup": {
        "spdxId": "SPDXRef-Package-9d14d5f84f12114a",
        "version": "1.15.3",
        "licenseConcluded": "The-MIT-License",
        "licenseDeclared": "The-MIT-License",
        "purl": "pkg:maven/org.jsoup/jsoup@1.15.3",
        "dependency": "org.spdx:java-spdx-library DEPENDS_ON"
    },
    "org.slf4j:slf4j-api": {
        "spdxId": "SPDXRef-Package-27c560513d549c66",
        "version": "2.0.7",
        "licenseConcluded": "MIT-License",
        "licenseDeclared": "MIT-License",
        "purl": "pkg:maven/org.slf4j/slf4j-api@2.0.7",
        "dependency": "org.spdx:java-spdx-library DEPENDS_ON"
    },
    "org.spdx:java-spdx-library": {
        "spdxId": "SPDXRef-Package-a5eeefe868200aae",
        "version": "1.1.13-SNAPSHOT",
        "licenseConcluded": "Apache-2.0",
        "licenseDeclared": "Apache-2.0",
        "purl": "pkg:maven/org.spdx/java-spdx-library@1.1.13-SNAPSHOT",
        "dependency": "pom.xml CONTAINS"
    }
}


'''
Tests Trivy manual agent commands
'''
class TestSpdxUtil(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.trivy_json_path = os.path.join(self.temp_dir.name, TRIVY_SPDX_FILENAME)
        shutil.copy(TEST_TRIVY_SPDX_PATH, self.trivy_json_path)
        self.large_json_path = os.path.join(self.temp_dir.name, LARGE_SPDX_FILENAME)
        shutil.copy(TEST_LARGE_SPDX_PATH, self.large_json_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_createxlsx(self):
        spdxDoc = spdxutil.parseFile(self.trivy_json_path)
        workbook = xlsx.makeXlsx(spdxDoc)
        ws = workbook.active
        self.assertEqual(len(TEST_PACKAGES), ws.max_row-1)
        for i in range(2, ws.max_row+1):
            pkg = TEST_PACKAGES[ws.cell(i, 1).value]
            self.assertIsNotNone(pkg)
            self.assertEqual(pkg['licenseDeclared'], ws.cell(i, 2).value)
            self.assertEqual(pkg['version'], ws.cell(i, 3).value)
            self.assertEqual(pkg['purl'], ws.cell(i, 4).value)
            self.assertEqual(pkg['dependency'], ws.cell(i, 5).value)
        
    def test_largexlsx(self):
        spdxDoc = spdxutil.parseFile(self.large_json_path)
        workbook = xlsx.makeXlsx(spdxDoc)
        ws = workbook.active
        self.assertTrue(ws.max_row > 1000)
        # TEMP
        # xlsxpath = os.path.join(self.temp_dir.name, "sample_report.xlsx")
        # xlsx.saveXlsx(workbook, xlsxpath)
        # pdb.set_trace()
        
if __name__ == '__main__':
    unittest.main()
        