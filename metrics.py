# Copyright The Linux Foundation
# SPDX-License-Identifier: Apache-2.0

from datatypes import Status

def printMetrics(cfg):
    # collect counts of subprojects and repos
    counts_inproc = [0, 0]
    counts_analyzed = [0, 0]
    counts_uploaded = [0, 0]
    counts_delivered = [0, 0]

    for prj in cfg._projects.values():
        for sp in prj._subprojects.values():
            st = sp._status.value

            if st >= Status.START.value and st <= Status.RANAGENTS.value:
                counts_inproc[0] += 1
                counts_inproc[1] += len(sp._repos)

            elif st > Status.RANAGENTS.value and st <= Status.MADEDRAFTFINDINGS.value or st == Status.STOPPED.value:
                counts_analyzed[0] += 1
                counts_analyzed[1] += len(sp._repos)

            elif st > Status.MADEDRAFTFINDINGS.value and st <= Status.UPLOADEDREPORTS.value:
                counts_uploaded[0] += 1
                counts_uploaded[1] += len(sp._repos)

            elif st > Status.UPLOADEDREPORTS.value and st <= Status.DELIVERED.value:
                counts_delivered[0] += 1
                counts_delivered[1] += len(sp._repos)

            else:
                print(f"{prj._name}/{sp._name}: Invalid status for metrics: {sp._status}")

    # print totals
    print(f"Latest scan and clearing in process:")
    print(f"  - subprojects: {counts_inproc[0]}")
    print(f"  - repos: {counts_inproc[1]}")
    print(f"")
    print(f"Scan and analysis complete, preparing report:")
    print(f"  - subprojects: {counts_analyzed[0]}")
    print(f"  - repos: {counts_analyzed[1]}")
    print(f"")
    print(f"Reports uploaded, delivery to maintainers in process:")
    print(f"  - subprojects: {counts_uploaded[0]}")
    print(f"  - repos: {counts_uploaded[1]}")
    print(f"")
    print(f"Reports delivered:")
    print(f"  - subprojects: {counts_delivered[0]}")
    print(f"  - repos: {counts_delivered[1]}")
    print(f"")
