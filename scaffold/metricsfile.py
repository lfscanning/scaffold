# SPDX-FileCopyrightText: Copyright The Linux Foundation
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import json

from scaffold.datatypes import Metrics

def loadMetrics(metricsFilename):
    metrics = {}

    try:
        with open(metricsFilename, 'r') as f:
            js = json.load(f)

            # expecting dict of prj name to sub-dict
            for prj_name, prj_dict in js.items():
                prj_metrics = {}
                # expecting prj_dict to be dict of sp name to metrics dict
                for sp_name, sp_metrics_dict in prj_dict.items():
                    sp_metrics = Metrics()
                    sp_metrics._prj_name = prj_name
                    sp_metrics._sp_name = sp_name
                    sp_metrics._state_category = sp_metrics_dict.get("state-category", "unknown")
                    sp_metrics._unpacked_files = sp_metrics_dict.get("unpacked-files", 0)
                    sp_metrics._num_repos = sp_metrics_dict.get("num-repos", 0)
                    sp_metrics._instances_veryhigh = sp_metrics_dict.get("instances-veryhigh", 0)
                    sp_metrics._instances_high = sp_metrics_dict.get("instances-high", 0)
                    sp_metrics._instances_medium = sp_metrics_dict.get("instances-medium", 0)
                    sp_metrics._instances_low = sp_metrics_dict.get("instances-low", 0)
                    sp_metrics._files_veryhigh = sp_metrics_dict.get("files-veryhigh", 0)
                    sp_metrics._files_high = sp_metrics_dict.get("files-high", 0)
                    sp_metrics._files_medium = sp_metrics_dict.get("files-medium", 0)
                    sp_metrics._files_low = sp_metrics_dict.get("files-low", 0)

                    # validate state category
                    if sp_metrics._state_category not in ["unknown", "inproc", "analyzed", "uploaded", "delivered", "stopped"]:
                        sp_metrics._state_category = "unknown"

                    prj_metrics[sp_name] = sp_metrics

                metrics[prj_name] = prj_metrics

            return metrics

    except json.decoder.JSONDecodeError as e:
        print(f'Error loading or parsing {metricsFilename}: {str(e)}')
        return {}

class MetricsJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, Metrics):
            return {
                "state-category": o._state_category,
                "unpacked-files": o._unpacked_files,
                "num-repos": o._num_repos,
                "instances-veryhigh": o._instances_veryhigh,
                "instances-high": o._instances_high,
                "instances-medium": o._instances_medium,
                "instances-low": o._instances_low,
                "files-veryhigh": o._files_veryhigh,
                "files-high": o._files_high,
                "files-medium": o._files_medium,
                "files-low": o._files_low,
            }

        else:
            return {'__{}__'.format(o.__class__.__name__): o.__dict__}

def saveMetrics(metricsFilename, metrics):
    with open(metricsFilename, "w") as f:
        json.dump(metrics, f, indent=4, cls=MetricsJSONEncoder)
