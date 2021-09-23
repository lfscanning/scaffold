## scaffold concepts

### Configuration

The following concepts are important in order to understand how scaffold works and how its configuration is structured:

* **policy**: represents a particular categorization of licenses, within the scope of a project.
  * Each policy typically defines a category of "Project licenses".
  * Each policy typically defines other categories such as "Non-OSS", "Copyleft", "Weak copyleft", "Attribution", "Other", etc.
  * Each policy should also define a category with the specific name "No license found".
* **project**: represents a collection of related subprojects.
  * Each project defines one or more policies.
  * Each project contains one or more subprojects.
  * Each project is defined as being of one of the following types:
    * `github`: means that the project's repos are all stored on GitHub, _in a separate GitHub org_ for each subproject.
    * `github-shared`: means that the project's repos are all stored on GitHub, _together in the same GitHub org_ for all subprojects.
    * `gerrit`: means that the project's repos are all stored on Gerrit.
* **subproject**: represents a collection of related repos within one project.
  * Each subproject contains the information about which repos it includes in the scanning or ignores / excludes.
  * If multiple license policies are defined for the overarching project, then each subproject can specify which of those policies applies to it.

### Process

For each project and each subproject, scaffold maintains a record of its current status. "status" is a field in the config.json file, and is one of a specified set of values (described below) that reflects what has already been completed for this subproject.

When scaffold receives a `run` command for a subproject, it does the following:
1. look at that subproject's current status
2. attempt to take the next action
3. if failing, stop work on this subproject; report the problem; and leave the status as-is
4. if succeeding, update status to reflect what it just completed, and loop back to 2, trying to go on to the next action

If scaffold receives a `run` command for a project as a whole (rather than a specific subproject), it will try to advance each subproject within that project using the above process.

Depending how the project is configured, it might be necessary to get all subprojects to the same state before any of them can proceed further. Primarily this occurs where a project is configured to generate a combined report for all subprojects; before it can do so, the reports for each subproject need to be completed first.

### Status values

Understanding the different status values (defined at the top of [`datatypes.py`](../datatypes.py)) is key to understanding how scaffold works.

Below is a list of the valid status values, and what it means for a subproject (or project) to be in each status.

Status | Meaning | Next action
------------------------------
`START` | Initial state to begin this month | Retrieve listing of repos; halt if there are any new repos that need to be categorized whether to scan or ignore
`GOTLISTING` | All repos in org are categorized either to scan or ignore | Clone the code from each repo in turn, and save it temporarily in the `code/` folder
`GOTCODE` | Code from all repos has been cloned | Prepare the code for scanning (e.g. by removing `.git/` directories and potentially others), zip the code into a single `.zip` file, and delete the unzipped code
`ZIPPEDCODE` | Code has been cleaned, zipped and deleted | If WhiteSource scanning is configured, run the WhiteSource Unified Agent on it; if not configured, just proceed to next status
`UPLOADEDWS` | If WhiteSource scanning is configured, WhiteSource scan has completed | Upload the code to Fossology using fossdriver
`UPLOADEDCODE` | Code was successfully uploaded to Fossology | Run Fossology's nomos and monk agents; run any configured bulk monk text matches; and run the copyright notice agent
`RANAGENTS` | Fossology agents have completed running | Stops here; user goes into Fossology and clears the scan results, and then gives scaffold the `clear` command when ready to proceed
`CLEARED` | User has finished clearing the Fossology scan results and has given scaffold the `clear` command | Retrieve the SPDX document for this scan from Fossology and save it to the `spdx/` folder
`GOTSPDX` | SPDX document was retrieved and saved locally | Process the SPDX document and make sure that this subproject's policy accounts for all licenses; halt if there are any license expressions that need to be categorized
`PARSEDSPDX` | SPDX document was processed and all license expressions are accounted for in the subproject's policy | Create XLSX and JSON files in the `report/` directory with the categorized license scan results
`CREATEDREPORTS` | XLSX and JSON files with categorized results were created | Apply the current set of findings for this project, and create the HTML report and instances file for user review
`MADEDRAFTFINDINGS` | HTML report and instances file were created from project's current findings | Stops here; user reviews the reports and instances file, and either re-runs after updating the findings or else gives scaffold the `approve` command when ready to proceed
`APPROVEDFINDINGS` | User has given scaffold the `approve` command | Create the "final" version of the HTML report with findings
`MADEFINALFINDINGS` | Final HTML findings report was created | Add the SPDX document (retrieved from Fossology) to the project's SPDX repo; commit it; and push it up to GitHub
`UPLOADEDSPDX` | SPDX document was committed and pushed to GitHub | Transfer the HTML and XLSX reports (via scp) to the web server
`UPLOADEDREPORTS` | HTML and XLSX reports were posted to web server | If JIRA is configured, update JIRA tickets; if not configured, just proceed to next status
`FILEDTICKETS` | If JIRA is configured, tickets have been updated | Stops here; user emails the HTML and XLSX links to project maintainers, and then gives scaffold the `deliver` command
`DELIVERED` | User has given scaffold the `deliver` command | Complete; no further action
`STOPPED` | For some reason (e.g., empty repo), scanning will not proceed | Complete; no further action
