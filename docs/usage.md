## scaffold usage

Before reading this, make sure that you have [installed all requirements](../README.md) and completed [configuration](./config.md).

Also, before reading this, it's important to read and understand the [concepts for how scaffold works](./concepts.md).

## Command format

scaffold is a command-line tool. Assuming that you've configured `sc` to be an alias to run scaffold (see the installation instructions), every run of scaffold takes the following form:

```
> sc [YYYY-MM] [COMMAND] [ADDITIONAL-ARGUMENTS]
```

`YYYY-MM` is the 4-digit year and two-digit month for the current scanning round, e.g. `2021-09`.

`COMMAND` is one of the commands described below.

`ADDITIONAL-ARGUMENTS` will vary depending on which command you're running. Many of the commands take the project identifier (often followed by the subproject identifier) as their first two parameters, e.g.:

```
> sc 2021-09 run project1 subproject4
```

which would run the next action on subproject4 within project1. For these commands, if a project is specified but no subproject is specified, typically it will attempt to run the requested command for each subproject within that project.

## Typical workflow

The following example assumes the following configuration has been set up in `config.json`:
* `project1` is defined as a project of type `github`, where each subproject has its own GitHub org
* `apache` is defined as a policy within `project1`
* `subproject4` is defined as a subproject within `project1`, using policy `apache`
* WhiteSource and JIRA are not configured
* the findings configuration file `findings-project1.yaml` and the matches configuration file `matches-project1.json` have been defined

Assuming that no errors are encountered, a typical workflow of the scanning process looks like the following:
* The user starts by running `> sc 2021-09 run project1 subproject4`
  * scaffold retrieves the list of repos from subproject4's GitHub org
    * if any previously-seen repos are no longer present, they are removed from the list to scan
    * if any new repos are seen:
      * they are added to the `repos-pending` array for subproject4
      * scaffold will stop running
      * the user must edit the `config.json` file to move each repo from subproject4's `repos-pending` array into either `repos` or `repos-ignore`, and then restart with the same `run` command
  * scaffold clones the code from each repo in subproject4's `repos` array. It removes the `.git/` folder from each, zips all of the code together into a single .zip file, and then deletes the old code.
  * the .zip file is uploaded to Fossology
  * the nomos, monk and copyright agents are run on the uploaded code in Fossology
  * any monk bulk text matches defined in the `matches-project1.json` file are also run
  * After the Fossology agents have completed running, scaffold stops with subproject4 in the `RANAGENTS` status.
* The user now goes into Fossology and manually clears the license and copyright findings.
* After clearing the Fossology results, the user runs: `> sc 2021-09 clear project1 subproject4`
* The user continues the scaffold process by running `> sc 2021-09 run project1 subproject4`
  * scaffold retrieves the SPDX document from Fossology with the cleared results
  * if there are any license expressions from the SPDX document that aren't currently in the `apache` policy for `project1`:
    * they are added to the `licenses-pending` array for subproject4
    * scaffold will stop running
    * the user must edit the `config.json` file to add an entry for each license expression to one of the categories in `project1`'s `apache` policy, and then restart with the same `run` command
  * scaffold creates categorized XLSX and JSON files:
    * XLSX: a summary sheet showing the total number of files for each categorized license, as well as detailed sheets for the specific files in each category
    * JSON: an internally-used categorized license file which is fed as input to the next stages
  * scaffold creates initial draft "Key findings" HTML report and JSON instances report, applying the findings configuration from `findings-project1.yaml`
  * scaffold stops with subproject4 in the `MADEDRAFTFINDINGS` status
* The user reviews the HTML report and JSON instances report.
  * If any key findings are not currently reported but should be called out, the user edits the `findings-project1.yaml` file to add an entry for the finding
  * After making the desired changes, the user manually deletes the HTML report and then restarts with the same `run` command to regenerate the reports
* After confirming that all desired key findings are shown on the HTML report, the user runs: `> sc 2021-09 approve project1 subproject4`
* The user continues the scaffold process by running `> sc 2021-09 run project1 subproject4`
  * scaffold finalizes the HTML report
  * scaffold adds the SPDX file to the spdx-project1 repo, commits it and pushes it up to GitHub
    * Note that the spdx-project1 repo must already be created in the SPDX Github repository (e.g. lfscanning) and cloned into the spdxrepos directory.  If the repository needs to be created, create an empty repo with the name `spdx-` followed by the project name (e.g. `spdx-project`).  Use the CC-0 license as the license for the new repository.
  * scaffold uploads the HTML and XLSX reports to the web server
* The user gets the links for these reports: `> sc 2021-09 printlinks project1 subproject4` and emails them to the project maintainers
* The user then finalizes the process by running `> sc 2021-09 deliver project1 subproject4`, which moves it to the `DELIVERED` status so that it is complete.


## Primary commands

### newmonth

* Additional arguments: N/A
* Example: `> sc 2021-09 newmonth`
* Summary: Creates a new subfolder within $SCAFFOLD-HOME for the next month after the one specified, copying configuration files.
* Details:
  * `newmonth` will create a new subfolder for the next month's scan cycle. So, if `2021-09` is specified, then it will copy the configuration from the `2021-09/` folder into a new `2021-10/` folder, updating values as appropriate.
  * It will reset the status for all projects and subprojects to `START`.
  * It will copy over the `config.json` file, as well as the `findings-*.yaml` and `matches-*.json` files from the prior month.

### run

* Additional arguments: `PROJECT [SUBPROJECT]`
* Example: `> sc 2021-09 run project1 subproject4`
* Summary: Attempts to run the next action in the standard sequence for one or all SUBPROJECTs in the PROJECT.
  * If no SUBPROJECT is specified, it will go in turn for each SUBPROJECT within the specified PROJECT.
  * See the [concepts guide](./concepts.md#status-values) for an explanation of what action will occur, depending on the subproject's current status.
  * `run` will cause scaffold to run for as many actions as it can, until it either:
    * reaches the `DELIVERED` or `STOPPED` states;
    * encounters a state that requires the user to take an action and then a manual command before proceeding (e.g. `RANAGENTS` => `clear`, `MADEDRAFTFINDINGS` => `approve`);
    * encounters a condition that requires the user to resolve a problem before proceeding (e.g. `START` => assign `repos-pending`, `GOTSPDX` => assign `licenses-pending`); or
    * encounters an unrecoverable error causing a crash.
  * If an unrecoverable error is encountered, it may be necessary for the user to manually edit the `config.json` file, potentially to adjust the `status` value to a different value in order to reset or proceed.

### status

* Additional arguments: `PROJECT [SUBPROJECT]`
* Example: `> sc 2021-09 status project1 subproject4`
* Summary: Display the current status value for one or all SUBPROJECTs in the PROJECT.

### clear

* Additional arguments: `PROJECT [SUBPROJECT]`
* Example: `> sc 2021-09 clear project1 subproject4`
* Summary: Marks the subproject as CLEARED after user clears its Fossology results.
* Details:
  * When the subproject is in the RANAGENTS status, the user should go to Fossology and manually clear the license and copyright scan results.
  * After that, the user runs the `clear` command, which sets the subproject's status to CLEARED.
  * The user then runs the `run` command for scaffold to proceed.
  * Running the `clear` command when the subproject is in any status other than RANAGENTS will have no effect.

### approve

* Additional arguments: `PROJECT [SUBPROJECT]`
* Example: `> sc 2021-09 approve project1 subproject4`
* Summary: Marks the subproject as APPROVEDFINDINGS after user reviews and confirms the key findings in the HTML report.
* Details:
  * When the subproject is in the MADEDRAFTFINDINGS status, the user should review the draft HTML report for key findings.
  * If any key findings are not listed, the user should:
    * edit the `findings-PROJECT.yaml` file to add new entries for the additional findings
    * delete the draft HTML report file
    * re-run the `> sc 2021-09 run PROJECT SUBPROJECT` command to regenerate the draft HTML report
    * review the newly-generated report
  * When the report is all set, the user runs the `approved` command, which sets the subproject's status to APPROVEDFINDINGS.
  * The user then runs the `run` command for scaffold to proceed.
  * Running the `approve` command when the subproject is in any status other than MADEDRAFTFINDINGS will have no effect.

### deliver

* Additional arguments: `PROJECT [SUBPROJECT]`
* Example: `> sc 2021-09 deliver project1 subproject4`
* Summary: Marks the subproject as DELIVERED after user delivers the report links to the project.
* Details:
  * Note that this command only marks the status as DELIVERED, after the user has manually emailed the results to the project team. It does not actually deliver / email the results itself.
  * The scaffold process is complete for this month after `deliver` is run.

### printlinks

* Additional arguments: `PROJECT [SUBPROJECT]`
* Example: `> sc 2021-09 printlinks project1 subproject4`
* Summary: Prints the URLs to one or more subprojects' HTML and XLSX reports, so that the user can copy and email them to the project team.

### clearlock

A lockfile is use to prevent more than one user from running the scaffold script at the same time for the same month.  In very unusual circumstances, the lockfile may not be properly removed (e.g. when the server crashes in the middle of a run).  In that situation, the clearlock command can be run to remove the lock file.

Note: this command should be used with caution and only run after verifying no other users are running the script.

## Additional Commands

### sbom

* Additional arguments: `PROJECT SUBPROJECT`
* Example: `> sc 2021-09 sbom project1 subproject4`
* Summary: Runs an SCA tool (currently [trivy](https://aquasecurity.github.io/trivy)) against the code with the licensing and vulnerability options and enriches the resultant SBOM with an enrichment tool (currently [parlay](https://github.com/snyk/parlay))
* Details:
  * Runs the trivy application with the following options:
    * `--scanners license,vuln`
	* `--format spdx-json`
  * Runs parlay application with the `ecosystems enrich` command
  * Uploads the resultant SPDX JSON file to the lfscanning repo spdx-[project-name]
  * Creates an xlsx report on the dependencies and store that report in the reports folder
