# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import requests

GITHUB_API_URL = "https://api.github.com"

def getOrgJSONData(org):
    url = f"{GITHUB_API_URL}/orgs/{org}/repos?per_page=100"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Error: Got invalid status code {r.status_code} from {url}")
        return None
    return r.json()

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
