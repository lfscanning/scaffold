# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

'''
Created on Nov 2, 2021

@author: Gary O'Neall

Utility class to support common function in Scaffold
'''

import shutil
import time

def retry_rmtree(path, max_retries=5):
    """Calls shutil.rmtree and, if fails, retries up to the maximum number of retries
    """
    sleepTime = 1
    for count in range(max_retries):
        try:
            shutil.rmtree(path)
            return  # Success!
        except OSError:
            print("Error removing directory "+path)
            if count < max_retries:
                print("Retrying...")
            time.sleep(sleepTime)
            sleepTime = sleepTime * 2
    # if we got here, we exceeded the 
    # Try one more time and let the exception be thrown if unsuccessful
    shutil.rmtree(path)
