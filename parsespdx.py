# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os

from datatypes import Status
from .slm.tvReader import TVReader
from .slm.tvParser import TVParser

MD5_EMPTY_FILE = "d41d8cd98f00b204e9800998ecf8427e"

def doParseSPDXForSubproject(cfg, prj, sp):
    # make sure we're at the right stage
    if sp._status != Status.GOTSPDX:
        print(f"{prj._name}/{sp._name}: status is {sp._status}, won't parse SPDX now")
        return False

    # find the SPDX file we want to parse
    spdxFolder = os.path.join(cfg._storepath, cfg._month, "spdx", prj._name)
    spdxFilename = f"{sp._name}-{sp._code_pulled}.spdx"
    spdxFilePath = os.path.join(spdxFolder, spdxFilename)

    tvList = []
    try:
        with open(spdxFilePath, 'r') as f:
            # read in the tag-value pairs line-by-line
            reader = TVReader()
            for line in f:
                reader.readNextLine(line)
            tvList = reader.finalize()
            # check for errors
            if reader.isError():
                print(f"{prj._name}/{sp._name}: error reading SPDX file: {reader.errorMessage}")

    except FileNotFoundError:
        print(f"{prj._name}/{sp._name}: SPDX tag-value file not found at {spdxFilePath}")
        return False

    # parse the tag-value pairs
    parser = TVParser()
    for tag, value in tvList:
        parser.parseNextPair(tag, value)
    fdList = parser.finalize()
    # check for errors
    if parser.isError():
        print(f"{prj._name}/{sp._name}: error parsing SPDX file: {parser.errorMessage}")
    # empty list means no file data found
    if fdList == []:
        print(f"{prj._name}/{sp._name}: error parsing SPDX file: no file data found")

    # apply adjustments
    applyAliases(cfg, prj, fdList)
    applyNoLicenseFoundFindings(cfg, prj, fdList)

    # reformulate into category/license/file structure, and/or error out
    # if any are missing
    cats = []
    for fd in fdList:


    # once we get here, the SPDX file has been parsed into JSON
    sp._status = Status.PARSEDSPDX

    # and when we return, the runner framework should update the project's
    # status to reflect the min of its subprojects
    return True

def applyAliases(cfg, prj, fdList):
    # build lookup of all configured aliases, with orig name => translated name
    aliases = {}
    for cat in prj._slm_category_configs:
        for lic in cat._license_configs:
            for a in lic._aliases:
                aliases[a] = lic._name

    # now, walk through fdList and apply aliases
    for fd in fdList:
        newLicense = aliases.get(fd.license, "")
        if newLicense != "":
            fd.license = newLicense

def applyNoLicenseFoundFindings(cfg, prj, fdList):
    # prepare extension search lists
    # split out those extensions ending in asterisks => anywhere in file path, not just at end
    # split out those extensions ending in equal sign => exact filename match
    anyList = []
    exactList = []
    extRevisedList = []
    for ext in prj._slm_extensions_skip:
        if ext.endswith("*"):
            anyList.append(str.lower(ext.rstrip("*")))
        elif ext.endswith("="):
            exactList.append(str.lower(ext.rstrip("=")))
        else:
            extRevisedList.append(str.lower(ext))

    for fd in fdList:
        if fd.license == "No license found":
            # check file extensions
            ext = os.path.splitext(fd.path)[1].lstrip(".")
            if str.lower(ext) in extRevisedList:
                fd.finding_extensions = "yes"
            # also check list of those with asterisks, for pattern anywhere in filename
            for pattern in anyList:
                if pattern in str.lower(fd.path):
                    fd.finding_extensions = "yes"
            # also check whether the filename is exactly the same as the "extension"
            for exactPattern in exactList:
                if exactPattern == str.lower(os.path.split(fd.path)[1]):
                    fd.finding_extensions = "yes"

            # also check third party dirs
            for directory in prj._slm_thirdparty_dirs:
                if directory in fd.path:
                    fd.finding_thirdparty = "yes"

            # also check empty files
            if fd.md5 == MD5_EMPTY_FILE:
                fd.finding_emptyfile = "yes"

def getCategoryForLicense(cfg, prj, lic):
    for cat in prj._slm_category_configs:
        if lic in cat._license_configs:
            return cat._name

    return None
