# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import requests

GITHUB_API_URL = "https://api.github.com"

def getOrgJSONData(org):
    url = f"{GITHUB_API_URL}/orgs/{org}/repos?per_page=100"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()

    # if r is 404, then this might be a user, not an org -- try that instead
    if r.status_code == 404:
        user_url = f"{GITHUB_API_URL}/users/{org}/repos?per_page=100"
        r2 = requests.get(user_url)
        if r2.status_code == 200:
            return r2.json()
        print(f"Error: Got invalid status code {r.status_code} from {url}, and {r2.status_code} from {user_url}")
        return None

    # else just fail
    print(f"Error: Got invalid status code {r.status_code} from {url}")
    return None

def parseOrgJSONData(rj):
    repos = []
    for repo in rj:
        repo_name = repo.get("name", None)
        #repo_url = repo.get("html_url", None)
        repos.append(repo_name)
    repos.sort()
    return repos

def getGithubRepoList(org):
    rj = getOrgJSONData(org)
    return parseOrgJSONData(rj)
