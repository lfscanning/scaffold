# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

from collections import defaultdict
import json

import requests

def getRepoJSONData(apiurl):
    url = f"{apiurl}/projects/"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Error: Got invalid status code {r.status_code} from {url}")
        return None
    # skip first few chars, which are added to avoid JSON poisoning problems?
    return json.loads(r.text[5:])

def parseRepoJSONData(rj):
    repos = { 'active': [], 'locked': [] }
    for repo_name, data in rj.items():
        state = data.get("state", None)
        if state == 'ACTIVE':
            repos['active'].append(repo_name)
        elif state == 'READ_ONLY':
            repos['locked'].append(repo_name)
    repos['active'].sort()
    repos['locked'].sort()
    return repos

def splitReposToDict(repos):
    repoDict = defaultdict(list)
    for repo in repos:
        prefix = repo.split("/")[0]
        repoDict[prefix].append(repo)
    return repoDict

def getGerritRepoDict(apiurl):
    rj = getRepoJSONData(apiurl)
    repos = parseRepoJSONData(rj)
    repodict = splitReposToDict(repos['active'])
    return dict(repodict)

def getGerritRepoList(apiurl):
    rj = getRepoJSONData(apiurl)
    repos = parseRepoJSONData(rj)
    return repos['active']
