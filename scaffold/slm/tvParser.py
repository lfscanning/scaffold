# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

class ParsedFileData:
    def __init__(self):
        super(ParsedFileData, self).__init__()
        self.path = ""
        self.license = ""
        self.md5 = ""
        self.sha1 = ""
        self.sha256 = ""
        # findings will get filled in by parsespdx.py
        self.finding_extensions = ""
        self.finding_thirdparty = ""
        self.finding_emptyfile = ""

class TVParser:
    # Possible parser state values
    # ready to read first file-related tag/value pair
    STATE_READY = 1
    # in the middle of reading a file-related tag/value pair
    STATE_MIDFILE = 2
    # encountered an error from which we can't recover
    STATE_ERROR = 99

    def __init__(self):
        super(TVParser, self).__init__()
        self._reset()

    ##### Main tag-value parsing functions
    ##### External usage shouldn't require calling anything except these

    def parseNextPair(self, tag, value):
        if self.state == self.STATE_READY:
            self._parseNextPairFromReady(tag, value)
        elif self.state == self.STATE_MIDFILE:
            self._parseNextPairFromMidfile(tag, value)
        elif self.state == self.STATE_ERROR:
            return
        else:
            # invalid state, set to error state
            self.errorMessage = f"Tag-value parser in invalid state for pair ('{tag}', '{value}'): {self.state}"
            self.state = self.STATE_ERROR

    def finalize(self):
        # if error, don't return the list
        if self.state == self.STATE_ERROR:
            return None

        if self.fdList == [] and self.currentFileData is None:
            return []

        # record current file data record
        self.fdList.append(self.currentFileData)
        # clean up
        self.currentFileData = None
        # and return file data list
        return self.fdList

    def isError(self):
        return self.state == self.STATE_ERROR

    ##### Tag-value parsing main helper functions

    def _parseNextPairFromReady(self, tag, value):
        if tag == "FileName":
            self.currentFileData = ParsedFileData()
            self.currentFileData.path = value
            self.state = self.STATE_MIDFILE

    def _parseNextPairFromMidfile(self, tag, value):
        if tag == "LicenseConcluded":
            self.currentFileData.license = value
        elif tag == "FileChecksum":
            self._parseFileChecksum(value)
        elif tag == "FileName":
            # record current file data record
            self.fdList.append(self.currentFileData)
            # and start a new one
            self.currentFileData = ParsedFileData()
            self.currentFileData.path = value

    def _parseFileChecksum(self, value):
        sp = value.split(":")
        if len(sp) != 2:
            self.errorMessage = f"Invalid FileChecksum format: '{value}' found for file {self.currentFileData.path}"
            self.state = self.STATE_ERROR
            return
        checksumType = sp[0]
        checksum = sp[1].strip()
        if checksumType == "SHA1":
            self.currentFileData.sha1 = checksum
        elif checksumType == "MD5":
            self.currentFileData.md5 = checksum
        elif checksumType == "SHA256":
            self.currentFileData.sha256 = checksum
        else:
            self.errorMessage = f"Unknown FileChecksum type: '{checksumType}' found for file {self.currentFileData.path}"
            self.state = self.STATE_ERROR

    ##### Other helper functions

    def _reset(self):
        self.state = self.STATE_READY
        self.fdList = []
        self.currentFileData = None
        self.errorMessage = ""
