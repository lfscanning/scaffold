# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os
from collections import OrderedDict
import openpyxl


##### SPDX / Trivy xlsx reporting functions

def makeXlsx(spdxDocument):
    wb = openpyxl.Workbook()
    _generateDependenciesSheet(wb, spdxDocument)

    # and return the workbook
    return wb

def saveXlsx(wb, path):
    try:
        wb.save(path)
        return True
    except PermissionError:
        return False

##### Helper functions for xlsx reporting

def _generateDependenciesSheet(wb, spdxDocument):
    # use the first (existing) sheet as the dependencies sheet
    ws = wb.active
    ws.title = "Dependencies"

    # adjust column widths
    ws.column_dimensions['A'].width = 50
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 80

    # create font styles
    fontBold = openpyxl.styles.Font(size=16, bold=True)
    fontNormal = openpyxl.styles.Font(size=14)
    alignNormal = openpyxl.styles.Alignment(wrap_text=True)

    # create headers
    ws['A1'] = "Package name"
    ws['A1'].font = fontBold
    ws['B1'] = "License"
    ws['B1'].font = fontBold
    ws['C1'] = "Version"
    ws['C1'].font = fontBold
    ws['D1'] = "Package URL"
    ws['D1'].font = fontBold
    # Create dependncy rows
    # TODO: Implement
    