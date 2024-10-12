# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import unittest
import os
import tempfile
import shutil
import spdx.spdxutil as spdxutil
import spdx.xlsx as xlsx
from config import loadConfig
from spdx_tools.spdx.model.document import Document
from spdx_tools.spdx.model.package import Package
from spdx_tools.spdx.model.package import ExternalPackageRef
from spdx_tools.spdx.model.package import ExternalPackageRefCategory
from spdx_tools.spdx.model.package import PackagePurpose
from spdx_tools.spdx.model.actor import ActorType
from spdx_tools.spdx.model.relationship import Relationship
from spdx_tools.spdx.model.relationship import RelationshipType
from spdx_tools.spdx.model import SpdxNoAssertion
from spdx_tools.spdx.model import SpdxNone
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document
import spdx_tools.spdx.document_utils as document_utils
import spdx_tools.spdx.spdx_element_utils as spdx_element_utils
from license_expression import get_spdx_licensing
import re

TRIVY_SPDX_FILENAME = "test-trivy-spdx.json"
TEST_TRIVY_SPDX_PATH = os.path.join(os.path.dirname(__file__), "testresources", TRIVY_SPDX_FILENAME)
LARGE_SPDX_FILENAME = "cncf-3-keycloak-spdx.json"
TEST_LARGE_SPDX_PATH = os.path.join(os.path.dirname(__file__), "testresources", LARGE_SPDX_FILENAME)
MATERIALX_CONFIG_FILENAME = "test-materialx-conf.json"
MATERIALX_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "testresources", MATERIALX_CONFIG_FILENAME)
MATERIALX_TRIVY_FILENAME = "MaterialX-2024-08-21-trivy-spdx.json"
MATERIALX_TRIVY_PATH = os.path.join(os.path.dirname(__file__), "testresources", MATERIALX_TRIVY_FILENAME)
SECRET_FILE_NAME = ".test-scaffold-secrets.json"
SPDX_TOOLS_JAVA_FILENAME = "spdx-tools-java-git-license-spdx.json"
SPDX_TOOLS_JAVA_PATH = os.path.join(os.path.dirname(__file__), "testresources", SPDX_TOOLS_JAVA_FILENAME)

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
        self.materialx_trivy_path = os.path.join(self.temp_dir.name, MATERIALX_TRIVY_FILENAME)
        shutil.copy(MATERIALX_TRIVY_PATH, self.materialx_trivy_path)
        self.scaffold_home_dir = os.path.join(self.temp_dir.name, "scaffold")
        os.mkdir(self.scaffold_home_dir)
        os.mkdir(os.path.join(self.scaffold_home_dir, 'spdxrepos'))
        self.config_dir = os.path.join(self.scaffold_home_dir, '2024-08')
        os.mkdir(self.config_dir)
        self.materialx_config_path = os.path.join(self.config_dir, MATERIALX_CONFIG_FILENAME)
        shutil.copy(MATERIALX_CONFIG_PATH, self.materialx_config_path)
        self.spdx_tools_java_path = os.path.join(self.temp_dir.name, SPDX_TOOLS_JAVA_FILENAME)
        shutil.copy(SPDX_TOOLS_JAVA_PATH, self.spdx_tools_java_path)
        

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_createxlsx(self):
        spdx_document = spdxutil.parseFile(self.trivy_json_path)
        workbook = xlsx.makeXlsx(spdx_document)
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
        spdx_document = spdxutil.parseFile(self.large_json_path)
        workbook = xlsx.makeXlsx(spdx_document)
        ws = workbook.active
        self.assertTrue(ws.max_row > 1000)
        # TEMP
        # xlsxpath = os.path.join(self.temp_dir.name, "sample_report.xlsx")
        # xlsx.saveXlsx(workbook, xlsxpath)
        # pdb.set_trace()
        
    def testFixLicenses(self):
        licensing = get_spdx_licensing()
        extracted_licensing_info = []
        result = spdxutil.fix_license('CC-BY-3.0+', extracted_licensing_info, licensing)
        self.assertEqual('LicenseRef-CC-BY-3.0-', str(result))
        self.assertEquals(1, len(extracted_licensing_info))
        license_declared = licensing.parse('GPL-2.0-or-later AND some-random-declared-id')
        license_concluded = licensing.parse('some-random-concluded-id AND some-random-declared-id')
        result_declared = spdxutil.fix_license(license_declared, extracted_licensing_info, licensing)
        self.assertTrue('AND' in str(result_declared))
        self.assertTrue('GPL-2.0-or-later' in str(result_declared))
        self.assertTrue('LicenseRef-' in str(result_declared))
        result_concluded = spdxutil.fix_license(license_concluded, extracted_licensing_info, licensing)
        self.assertTrue('LicenseRef-' in str(result_concluded))
        self.assertEqual(3, len(extracted_licensing_info))
        found_declared = False
        found_concluded = False
        for extracted in extracted_licensing_info:
            if 'some-random-concluded-id' in extracted.extracted_text:
                found_concluded = True
            elif 'some-random-declared-id' in extracted.extracted_text:
                found_declared = True
        self.assertTrue(found_concluded)
        self.assertTrue(found_declared)
    
    def testRegressionToolsJava(self):
        self.maxDiff = None
        spdx_document = spdxutil.parseFile(self.spdx_tools_java_path)
        cfg = loadConfig(self.materialx_config_path, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects['aswf']
        sp = prj._subprojects['spdx-tools-java']
        spdxutil.augmentTrivyDocument(spdx_document, cfg, prj, sp)
        errors = validate_full_spdx_document(spdx_document)
        self.assertFalse(errors)
        
    def testFixTrivyDocument(self):
        self.maxDiff = None
        spdx_document = spdxutil.parseFile(self.materialx_trivy_path)
        cfg = loadConfig(self.materialx_config_path, self.scaffold_home_dir, SECRET_FILE_NAME)
        prj = cfg._projects['aswf']
        sp = prj._subprojects['materialx']
        spdxutil.augmentTrivyDocument(spdx_document, cfg, prj, sp)
        for relationship in spdx_document.relationships:
            if relationship.relationship_type == RelationshipType.DESCRIBES and relationship.spdx_element_id == 'SPDXRef-DOCUMENT' and \
                    spdx_element_utils.get_element_type_from_spdx_id(relationship.related_spdx_element_id, spdx_document) == Package:
                describes = document_utils.get_element_from_spdx_id(spdx_document, relationship.related_spdx_element_id)
        self.assertEqual('aswf.materialx', describes.name)
        self.assertEqual('(BSD-3-Clause AND BSD-3-Clause AND CC-BY-3.0 AND BSD-3-Clause AND CC-BY-4.0 AND LicenseRef-CC-BY-3.0-) OR (MIT AND CC-BY-4.0 AND AMPAS AND Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND Apache-2.0 AND CC-BY-4.0 AND CC-BY-4.0 AND CC-BY-4.0 AND MPL-2.0 AND MPL-2.0 AND CC-BY-4.0 AND MPL-2.0 AND LicenseRef-DreamWorks-BSD-style-1)', \
                            str(describes.license_declared))
        
        self.assertEqual('(BSD-3-Clause AND BSD-3-Clause AND CC-BY-3.0 AND BSD-3-Clause AND CC-BY-4.0 AND LicenseRef-CC-BY-3.0-) OR (MIT AND CC-BY-4.0 AND AMPAS AND Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND Apache-2.0 AND CC-BY-4.0 AND CC-BY-4.0 AND CC-BY-4.0 AND MPL-2.0 AND MPL-2.0 AND CC-BY-4.0 AND MPL-2.0 AND LicenseRef-DreamWorks-BSD-style-1)', \
                            str(describes.license_concluded))
        contained = []
        for relationship in spdx_document.relationships:
            if relationship.relationship_type == RelationshipType.CONTAINS and relationship.spdx_element_id == describes.spdx_id:
                repo_pkg = document_utils.get_element_from_spdx_id(spdx_document, relationship.related_spdx_element_id)
                contained.append(repo_pkg)
                if repo_pkg.name == 'MaterialX':
                    materialx_pkg = repo_pkg
        self.assertEqual(3, len(contained))
        self.assertEqual('Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND Apache-2.0 AND CC-BY-4.0', str(materialx_pkg.license_declared))
        self.assertEqual(SpdxNoAssertion(), materialx_pkg.license_concluded)
        self.assertEqual('https://github.com/AcademySoftwareFoundation/MaterialX/archive/153a803c46181319fd782ef8426ff58a2e885d82.zip', materialx_pkg.download_location)
        self.assertEqual(1, len(materialx_pkg.external_references))
        self.assertEqual(ExternalPackageRefCategory.PACKAGE_MANAGER, materialx_pkg.external_references[0].category)
        self.assertEqual('purl', materialx_pkg.external_references[0].reference_type)
        self.assertEqual('pkg:github/AcademySoftwareFoundation/MaterialX@153a803c46181319fd782ef8426ff58a2e885d82', materialx_pkg.external_references[0].locator)
        self.assertEqual('153a803c46181319fd782ef8426ff58a2e885d82', materialx_pkg.version)
        self.assertEqual(PackagePurpose.SOURCE, materialx_pkg.primary_package_purpose)
        self.assertEqual(ActorType.ORGANIZATION, materialx_pkg.supplier.actor_type)
        self.assertEqual('Linux Foundation Project aswf', materialx_pkg.supplier.name)
        # Check for fixing up the contains relationships
        fixed_relationships = []
        for relationship in spdx_document.relationships:
            if relationship.related_spdx_element_id == 'SPDXRef-Application-95ffd6aeac0971a4':
                fixed_relationships.append(relationship)
        self.assertEqual(1, len(fixed_relationships))
        self.assertEqual(RelationshipType.CONTAINS, fixed_relationships[0].relationship_type)
        # Check the annotation fixes
        found_annotation = False
        # TODO make sure the package attribution text is removed
        for annotation in spdx_document.annotations:
            if annotation.annotation_comment == 'Class: lang-pkgs':
                found_annotation = True
        self.assertTrue(found_annotation)
        
        # Test for modification to creation info
        found_scaffold = False
        found_lf = False
        for creator in spdx_document.creation_info.creators:
            if creator.name == 'Scaffold' and creator.actor_type == ActorType.TOOL:
                found_scaffold = True
            if creator.name == 'Linux Foundation' and creator.actor_type == ActorType.ORGANIZATION:
                found_lf = True
        self.assertTrue(found_scaffold)
        self.assertTrue(found_lf)
        errors = validate_full_spdx_document(spdx_document)
        self.assertFalse(errors)
        
if __name__ == '__main__':
    unittest.main()
        