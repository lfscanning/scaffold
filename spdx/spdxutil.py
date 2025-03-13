# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

# Utility class to support merging / fixing up SPDX documents

from license_expression import get_spdx_licensing, LicenseSymbol
from spdx_tools.spdx.model.package import Package
from spdx_tools.spdx.model.package import ExternalPackageRef
from spdx_tools.spdx.model.package import ExternalPackageRefCategory
from spdx_tools.spdx.model.package import PackagePurpose
from spdx_tools.spdx.model.actor import Actor
from spdx_tools.spdx.model.annotation import Annotation
from spdx_tools.spdx.model.annotation import AnnotationType
from spdx_tools.spdx.model.actor import ActorType
from spdx_tools.spdx.model.relationship import Relationship
from spdx_tools.spdx.model.relationship import RelationshipType
from spdx_tools.spdx.model.extracted_licensing_info import ExtractedLicensingInfo
from spdx_tools.spdx.model import SpdxNoAssertion
from spdx_tools.spdx.model import SpdxNone
from spdx_tools.spdx.parser.parse_anything import parse_file
from spdx_tools.spdx.writer.write_anything import write_file
from spdx_tools.common.spdx_licensing import spdx_licensing as tools_python_licensing
import spdx_tools.spdx.document_utils as document_utils
import spdx_tools.spdx.spdx_element_utils as spdx_element_utils
from datatypes import ProjectRepoType
from slmjson import loadSLMCategories
import re
import os
import json

'''
updates the licensing parser for SPDX and adds back in missing symbols
for NONE, NOASSERTION and deprecated licenses
'''
def updateLicensing(licensing):
    licensing.known_symbols['NOASSERTION'] = LicenseSymbol('NOASSERTION')
    licensing.known_symbols['NONE'] = LicenseSymbol('NONE')
    licensing.known_symbols['AGPL-1.0'] = LicenseSymbol('AGPL-1.0')
    licensing.known_symbols['AGPL-3.0'] = LicenseSymbol('AGPL-3.0')
    licensing.known_symbols['BSD-2-Clause-FreeBSD'] = LicenseSymbol('BSD-2-Clause-FreeBSD')
    licensing.known_symbols['BSD-2-Clause-NetBSD'] = LicenseSymbol('BSD-2-Clause-NetBSD')
    licensing.known_symbols['bzip2-1.0.5'] = LicenseSymbol('bzip2-1.0.5')
    licensing.known_symbols['eCos-2.0'] = LicenseSymbol('eCos-2.0')
    licensing.known_symbols['GFDL-1.1'] = LicenseSymbol('GFDL-1.1')
    licensing.known_symbols['GFDL-1.2'] = LicenseSymbol('GFDL-1.2')
    licensing.known_symbols['GFDL-1.3'] = LicenseSymbol('GFDL-1.3')
    licensing.known_symbols['GPL-1.0'] = LicenseSymbol('GPL-1.0')
    licensing.known_symbols['GPL-1.0+'] = LicenseSymbol('GPL-1.0+')
    licensing.known_symbols['GPL-2.0'] = LicenseSymbol('GPL-2.0')
    licensing.known_symbols['GPL-2.0+'] = LicenseSymbol('GPL-2.0+')
    licensing.known_symbols['GPL-2.0-with-autoconf-exception'] = LicenseSymbol('GPL-2.0-with-autoconf-exception')
    licensing.known_symbols['GPL-2.0-with-bison-exception'] = LicenseSymbol('GPL-2.0-with-bison-exception')
    licensing.known_symbols['GPL-2.0-with-classpath-exception'] = LicenseSymbol('GPL-2.0-with-classpath-exception')
    licensing.known_symbols['GPL-2.0-with-font-exception'] = LicenseSymbol('GPL-2.0-with-font-exception')
    licensing.known_symbols['GPL-2.0-with-GCC-exception'] = LicenseSymbol('GPL-2.0-with-GCC-exception')
    licensing.known_symbols['GPL-3.0'] = LicenseSymbol('GPL-3.0')
    licensing.known_symbols['GPL-3.0+'] = LicenseSymbol('GPL-3.0+')
    licensing.known_symbols['GPL-3.0-with-autoconf-exception'] = LicenseSymbol('GPL-3.0-with-autoconf-exception')
    licensing.known_symbols['GPL-3.0-with-GCC-exception'] = LicenseSymbol('GPL-3.0-with-GCC-exception')
    licensing.known_symbols['LGPL-2.0'] = LicenseSymbol('LGPL-2.0')
    licensing.known_symbols['LGPL-2.0+'] = LicenseSymbol('LGPL-2.0+')
    licensing.known_symbols['LGPL-2.1'] = LicenseSymbol('LGPL-2.1')
    licensing.known_symbols['LGPL-2.1+'] = LicenseSymbol('LGPL-2.1+')
    licensing.known_symbols['LGPL-3.0'] = LicenseSymbol('LGPL-3.0')
    licensing.known_symbols['LGPL-3.0+'] = LicenseSymbol('LGPL-3.0+')
    licensing.known_symbols['Net-SNMP'] = LicenseSymbol('Net-SNMP')
    licensing.known_symbols['Nunit'] = LicenseSymbol('Nunit')
    licensing.known_symbols['StandardML-NJ'] = LicenseSymbol('StandardML-NJ')
    licensing.known_symbols['wxWindows'] = LicenseSymbol('wxWindows')


    licensing.known_symbols_lowercase['noassertion'] = LicenseSymbol('NOASSERTION')
    licensing.known_symbols_lowercase['none'] = LicenseSymbol('NONE')
    licensing.known_symbols_lowercase['agpl-1.0'] = LicenseSymbol('AGPL-1.0')
    licensing.known_symbols_lowercase['agpl-3.0'] = LicenseSymbol('AGPL-3.0')
    licensing.known_symbols_lowercase['bsd-2-clause-freebsd'] = LicenseSymbol('BSD-2-Clause-FreeBSD')
    licensing.known_symbols_lowercase['bsd-2-clause-netbsd'] = LicenseSymbol('BSD-2-Clause-NetBSD')
    licensing.known_symbols_lowercase['bzip2-1.0.5'] = LicenseSymbol('bzip2-1.0.5')
    licensing.known_symbols_lowercase['ecos-2.0'] = LicenseSymbol('eCos-2.0')
    licensing.known_symbols_lowercase['gfdl-1.1'] = LicenseSymbol('GFDL-1.1')
    licensing.known_symbols_lowercase['gfdl-1.2'] = LicenseSymbol('GFDL-1.2')
    licensing.known_symbols_lowercase['gfdl-1.3'] = LicenseSymbol('GFDL-1.3')
    licensing.known_symbols_lowercase['gpl-1.0'] = LicenseSymbol('GPL-1.0')
    licensing.known_symbols_lowercase['gpl-1.0+'] = LicenseSymbol('GPL-1.0+')
    licensing.known_symbols_lowercase['gpl-2.0'] = LicenseSymbol('GPL-2.0')
    licensing.known_symbols_lowercase['gpl-2.0+'] = LicenseSymbol('GPL-2.0+')
    licensing.known_symbols_lowercase['gpl-2.0-with-autoconf-exception'] = LicenseSymbol('GPL-2.0-with-autoconf-exception')
    licensing.known_symbols_lowercase['gpl-2.0-with-bison-exception'] = LicenseSymbol('GPL-2.0-with-bison-exception')
    licensing.known_symbols_lowercase['gpl-2.0-with-classpath-exception'] = LicenseSymbol('GPL-2.0-with-classpath-exception')
    licensing.known_symbols_lowercase['gpl-2.0-with-font-exception'] = LicenseSymbol('GPL-2.0-with-font-exception')
    licensing.known_symbols_lowercase['gpl-2.0-with-gcc-exception'] = LicenseSymbol('GPL-2.0-with-GCC-exception')
    licensing.known_symbols_lowercase['gpl-3.0'] = LicenseSymbol('GPL-3.0')
    licensing.known_symbols_lowercase['gpl-3.0+'] = LicenseSymbol('GPL-3.0+')
    licensing.known_symbols_lowercase['gpl-3.0-with-autoconf-exception'] = LicenseSymbol('GPL-3.0-with-autoconf-exception')
    licensing.known_symbols_lowercase['gpl-3.0-with-gcc-exception'] = LicenseSymbol('GPL-3.0-with-GCC-exception')
    licensing.known_symbols_lowercase['lgpl-2.0'] = LicenseSymbol('LGPL-2.0')
    licensing.known_symbols_lowercase['lgpl-2.0+'] = LicenseSymbol('LGPL-2.0+')
    licensing.known_symbols_lowercase['lgpl-2.1'] = LicenseSymbol('LGPL-2.1')
    licensing.known_symbols_lowercase['lgpl-2.1+'] = LicenseSymbol('LGPL-2.1+')
    licensing.known_symbols_lowercase['lgpl-3.0'] = LicenseSymbol('LGPL-3.0')
    licensing.known_symbols_lowercase['lgpl-3.0+'] = LicenseSymbol('LGPL-3.0+')
    licensing.known_symbols_lowercase['net-snmp'] = LicenseSymbol('Net-SNMP')
    licensing.known_symbols_lowercase['nunit'] = LicenseSymbol('Nunit')
    licensing.known_symbols_lowercase['standardml-nj'] = LicenseSymbol('StandardML-NJ')
    licensing.known_symbols_lowercase['wxwindows'] = LicenseSymbol('wxWindows')

'''
Gets the licensing parser for SPDX and adds back in missing symbols
for NONE, NOASSERTION and deprecated licenses
'''
def getLicensing():
    licensing = get_spdx_licensing()
    updateLicensing(licensing)
    return licensing

'''
Parses the SPDX JSON file for any license expressions that do not parse
Fix these license by converting them to an extracted license info
'''
def fixLicenseExpressions(fileName):
    with open(fileName, 'r', encoding='utf-8') as file:
        spdxJson = json.load(file)
    extractedLicenseText = {}
    licensing = getLicensing()
    _fix_license_expressions(spdxJson, extractedLicenseText, licensing)
    if extractedLicenseText:
        if 'hasExtractedLicensingInfos' in spdxJson:
            extracted = spdxJson['hasExtractedLicensingInfos']
        else:
            extracted = []
            spdxJson['hasExtractedLicensingInfos'] = extracted
        for lic in extractedLicenseText.values():
            extracted.append(lic)
    with open(fileName, 'w', encoding='utf-8') as file:
        json.dump(spdxJson, file)

def _fix_license_expressions(elementJson, extractedLicenseText, licensing):
    if isinstance(elementJson, dict):
        fixedLicenses = {}
        for key, value in elementJson.items():
            if key == "licenseConcluded" or key == "licenseDeclared":
                try:
                    for lic_symbol in licensing.license_symbols(value):
                        if str(lic_symbol).startswith("LicenseRef-"):
                            licensing.known_symbols[str(lic_symbol)] = lic_symbol
                    test = licensing.parse(value, validate=True, strict=True)
                except:
                    if not value in extractedLicenseText:
                        licenseId = 'LicenseRef-fixed-' + hex(abs(hash(value)))
                        extractedLicenseText[value] = {
                            "licenseId": licenseId,
                            "extractedText": value
                        }
                    else:
                        licenseId = extractedLicenseText[value]['licenseId']
                    fixedLicenses[key] = licenseId
            else:
                _fix_license_expressions(value, extractedLicenseText, licensing)
        for key, value in fixedLicenses.items():
            elementJson[key] = value
    elif isinstance(elementJson, list):
        for value in elementJson:
            _fix_license_expressions(value, extractedLicenseText, licensing)

'''
Parses an SPDX file with a supported file extension
Raises SPDXParsingError on parsing errors
'''
def parseFile(file):
    updateLicensing(tools_python_licensing)
    return parse_file(file)

'''
writes an SPDX document to a file in the format dictated by the file extension
'''
def writeFile(spdx_document, file):
    write_file(spdx_document, file, validate=False)
    print("SPDX successfully written")
    
def augmentTrivyDocument(spdx_document, cfg, prj, sp):
    remove_dup_packages(spdx_document)
    licensing = getLicensing()
    # find the root of the document
    describes = None
    for relationship in spdx_document.relationships:
        if relationship.relationship_type == RelationshipType.DESCRIBES and relationship.spdx_element_id == 'SPDXRef-DOCUMENT' and \
                spdx_element_utils.get_element_type_from_spdx_id(relationship.related_spdx_element_id, spdx_document) == Package:
            describes = document_utils.get_element_from_spdx_id(spdx_document, relationship.related_spdx_element_id)
    if describes == None:
        print("No document describes, Trivy document not augmented")
        return False
    # Set the name to the "project.subproject"
    describes.name = prj._name + "." + sp._name
    # set the version to the date the analysis was run
    describes.version = cfg._month
    # Collect the project licenses and set the project license to the AND of all project licenses
    # if subproject policy name is an empty string, then use the first
    # policy if there is only one (if there's more than one, error out)
    if sp._slm_policy_name == "":
        if len(prj._slm_policies) == 1:
            policy = list(prj._slm_policies.values())[0]
        else:
            print(f"{prj._name}/{sp._name}: no slm policy specified for subproject but project has multiple policies, won't fix the Trivy SBOM")
            return False
    # otherwise get the right policy for this subproject, or fail if we can't
    else:
        try:
            policy = prj._slm_policies[sp._slm_policy_name]
        except KeyError:
            print(f"{prj._name}/{sp._name}: slm policy name \"{sp._slm_policy_name}\" not defined, won't fix the Trivy SBOM")
            return False
    subproject_licenses = []
    for category in policy._category_configs:
        if category._name == "Project Licenses":
            if len(category._license_configs) > 0:
                subproject_licenses.append(category._license_configs[0]._name)
    try:
        subprojectDeclaredLicense = licenseStringsToExpression(subproject_licenses, spdx_document.extracted_licensing_info, licensing)
    except:
        print(f'Error converting license IDs to expressions for {subproject_licenses}.  Fix the config file to contain accurate SPDX license IDs')
        return False
    # Create the concluded license with the AND of all the found licenses from FOSSOlogy
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    jsonFilename = f"{sp._name}-{sp._code_pulled}.json"
    jsonPath = os.path.join(reportFolder, jsonFilename)
    if os.path.exists(jsonPath):
        # load JSON license scan results
        categories = loadSLMCategories(prj, sp, jsonPath)
        subprojectConcludedLicenses = []
        for cat in categories:
            # skip category if it has no files
            if cat._numfiles > 0:
                for lic in cat._licenses:
                    if lic._numfiles > 0:
                        subprojectConcludedLicenses.append(lic._name)
        for lic in subproject_licenses:
            if not lic in subprojectConcludedLicenses:
                subprojectConcludedLicenses.append(lic)
        subprojectConcludedLicense = licenseStringsToExpression(subprojectConcludedLicenses, spdx_document.extracted_licensing_info, licensing)
    else:
        print(f"{prj._name}/{sp._name}: No SLM JSON file found - using project declared license as concluded license")
        subprojectConcludedLicense = subprojectDeclaredLicense
    
    describes.license_declared = subprojectDeclaredLicense
    describes.license_concluded = subprojectConcludedLicense
    describes.supplier = Actor(actor_type = ActorType.ORGANIZATION, name = 'Linux Foundation Project ' + prj._name)
    
    # Add a level under root for each of the repos
    repo_packages = {}
    for repo in sp._code_repos.keys():
        name = repo
        fileAnalyzed = False
        if sp._repotype == ProjectRepoType.GITHUB:
            locator = 'pkg:github/' + sp._github_org + '/' + repo + '@' + sp._code_repos[repo]
            purl = ExternalPackageRef(category=ExternalPackageRefCategory.PACKAGE_MANAGER, reference_type='purl', locator=locator)
            # https://github.com/lfscanning/scaffold/archive/7ef25b63f44cb3a68cd60a3c26532e13853917a2.zip
            download_location = 'https://github.com/' + sp._github_org + '/' + repo + '/archive/' + sp._code_repos[repo] + '.zip'
            external_references = [purl]
        elif sp._repotype == ProjectRepoType.GITHUB_SHARED:
            locator = 'pkg:github/' + prj._github_shared_org + '/' + repo + '@' + sp._code_repos[repo]
            purl = ExternalPackageRef(category=ExternalPackageRefCategory.PACKAGE_MANAGER, reference_type='purl', locator=locator)
            # https://github.com/lfscanning/scaffold/archive/7ef25b63f44cb3a68cd60a3c26532e13853917a2.zip
            download_location = 'https://github.com/' + prj._github_shared_org + '/' + repo + '/archive/' + sp._code_repos[repo] + '.zip'
            external_references = [purl]
        # else if sp._repotype == ProjectRepoType.GERRIT:
            # https://gerrit.onap.org/r/aai/aai-common
            # git clone "https://gerrit.onap.org/r/aai"
        else:
            download_location = SpdxNoAssertion()
            external_references = []
        version = sp._code_repos[repo]
        spdx_id = toSpdxRef(prj._name + "-" + sp._name + '-' + repo)
        supplier = Actor(actor_type = ActorType.ORGANIZATION, name = 'Linux Foundation Project ' + prj._name)
        source_info = 'The source this package was part of the LF Scanning configuration for the project ' + prj._name
        comment = 'This package was added to the Trivy analysis for the ' + name + ' by the Scaffold tool SBOM augmentation'
        repo_packages[repo] = Package(spdx_id = spdx_id, name = repo, download_location = download_location, version = version, supplier = supplier, \
                                        files_analyzed = False, source_info = source_info, license_concluded = subprojectConcludedLicense, \
                                        license_declared = subprojectDeclaredLicense, comment = comment, external_references = external_references, \
                                        primary_package_purpose = PackagePurpose.SOURCE)
        spdx_document.packages.append(repo_packages[repo])
        # add a contains relationship from the root to this package
        spdx_document.relationships.append(Relationship(spdx_element_id=describes.spdx_id, relationship_type=RelationshipType.CONTAINS, related_spdx_element_id=spdx_id))
    # move all the existing described relationships to their appropriate described fields
    for relationship in spdx_document.relationships:
        if relationship.spdx_element_id == describes.spdx_id:
            related_element = document_utils.get_element_from_spdx_id(spdx_document, relationship.related_spdx_element_id)
            repo = findRepoName(related_element, sp._repos)
            if repo:
                relationship.spdx_element_id = repo_packages[repo].spdx_id

    # Add version and supplier info for any Trivy generated packages representing metadata files
    for pkg in spdx_document.packages:
        m = re.match(r'([^/]+)/.+', pkg.name)
        if m and m.group(1) in repo_packages:
            repo_pkg = repo_packages[m.group(1)]
            if not hasattr(pkg, 'version') or not pkg.version:
                pkg.version = repo_pkg.version
            if not hasattr(pkg, 'supplier') or not pkg.supplier:
                pkg.supplier = repo_pkg.supplier
                
    # Fix up the creation info to add scaffold and Parlay as a tool and Linux Foundation as an organization
    spdx_document.creation_info.creators.append(Actor(actor_type = ActorType.ORGANIZATION, name = 'Linux Foundation'))
    spdx_document.creation_info.creators.append(Actor(actor_type = ActorType.TOOL, name = 'Scaffold'))
    spdx_document.creation_info.creators.append(Actor(actor_type = ActorType.TOOL, name = 'Parlay'))
    for spdx_element in spdx_document.packages:
        spdx_element.license_concluded = fix_license(spdx_element.license_concluded, spdx_document.extracted_licensing_info, licensing)
        if spdx_element.license_declared == SpdxNone() or spdx_element.license_declared == SpdxNoAssertion():
            spdx_element.license_declared = spdx_element.license_concluded
        else:
            spdx_element.license_declared = fix_license(spdx_element.license_declared, spdx_document.extracted_licensing_info, licensing)
        fix_download_location(spdx_element)
        fix_attribution_text(spdx_element, spdx_document.annotations, spdx_document.creation_info.created)
    # Change the NONES to NOASSERTION for licenses and download locations
    # Change any license IDs in expressions to LicenseRef's
    # Change attribution text to annotations
    for spdx_element in spdx_document.files:
        spdx_element.license_concluded = fix_license(spdx_element.license_concluded, spdx_document.extracted_licensing_info, licensing)
        if spdx_element.license_declared == SpdxNone() or spdx_element.license_declared == SpdxNoAssertion():
            spdx_element.license_declared = spdx_element.license_concluded
        else:
            spdx_element.license_declared = fix_license(spdx_element.license_declared, spdx_document.extracted_licensing_info, licensing)
        fix_download_location(spdx_element)
        fix_attribution_text(spdx_element, spdx_document.annotations, spdx_document.creation_info.created)
    for spdx_element in spdx_document.snippets:
        spdx_element.license_concluded = fix_license(spdx_element.license_concluded, spdx_document.extracted_licensing_info, licensing)
        if spdx_element.license_declared == SpdxNone() or spdx_element.license_declared == SpdxNoAssertion():
            spdx_element.license_declared = spdx_element.license_concluded
        else:
            spdx_element.license_declared = fix_license(spdx_element.license_declared, spdx_document.extracted_licensing_info, licensing)
        fix_download_location(spdx_element)
        fix_attribution_text(spdx_element, spdx_document.annotations, spdx_document.creation_info.created)
        
    
    
    print("Trivy document augmented")
    return True
    
def remove_dup_packages(spdx_document):
    # Removes duplicate packages from the SPDX document which will cause validation to fail
    new_pkgs = [] # Note: we don't use the remove method on the spdx_document.packages due to performance issues
    all_pkg_ids = set(())
    num_dups = 0
    for pkg in spdx_document.packages:
        if pkg.spdx_id in all_pkg_ids:
            num_dups = num_dups + 1
        else:
            new_pkgs.append(pkg)
            all_pkg_ids.add(pkg.spdx_id)
    if num_dups > 0:
        print(f'Removing {num_dups} duplicate packages')
        spdx_document.packages = new_pkgs

def fix_license(lic, extracted_licensing_info, licensing):
    if lic == SpdxNone():
        return SpdxNoAssertion()
    elif lic == SpdxNoAssertion():
        return lic
    else:
        unknown_keys = licensing.unknown_license_keys(lic)
        if not unknown_keys:
            return lic
        unparsed_lic = str(lic)
        for unknown_key in unknown_keys:
            # see if the unknown key is part of a WITH statement - we must replace these first
            # so that the second search for the pattern will just find the individual occurences
            withs = re.findall(f'([^ ]+) WITH ({re.escape(unknown_key)})', unparsed_lic)
            for w in withs:
                with_extracted_id = re.sub(r'[^0-9a-zA-Z\.\-]+', '-', w[0]) + '-LicenseRef-' + re.sub(r'[^0-9a-zA-Z\.\-\+]+', '-', w[1])
                if not with_extracted_id.startswith('LicenseRef-'):
                    with_extracted_id = 'LicenseRef-' + with_extracted_id
                with_id_found = False
                for existing in extracted_licensing_info:
                    if existing.license_id.lower() == with_extracted_id.lower():
                        with_id_found = True
                        with_extracted_id = existing.license_id # perserve the original case
                        break
                if not with_id_found:
                    extracted_licensing_info.append(ExtractedLicensingInfo(license_id = with_extracted_id, extracted_text = f'{w[0]} WITH {w[1]}', \
                                    comment = 'This license text represents a WITH statement found in licensing metadata - the actual text is not known'))
                unparsed_lic = re.sub(f'{re.escape(w[0])} WITH {re.escape(w[1])}', with_extracted_id, unparsed_lic)
            # Now we can handle the IDs not found in the WITH statements
            if unknown_key.startswith('LicenseRef-'):
                extracted_id = unknown_key
            else:
                extracted_id = 'LicenseRef-' + re.sub(r'[^0-9a-zA-Z\.\-]+', '-', unknown_key)
            extracted_id_found = False
            for existing in extracted_licensing_info:
                if existing.license_id.lower() == extracted_id.lower():
                    extracted_id_found = True
                    extracted_id = existing.license_id # perserve the original case
                    break
            if not extracted_id_found:
                extracted_licensing_info.append(ExtractedLicensingInfo(license_id = extracted_id, extracted_text = unknown_key, \
                                    comment = 'This license text represents a string found in licensing metadata - the actual text is not known'))
            unparsed_lic = re.sub(r'(?<!LicenseRef-)' + re.escape(unknown_key), extracted_id, unparsed_lic)
        return licensing.parse(unparsed_lic)
        
def fix_download_location(spdx_element):
    if spdx_element.download_location == SpdxNone():
        spdx_element.download_location = SpdxNoAssertion()
        
def fix_attribution_text(spdx_element, annotations, date):
    for attribution in spdx_element.attribution_texts:
        annotations.append(Annotation(spdx_id = spdx_element.spdx_id, annotation_type = AnnotationType.OTHER, \
                            annotator = Actor(actor_type = ActorType.TOOL, name='Trivy'), annotation_date = date, \
                            annotation_comment = attribution))
    spdx_element.attribution_texts = []
    
def toSpdxRef(identifier):
    return 'SPDXRef-' + re.sub(r'[^0-9a-zA-Z\.\-\+]+', '-', identifier)
    
def findRepoName(element, repos):
    if element == None:
        return None
    for repo in repos:
        if element.name.startswith(repo + "/"):
            return repo
        if hasattr(element, 'source_info') and hasattr(element.source_info, 'startswith') and element.source_info.startswith("package found in: "+repo+"/"):
            return repo
    return None

def licenseStringsToExpression(license_strings, extracted_licensing_info, licensing):
    if license_strings:
        licstr = _licenseStringToExpression(license_strings[0], extracted_licensing_info, licensing)
        for i in range(1, len(license_strings)-1):
            licstr = licstr + " AND " + _licenseStringToExpression(license_strings[i], extracted_licensing_info, licensing)
        return licensing.parse(licstr)
    else:
        return SpdxNoAssertion()
        
def _licenseStringToExpression(license_string, extracted_licensing_info, licensing):
    try:
        lic = licensing.parse(license_string)
        if ' ' in license_string:
            return '(' + str(fix_license(lic, extracted_licensing_info, licensing)) + ')'
        else:
            return str(fix_license(lic, extracted_licensing_info, licensing))
    except:
        extracted_id = re.sub(r'[^0-9a-zA-Z\.\-]+', '-', license_string)
        if not extracted_id.startswith("LicenseRef-"):
            extracted_id = "LicenseRef-" + extracted_id
        extracted_id_found = False
        for existing in extracted_licensing_info:
            if existing.license_id == extracted_id:
                extracted_id_found = True
                break
        if not extracted_id_found:
            extracted_licensing_info.append(ExtractedLicensingInfo(license_id = extracted_id, extracted_text = license_string, \
                                comment = 'This license text represents a string found in licensing metadata - the actual text is not known'))
        return extracted_id
            
