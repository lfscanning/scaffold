# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datatypes import ProjectRepoType, Status
from github import getRepoList

def doNextThing(cfg):
    for prj in cfg._projects.values():
        retval = True
        while retval:
            retval = doNextThingForProject(cfg, prj)

# Tries to do the next thing for this project. Returns True if
# accomplished something (meaning that we could call this again
# and possibly do the next-next thing), or False if accomplished
# nothing (meaning that we probably need to intervene).
def doNextThingForProject(cfg, prj):
    # if GitHub project, go to subprojects
    if prj._repotype == ProjectRepoType.GITHUB:
        did_something = False
        for sp in prj._subprojects.values():
            retval = True
            while retval:
                retval = doNextThingForSubproject(cfg, prj, sp)
                if retval:
                    did_something = True
        return did_something

    else:
        # or if Gerrit project, do everything here
        status = prj._status
        if status == Status.START:
            # get repo listing and see if we're good
            # FIXME figure out handling this for Gerrit
            #return doRepoListingForProject(prj)
            return False

        else:
            print(f"Invalid status for {prj._name}: status")
            return False

# Tries to do the next thing for this subproject. Returns True if
# accomplished something (meaning that we could call this again
# and possibly do the next-next thing), or False if accomplished
# nothing (meaning that we probably need to intervene).
def doNextThingForSubproject(cfg, prj, sp):
    status = sp._status
    if status == Status.START:
        # get repo listing and see if we're good
        return doRepoListingForSubproject(cfg, prj, sp)

    else:
        print(f"Invalid status for {prj._name}: status")
        return False


# Runner for START in GitHub
def doRepoListingForSubproject(cfg, prj, sp):
    allrepos = getRepoList(sp._github_org)

    # first, figure out what repos need to be added
    for r in allrepos:
        if r not in sp._repos and r not in sp._github_repos_ignore and r not in sp._github_repos_pending:
            sp._github_repos_pending.append(r)
            print(f"{prj}/{sp}: new pending repo: {r}")

    # then, figure out what repos need to be removed
    repos_to_remove = []
    for r in sp._repos:
        if r not in allrepos:
            repos_to_remove.append(r)
    for r in repos_to_remove:
        sp._repos.remove(r)
        print(f"{prj}/{sp}: removed {r} from repos")

    repos_ignore_to_remove = []
    for r in sp._github_repos_ignore:
        if r not in allrepos:
            repos_ignore_to_remove.append(r)
    for r in repos_ignore_to_remove:
        sp._github_repos_ignore.remove(r)
        print(f"{prj}/{sp}: removed {r} from repos-ignore")

    # finally, throw a "fail" if any new repos are pending
    if len(sp._github_repos_pending) > 0:
        print(f"{prj}/{sp}: stopped, need to assign repos-pending")
        return False
    else:
        # success - advance state
        sp._status = Status.GOTLISTING
        return True
