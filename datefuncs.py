# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime

# Parse a YYYY-MM string and return the year and month as ints.
def parseYM(s):
    try:
        dt = datetime.strptime(s, '%Y-%m')
        return dt.year, dt.month
    except ValueError:
        print(f'Error parsing year-month: {s} is not in YYYY-MM format')
        return 0, 0

# get preceding year-month given a year-month pair
def priorMonth(year, month):
    if month == 1:
        return year-1, 12
    return year, month-1

# get next year-month given a year-month pair
def nextMonth(year, month):
    if month == 12:
        return year+1, 1
    return year, month+1

