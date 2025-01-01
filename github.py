# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import requests

GITHUB_API_URL = "https://api.github.com"

def getOrgJSONData(gh_oauth_token, org, page):
    url = f"{GITHUB_API_URL}/orgs/{org}/repos?page={page}&per_page=100"
    r = requests.get(url, headers={"Authorization": f"token {gh_oauth_token}"})
    if r.status_code == 200:
        return r.json()

    # if r is 404, then this might be a user, not an org -- try that instead
    if r.status_code == 404:
        user_url = f"{GITHUB_API_URL}/users/{org}/repos?page={page}&per_page=100"
        r2 = requests.get(user_url, headers={"Authorization": f"token {gh_oauth_token}"})
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

def getGithubRepoList(gh_oauth_token, org):
    repos = []
    stillSomeRepos = True
    page = 1
    while stillSomeRepos:
        rj = getOrgJSONData(gh_oauth_token, org, page)
        gotRepos = parseOrgJSONData(rj)
        if len(gotRepos) <= 0:
            stillSomeRepos = False
            break
        else:
            for r in gotRepos:
                repos.append(r)
            page += 1

    return repos
