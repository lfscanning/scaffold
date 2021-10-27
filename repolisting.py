# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datatypes import ProjectRepoType, Status, Subproject
from github import getGithubRepoList
from gerrit import getGerritRepoDict, getGerritRepoList

# Runner for START in GitHub
def doRepoListingForSubproject(cfg, prj, sp):
    allrepos = getGithubRepoList(cfg._secrets._gitoauth[prj], sp._github_org)

    # first, figure out what repos need to be added
    for r in allrepos:
        if r not in sp._repos and r not in sp._github_repos_ignore and r not in sp._github_repos_pending:
            sp._github_repos_pending.append(r)
            print(f"{prj._name}/{sp._name}: new pending repo: {r}")

    # then, figure out what repos need to be removed
    repos_to_remove = []
    for r in sp._repos:
        if r not in allrepos:
            repos_to_remove.append(r)
    for r in repos_to_remove:
        sp._repos.remove(r)
        print(f"{prj._name}/{sp._name}: removed {r} from repos")

    repos_ignore_to_remove = []
    for r in sp._github_repos_ignore:
        if r not in allrepos:
            repos_ignore_to_remove.append(r)
    for r in repos_ignore_to_remove:
        sp._github_repos_ignore.remove(r)
        print(f"{prj._name}/{sp._name}: removed {r} from repos-ignore")

    # finally, throw a "fail" if any new repos are pending
    if len(sp._github_repos_pending) > 0:
        print(f"{prj._name}/{sp._name}: stopped, need to assign repos-pending")
        return False
    else:
        # success - advance state
        sp._status = Status.GOTLISTING
        return True

# Runner for START in GITHUB-SHARED
def doRepoListingForProject(cfg, prj):
    if prj._repotype == ProjectRepoType.GITHUB_SHARED:
        # collect all configured repos, and what subprojects they're in
        allcfgrepos = {}
        for sp_name, sp in prj._subprojects.items():
            for r in sp._repos:
                allcfgrepos[r] = sp_name

        # collect all real repos currently on GitHub
        allrealrepos = getGithubRepoList(cfg._secrets._gitoauth[prj], prj._github_shared_org)

        # first, figure out what repos need to be added
        for r in allrealrepos:
            config_sp = allcfgrepos.get(r, "")
            if config_sp == "" and r not in prj._github_shared_repos_ignore and r not in prj._github_shared_repos_pending:
                prj._github_shared_repos_pending.append(r)
                print(f"{prj._name}: new pending repo: {r}")

        # then, figure out what repos need to be removed
        for sp_name, sp in prj._subprojects.items():
            repos_to_remove = []
            for r in sp._repos:
                if r not in allrealrepos:
                    repos_to_remove.append(r)
            for r in repos_to_remove:
                sp._repos.remove(r)
                print(f"{prj._name}/{sp._name}: removed {r} from repos")

        repos_ignore_to_remove = []
        for r in prj._github_shared_repos_ignore:
            if r not in allrealrepos:
                repos_ignore_to_remove.append(r)
        for r in repos_ignore_to_remove:
            prj._github_shared_repos_ignore.remove(r)
            print(f"{prj._name}: removed {r} from repos-ignore")

        # finally, throw a "fail" if any new repos are pending
        if len(prj._github_shared_repos_pending) > 0:
            print(f"{prj._name}: stopped, need to assign repos-pending")
            return False
        else:
            # success - advance state
            prj._status = Status.GOTLISTING
            for _, sp in prj._subprojects.items():
                sp._status = Status.GOTLISTING
            return True

# Runner for START in GERRIT
def doRepoListingForGerritProject(cfg, prj):
    if prj._gerrit_subproject_config == "auto":
        return doRepoListingForGerritAutoProject(cfg, prj)
    elif prj._gerrit_subproject_config == "one":
        return doRepoListingForGerritOneProject(cfg, prj)
    elif prj._gerrit_subproject_config == "manual":
        return doRepoListingForGerritManualProject(cfg, prj)
    else:
        print(f"{prj._name}: invalid subproject-config value: {prj._gerrit_subproject_config}")
        return False

# Runner for START in GERRIT where subproject-config is auto
def doRepoListingForGerritAutoProject(cfg, prj):
    # get the sorted dictionary of repos by top-level grouping, if any
    rd = getGerritRepoDict(prj._gerrit_apiurl)

    # now, figure out which repos to assign to which subprojects
    # and create subprojects where needed
    groupings_seen = []
    for grouping, repos in rd.items():
        if grouping not in prj._gerrit_repos_ignore:
            groupings_seen.append(grouping)
            sp = prj._subprojects.get(grouping, None)
            if sp == None:
                sp = Subproject()
                sp._name = grouping
                sp._repotype = ProjectRepoType.GERRIT
                sp._status = Status.START
                prj._subprojects[grouping] = sp
            # now, figure out which new repos in this grouping we need to add
            repos_seen = []
            repos_to_remove = []
            for repo in repos:
                repos_seen.append(repo)
                if repo not in sp._repos:
                    sp._repos.append(repo)
                    print(f"{prj._name}/{sp._name}: added {repo} to repos")
            # and which old repos we need to remove
            for repo in sp._repos:
                if repo not in repos_seen:
                    repos_to_remove.append(repo)
            for repo in repos_to_remove:
                sp._repos.remove(repo)
                print(f"{prj._name}/{sp._name}: removed {repo} from repos")

    # now, finally, figure out which old subprojects we need to remove
    subprojects_to_remove = []
    for sp_name in prj._subprojects.keys():
        if sp_name not in groupings_seen:
            subprojects_to_remove.append(sp_name)
    for sp_name in subprojects_to_remove:
        del prj._subprojects[sp_name]
        print(f"{prj._name}: removed subproject {sp_name}")

    # finally, update status for remaining subprojects
    for sp in prj._subprojects.values():
        sp._status = Status.GOTLISTING
    prj._status = Status.GOTLISTING

    return True

# Runner for START in GERRIT where subproject-config is one
def doRepoListingForGerritOneProject(cfg, prj):
    # check that there's only one subproject and that it has the right name
    if len(prj._subprojects) > 1:
        print(f"{prj._name}: subproject-config value is 'one' but more than one subproject exists")
        return False
    if len(prj._subprojects) == 1:
        # should only be one but we'll iterate to get the first one
        for sp_name in prj._subprojects.keys():
            if sp_name != prj._name:
                print(f"{prj._name}: subproject-config value is 'one' but subproject has different name from project: {sp_name}")
                return False
    # or if no subprojects, create new subproject for this gerrit org overall
    if len(prj._subprojects) == 0:
        sp = Subproject()
        sp._name = prj._name
        sp._repotype = ProjectRepoType.GERRIT
        sp._status = Status.START
        prj._subprojects[prj._name] = sp

    # get the sorted dictionary of repos by top-level grouping, if any
    rd = getGerritRepoDict(prj._gerrit_apiurl)

    # now, figure out which repos to add
    repos_seen = []
    sp = prj._subprojects.get(prj._name, None)
    if sp == None:
        print(f"{prj._name}: unable to get subproject {prj._name}")
        return False
    for grouping, repos in rd.items():
        if grouping not in prj._gerrit_repos_ignore:
            for repo in repos:
                repos_seen.append(repo)
                if repo not in sp._repos:
                    sp._repos.append(repo)
                    print(f"{prj._name}/{sp._name}: added {repo} to repos")
    # and which ones to remove
    repos_to_remove = []
    for repo in sp._repos:
        if repo not in repos_seen:
            repos_to_remove.append(repo)
    for repo in repos_to_remove:
        sp._repos.remove(repo)
        print(f"{prj._name}/{sp._name}: removed {repo} from repos")

    # finally, update status for remaining subprojects
    sp._status = Status.GOTLISTING
    prj._status = Status.GOTLISTING

    return True

# Runner for START in GERRIT where subproject-config is manual
def doRepoListingForGerritManualProject(cfg, prj):
    # collect all configured repos, and what subprojects they're in
    allcfgrepos = {}
    for sp_name, sp in prj._subprojects.items():
        for r in sp._repos:
            allcfgrepos[r] = sp_name

    # collect all real repos currently on Gerrit
    allrealrepos = getGerritRepoList(prj._gerrit_apiurl)

    # first, figure out what repos need to be added
    for r in allrealrepos:
        config_sp = allcfgrepos.get(r, "")
        if config_sp == "" and r not in prj._gerrit_repos_ignore and r not in prj._gerrit_repos_pending:
            prj._gerrit_repos_pending.append(r)
            print(f"{prj._name}: new pending repo: {r}")

    # then, figure out what repos need to be removed
    for sp_name, sp in prj._subprojects.items():
        repos_to_remove = []
        for r in sp._repos:
            if r not in allrealrepos:
                repos_to_remove.append(r)
        for r in repos_to_remove:
            sp._repos.remove(r)
            print(f"{prj._name}/{sp._name}: removed {r} from repos")

    repos_ignore_to_remove = []
    for r in prj._gerrit_repos_ignore:
        if r not in allrealrepos:
            repos_ignore_to_remove.append(r)
    for r in repos_ignore_to_remove:
        prj._gerrit_repos_ignore.remove(r)
        print(f"{prj._name}: removed {r} from repos-ignore")

    # finally, throw a "fail" if any new repos are pending
    if len(prj._gerrit_repos_pending) > 0:
        print(f"{prj._name}: stopped, need to assign repos-pending")
        return False
    else:
        # success - advance state
        prj._status = Status.GOTLISTING
        for _, sp in prj._subprojects.items():
            sp._status = Status.GOTLISTING
        return True
