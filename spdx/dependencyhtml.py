# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from jinja2 import Template
import os

def makeHtml(spdxDocument, prj, sp):
    # load template
    templatePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "templates", "dependencies.html")
    with open(templatePath, "r") as tmpl_f:
        tmplstr = tmpl_f.read()
    dependencies = _get_dependencies(spdxDocument)
    if sp._github_org:
        orgLink = f'https://github.com/{sp._github_org}'
    else:
        orgLink = None
    context = {
        "prjName": prj._name,
        "spName": sp._name,
        "orgLink": orgLink,
        "codeDate": sp._code_pulled,
        "dependencies_headers": [
            "Package name",
            "License",
            "Version",
            "Package URL",
            "Dependency Relationship",
        ],
        "dependencies": dependencies,
        "dependencies_count": len(dependencies),
    }
    tmpl = Template(tmplstr)
    return tmpl.render(context)

def _get_dependencies(spdxDocument):
    dependencies = []
    # Collect all the package SPDX IDs
    unrecordedPackages = {}
    pkgRelationships = {}
    for pkg in spdxDocument.packages:
        unrecordedPackages[pkg.spdx_id] = pkg
        pkgRelationships[pkg.spdx_id] = []
    docRelationships = []
    for relationship in spdxDocument.relationships:
        if relationship.spdx_element_id == spdxDocument.creation_info.spdx_id:
            docRelationships.append(relationship)
        elif relationship.spdx_element_id in unrecordedPackages:
            pkgRelationships[relationship.spdx_element_id].append(relationship)
    for docRelationship in docRelationships:
        # start at the top so we sort in a somewhat natural hierarchy
        if docRelationship.related_spdx_element_id in unrecordedPackages:
            pkg = unrecordedPackages[docRelationship.related_spdx_element_id]

            dependencies.append(_get_dependency_context(pkg, "SPDXRef-DOCUMENT "+docRelationship.relationship_type.name))
            del unrecordedPackages[docRelationship.related_spdx_element_id]
            _addrelationships(dependencies, pkg, unrecordedPackages, pkgRelationships)
    for pkg in unrecordedPackages.values():
        dependencies.append(_get_dependency_context(pkg, "UNKNOWN - package in the document but not referenced in a relationship"))
    return dependencies

def _get_dependency_context(pkg, relationship_type):
    name = pkg.name if pkg.name else ""
    version = pkg.version if pkg.version else ""
    if hasattr(pkg, 'license_concluded') and not pkg.license_concluded is None:
        concludedLicense = str(pkg.license_concluded)
    else:
        concludedLicense = ""
    purl = ""
    for externalRef in pkg.external_references:
        if externalRef.reference_type == "purl":
            purl = externalRef.locator
    return {
        "package_name": name,
        "license": concludedLicense,
        "version": version,
        "package_url": purl,
        "dependency_relationship": relationship_type
    }

def _addrelationships(dependencies, pkg, unrecordedPackages, pkgRelationships):
    for relationship in pkgRelationships[pkg.spdx_id]:
        if relationship.related_spdx_element_id in unrecordedPackages:
            relatedPkg = unrecordedPackages[relationship.related_spdx_element_id]
            pkgName = pkg.name if pkg.name else "UNKNOWN"
            dependencies.append(_get_dependency_context(relatedPkg, pkgName + " " + relationship.relationship_type.name))
            del unrecordedPackages[relationship.related_spdx_element_id]
            _addrelationships(dependencies, relatedPkg, unrecordedPackages, pkgRelationships)