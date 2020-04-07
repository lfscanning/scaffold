# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

class TVReader:
    # Possible reader state values
    # ready to read new tag/value pair
    STATE_READY = 1
    # in the middle of reading a multi-line <text> value
    STATE_MIDTEXT = 2
    # encountered an error from which we can't recover
    STATE_ERROR = 99

    def __init__(self):
        super(TVReader, self).__init__()
        self._reset()

    ##### Main tag-value reading functions
    ##### External usage shouldn't require calling anything except these

    def readNextLine(self, line):
        self.currentLine += 1

        if self.state == self.STATE_READY:
            self._readNextLineFromReady(line)
        elif self.state == self.STATE_MIDTEXT:
            self._readNextLineFromMidtext(line)
        elif self.state == self.STATE_ERROR:
            return
        else:
            # invalid state, set to error state
            self.errorMessage = f"Tag-value reader in invalid state at line {self.currentLine}: {self.state}"
            self.state = self.STATE_ERROR

    def finalize(self):
        if self.state == self.STATE_ERROR:
            # error message should already be set
            return None
        elif self.state == self.STATE_MIDTEXT:
            self.state = self.STATE_ERROR
            self.errorMessage = "No closing </text> tag found"
            return None
        else:
            return self.tvList

    def isError(self):
        return self.state == self.STATE_ERROR

    ##### Tag-value reading main helper functions

    def _readNextLineFromReady(self, line):
        # strip whitespace from beginning of line
        line = line.lstrip()

        # ignore empty lines
        if line == '':
            return

        # ignore comment lines
        if line.startswith("#"):
            return

        # scan for a colon to split tag and value
        colonLoc = line.find(':')

        # if no colon found, this is an error
        if colonLoc == -1:
            self.errorMessage = f"No colon found at line {self.currentLine}: '{line.strip()}'"
            self.state = self.STATE_ERROR
            return

        # preceding string becomes tag
        self.currentTag = line[0:colonLoc].strip()

        # subsequent string becomes value, or start of value if multi-line <text>
        lineRemainder = line[colonLoc+1:]
        startTextLoc = lineRemainder.find("<text>")
        if startTextLoc == -1:
            # no <text>, so just do this value as a single line
            self.currentValue = lineRemainder.strip()
            # we'll fall through to add this to the tag-value list below
        else:
            # did find <text>, so determine whether to start multi-line reading
            # exclude the <text> tag itself
            self.currentValue = lineRemainder[startTextLoc+6:]
            # is there a closing </text>?
            endTagLoc = self.currentValue.find("</text>")
            if endTagLoc == -1:
                # no closing </text>, so go to multi-line reading and add a newline
                self.state = self.STATE_MIDTEXT
                self.currentValue += '\n'
                return
            else:
                # found a closing </text>, so just one line
                # extract the value prior to </text>
                self.currentValue = self.currentValue[:endTagLoc]

        # if we got here, the value was a single line (maybe with opening and
        # closing <text>)
        # add to tag-value list as a tuple
        t = (self.currentTag, self.currentValue)
        self.tvList.append(t)
        # and reset current tag and current value
        self._resetCurrentTagValue()

    def _readNextLineFromMidtext(self, line):
        endTagLoc = line.find("</text>")
        if endTagLoc == -1:
            # no closing </text>, so continue multiline
            self.currentValue += line + '\n'
        else:
            # found closing </text> so end multiline and record this tag-value
            self.currentValue += line[0:endTagLoc]
            t = (self.currentTag, self.currentValue)
            self.tvList.append(t)
            # reset current tag and current value, and go back to ready state
            self._resetCurrentTagValue()
            self.state = self.STATE_READY

    ##### Other helper functions

    def _reset(self):
        self.state = self.STATE_READY
        self.tvList = []
        self.currentLine = 0
        self.currentTag = ""
        self.currentValue = ""
        self.errorMessage = ""

    def _resetCurrentTagValue(self):
        self.currentTag = ""
        self.currentValue = ""
