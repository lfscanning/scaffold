# Utility class to support merging / fixing up SPDX documents

from spdx_tools.spdx.model.document import Document
from spdx_tools.spdx.parser.error import SPDXParsingError
from spdx_tools.spdx.parser.parse_anything import parse_file
from spdx_tools.spdx.writer.write_anything import write_file

'''
Parses an SPDX file with a supported file extension
Raises SPDXParsingError on parsing errors
'''
def parseFile(file):
    return parse_file(file)

'''
wrties an SPDX document to a file in the format dictated by the file extension
'''
def writeFile(spdxDocument, file):
    write_file(spdxDocument, file, validate=False)
    print("SPDX sucessfully written")
    
def fixTrivyDocument(spdxDocument):
    # TODO: Implement
    print("Fixing trivy document")
    
