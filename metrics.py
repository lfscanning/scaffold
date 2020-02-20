# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

import os

from datatypes import Metrics, Priority, Status
from instancesfile import loadInstances
from metricsfile import loadMetrics

def printMetrics(metricsFilename):
    # collect counts of subprojects, repos and files
    counts_inproc = [0, 0, 0]
    counts_analyzed = [0, 0, 0]
    counts_uploaded = [0, 0, 0]
    counts_delivered = [0, 0, 0]

    # also collect counts of instances and corresponding files
    # order: veryhigh, high, medium, low
    counts_instances = [0, 0, 0, 0]
    counts_instances_files = [0, 0, 0, 0]

    all_metrics = loadMetrics(metricsFilename)
    if all_metrics == {}:
        print(f"Got empty metrics; bailing")
        return

    for prj in all_metrics.values():
        for sp_metrics in prj.values():
            if sp_metrics._state_category == "inproc":
                counts_inproc[0] += 1
                counts_inproc[1] += sp_metrics._num_repos
                counts_inproc[2] += sp_metrics._unpacked_files

            elif sp_metrics._state_category == "analyzed":
                counts_analyzed[0] += 1
                counts_analyzed[1] += sp_metrics._num_repos
                counts_analyzed[2] += sp_metrics._unpacked_files

            elif sp_metrics._state_category == "uploaded":
                counts_uploaded[0] += 1
                counts_uploaded[1] += sp_metrics._num_repos
                counts_uploaded[2] += sp_metrics._unpacked_files

            elif sp_metrics._state_category == "delivered":
                counts_delivered[0] += 1
                counts_delivered[1] += sp_metrics._num_repos
                counts_delivered[2] += sp_metrics._unpacked_files

            else:
                if sp_metrics._state_category != "stopped":
                    print(f"{sp_metrics._prj_name}/{sp_metrics._sp_name}: Invalid status category for metrics: {sp_metrics._state_category}")

            # also get instance and file counts by priority
            counts_instances[0] += sp_metrics._instances_veryhigh
            counts_instances[1] += sp_metrics._instances_high
            counts_instances[2] += sp_metrics._instances_medium
            counts_instances[3] += sp_metrics._instances_low
            counts_instances_files[0] += sp_metrics._files_veryhigh
            counts_instances_files[1] += sp_metrics._files_high
            counts_instances_files[2] += sp_metrics._files_medium
            counts_instances_files[3] += sp_metrics._files_low

    # print totals
    print(f"Latest scan and clearing in process:")
    print(f"  - subprojects: {counts_inproc[0]}")
    print(f"  - repos: {counts_inproc[1]}")
    print(f"  - files: {counts_inproc[2]}")
    print(f"")
    print(f"Scan and analysis complete, preparing report:")
    print(f"  - subprojects: {counts_analyzed[0]}")
    print(f"  - repos: {counts_analyzed[1]}")
    print(f"  - files: {counts_analyzed[2]}")
    print(f"")
    print(f"Reports uploaded, delivery to maintainers in process:")
    print(f"  - subprojects: {counts_uploaded[0]}")
    print(f"  - repos: {counts_uploaded[1]}")
    print(f"  - files: {counts_uploaded[2]}")
    print(f"")
    print(f"Reports delivered:")
    print(f"  - subprojects: {counts_delivered[0]}")
    print(f"  - repos: {counts_delivered[1]}")
    print(f"  - files: {counts_delivered[2]}")
    print(f"")
    print(f"")
    print(f"Findings by priority:")
    print(f"  Very High: {counts_instances[0]} instances ({counts_instances_files[0]} files)")
    print(f"  High:      {counts_instances[1]} instances ({counts_instances_files[1]} files)")
    print(f"  Medium:    {counts_instances[2]} instances ({counts_instances_files[2]} files)")
    print(f"  Low:       {counts_instances[3]} instances ({counts_instances_files[3]} files)")
    print(f"")

def getMetrics(cfg, fdServer):
    all_metrics = {}

    for prj in cfg._projects.values():
        prj_metrics = {}
        for sp in prj._subprojects.values():
            print(f"{prj._name}/{sp._name}: getting metrics")
            sp_metrics = Metrics()
            sp_metrics._prj_name = prj._name
            sp_metrics._sp_name = sp._name

            # determine state category
            st = sp._status.value
            if st >= Status.START.value and st <= Status.RANAGENTS.value:
                sp_metrics._state_category = "inproc"
            elif st > Status.RANAGENTS.value and st <= Status.MADEDRAFTFINDINGS.value:
                sp_metrics._state_category = "analyzed"
            elif st > Status.MADEDRAFTFINDINGS.value and st <= Status.FILEDTICKETS.value:
                sp_metrics._state_category = "uploaded"
            elif st > Status.FILEDTICKETS.value and st <= Status.DELIVERED.value:
                sp_metrics._state_category = "delivered"
            elif st == Status.STOPPED.value:
                sp_metrics._state_category = "stopped"
            else:
                sp_metrics._state_category = "unknown"

            # determine number of unpacked files, if it's been uploaded to Fossology
            if st >= Status.UPLOADEDCODE.value and st != Status.STOPPED.value:
                sp_metrics._unpacked_files = getNumberUnpackedFiles(cfg, fdServer, prj, sp)
            else:
                sp_metrics._unpacked_files = 0

            # determine number of repos regardless of stage (if not scanned yet,
            # we'll just rely on last month's count, or else empty set)
            sp_metrics._num_repos = len(sp._repos)

            # determine instances, if we've at least made draft findings
            if st >= Status.MADEDRAFTFINDINGS.value and st != Status.STOPPED.value:
                instSet = getInstanceSet(cfg, prj, sp)
                if instSet is None:
                    print(f"{prj._name}/{sp._name}: unable to load instances file")
                else:
                    for inst in instSet._flagged:
                        # currently can't use inst._priority because it has to
                        # be retrieved from the finding data
                        priority = getInstancePriority(cfg, prj, inst._finding_id)
                        if priority == Priority.VERYHIGH:
                            sp_metrics._instances_veryhigh += 1
                            sp_metrics._files_veryhigh += len(inst._files)
                        elif priority == Priority.HIGH:
                            sp_metrics._instances_high += 1
                            sp_metrics._files_high += len(inst._files)
                        elif priority == Priority.MEDIUM:
                            sp_metrics._instances_medium += 1
                            sp_metrics._files_medium += len(inst._files)
                        elif priority == Priority.LOW:
                            sp_metrics._instances_low += 1
                            sp_metrics._files_low += len(inst._files)
                        else:
                            print(f"{prj._name}/{sp._name}: invalid priority {priority} for instance with id {inst._finding_id}")

            prj_metrics[sp._name] = sp_metrics
        all_metrics[prj._name] = prj_metrics
    return all_metrics

def getNumberUnpackedFiles(cfg, fdServer, prj, sp):
    # first, get the folder and then upload ID for this sp
    uploadName = os.path.basename(sp._code_path)
    uploadFolder = f"{prj._name}-{cfg._month}"
    folderNum = fdServer.GetFolderNum(uploadFolder)
    if folderNum is None or folderNum == -1:
        print(f"{prj._name}/{sp._name}: could not retrieve folder number for folder {uploadFolder}")
        return 0
    uploadNum = fdServer.GetUploadNum(folderNum, uploadName)
    if uploadNum is None or uploadNum == -1:
        print(f"{prj._name}/{sp._name}: could not retrieve upload number for upload {uploadName} in folder {uploadFolder} ({folderNum})")
        return 0

    # also need the top tree item number
    u = fdServer._getUploadData(folderNum, uploadName, False)
    if u is None:
        print(f"{prj._name}/{sp._name}: could not retrieve upload data for upload {uploadName}")
        return 0

    # now, retrieve and extract the relevant stats
    stats = fdServer.GetUploadStatistics(uploadNum, u.topTreeItemId)
    if stats == []:
        print(f"{prj._name}/{sp._name}: could not retrieve stats for upload {uploadName}")
        return 0

    unpacked_files = stats.get("Files", -1)
    if unpacked_files == -1:
        print(f"{prj._name}/{sp._name}: file count not found in stats for upload {uploadName}")
        return 0

    return unpacked_files

def getInstanceSet(cfg, prj, sp):
    # calculate paths; report folder would have been created in doCreateReport stage
    reportFolder = os.path.join(cfg._storepath, cfg._month, "report", prj._name)
    instancesJsonFilename = f"{sp._name}-instances-{sp._code_pulled}.json"
    instancesJsonPath = os.path.join(reportFolder, instancesJsonFilename)
    return loadInstances(instancesJsonPath)

def getInstancePriority(cfg, prj, finding_id):
    for finding in prj._findings:
        if finding._id == finding_id:
            return finding._priority
