# scaffold configuration

## Overview

scaffold depends on having a local directory where all configuration and local scaffold activity is stored.

Within this directory, there will be a subdirectory for each monthly scan, named in the form `yyyy-mm/`. Each of these subdirectories has a primary configuration file `config.json`. This `config.json` file contains the information about scaffold's configuration, including an entry for each project and subproject that scaffold is scanning.

When scaffold is run from the command line, it will load in `config.json`; process the requested actions; and output a revised `config.json` file with the updated status details. It will also store a backup copy of the prior `config.json` file in the `backup/` subdirectory for that month, in case there are any errors that result in an invalid `config.json` file being outputted.

In addition to the `config.json` file, a `findings-[project].yaml` file is needed to generate the HTML report.  Details on the file format are below.

An optional `matches-[project].json` file providing information on bulk matches for fossology.  See the details below.

There are also some other configuration files containing secrets that should be stored in the user's home directory. These are also detailed below.

## Configuration

### Create main scaffold directory

Create the main directory where scaffold activity will occur. Note that this is a working directory, and should be different from where the scaffold code itself is stored.

This is typically in the user's home directory, e.g.:

```
> mkdir /home/USER/scaffold
```

If the directory is different than `~/scaffold/`, then you will need to define a `SCAFFOLD_HOME` environment variable containing the location of this directory.

Wherever this directory is stored, in the instructions below it will be referred to as $SCAFFOLD-HOME.

Within this directory, also create a subdirectory called `spdxrepos/`, e.g.:

```
> mkdir $SCAFFOLD-HOME/spdxrepos
```

This is where repos will be cloned for public posting of SPDX files from the cleared Fossology scans.

Finally, create a subdirectory for the current month, e.g. for September 2021:

```
> mkdir $SCAFFOLD-HOME/2021-09
```

### Create config.json file

A very basic template for the `config.json` file is available at [`config-template.json`](./config-template.json). Copy this file into the folder for this month's scans:

```
> cp docs/config-template.json $SCAFFOLD-HOME/2021-09/config.json
```

Edit that config.json's contents to configure for your setup. The following provides details about what the various fields mean.

#### "config" object

* `storepath`: on-disk path for $SCAFFOLD-HOME
* `month`: this month as a string in "YYYY-MM" format, e.g. `"2021-09"`
* `version`: version of this config.json file. Starts at 1 and increments each time the config.json file is modified by scaffold (saving the prior version to the `backup/` subfolder)
* `spdxGithubOrg`: name of GitHub org where repos containing the SPDX documents from Fossology will be posted
* `spdxGithubSignoff`: name and email address to use in `Signed-off-by:` commit messages for the SPDX documents
* `webReportsPath`: on-disk path on the web server for where reports should be scp'd
* `webReportsUrl`: URL path fragment to appear between the web server domain name and the specific project/subproject address for reports, typically just `"reports"`
* `webServerUseScp`: if true, use SCP to copy files to the webserver.  If false, the files will be copied to the`webReportsPath` directly
* `webServer`: domain name for the web server where reports will be uploaded
* `webServerUsername`: user name of account on web server, used for SCP connections - required only if `webServerUseScp=true`

There are also several values prefixed by `ws`. These are currently required to be present, but are not used unless one or more projects are configured to upload scan findings to WhiteSource (FIXME: details to be added).

#### "project" objects:

Each project will have a unique identifier / key which should be used as its ID in all scaffold commands.

Within the project's object are the following fields:
* `slm`: refers to SPDX License Manager (a precursor to scaffold); contains the following fields:
  * `policies`: Each policy has a unique identifier and contains the following fields:
    * `categories`: an ordered array of categories of licenses. Each category has the following properties:
      * `name`: a unique name for the category
      * `licenses`: an ordered array of licenses in this category. Each license as the following properties:
        * `name`: a unique reference for this license, which will appear in the reports. Can be an SPDX license expression or any other text.
        * `aliases`: an array of SPDX license expressions, received from the SPDX document from Fossology, which should be mapped and translated to this license name in the reports.
      * `flagged`: an array of category names that should be flagged in the internal instances JSON report, for review as key findings
    * NOTE: there should always be one category with the name "No license found". It should contain a license also with the name "No license found", and the alias "NOASSERTION". scaffold uses this category/license pair to break out files with no license found that meet certain other criteria (e.g. with a specified file extension to ignore, in a third party directory to ignore, or empty files)
  * `combinedReport`: boolean, to indicate whether there should also be an aggregate report that combines the findings and results from all of the subprojects together
  * `extensions-skip`: array of filename extensions that should be grouped into the "excluded file extension" category in the report if no license is detected
  * `thirdparty-dirs`: array of directories whose sub-contents should be grouped into the "third party directory" category in the report if no license is detected

* `status`: for some project types (e.g. `gerrit`), the project's overall status is also tracked.

* `subprojects`: object containing the project's subprojects and their configurations

* `type`: one of the following values:
  * `github`: means that each of the project's subprojects are hosted on GitHub _in different orgs_
  * `github-shared`: means that each of the project's subprojects are hosted on GitHub _in the same org_
  * `gerrit`: means that each of the project's subprojects are hosted on Gerrit
  * Each subproject will have a sub-property with the same key as the project's `type`, described further below

If the project's `type` is `github-shared`, then it will also contain a `github-shared` property with the following fields:
* `org`: the GitHub org identifier
* `repos-ignore`: array of repos that should _not_ be assigned to any subproject.
* `repos-pending`: array of repos that were detected and need to be either assigned to a subproject or added to `repos-ignore`.

If the project's `type` is `gerrit`, then it will also contain a `gerrit` property with the following fields:
* `apiurl`: the URL to the project's Gerrit API endpoint
* `subproject-config`:
  * `"one"` means that all repos will be combined into exactly one subproject.
  * `"auto"` means that scaffold will automatically create and remove subprojects, based on the hierarchy within the Gerrit repos.
  * `"manual"` means that the user will need to create and remove subprojects manually.
* `repos-ignore`: array of repos that should _not_ be assigned to any subproject.
* `repos-pending`: array of repos that were detected and need to be either assigned to a subproject or added to `repos-ignore`.

#### "subproject" objects:

Each subproject will have an identifier / key which is unique within that project, and which should be used as its ID in all scaffold commands.

Within the subproject's object are the following fields:
* `status`: the [current status](./concepts.md#status-values) of the subproject in scaffold for this month
* `slm`: an object storing data relating to the subproject's SPDX files and any detected licenses that need to be added to the applicable policy's categories
* `web`: an object storing data relating to where the HTML and XLSX reports are uploaded
* `code`: an object storing data relating to code that has been pulled from the repos

There is also a property with the same name as the parent project's `type`, with different sub-fields depending on the project's `type` value (FIXME: details to be added).

### Create a .scaffold-secrets.json

The file must be created in your home directory.

See the [sample file](./sample-scaffold-secrets.json) file for the JSON file structure.

The JSON file has the following fields:
* `default_github_oauth`: A required GitHub OAuth token which is used to access gitHub if no project specific tokens are provided.  See the [GitHub OAuth documentation](https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps) for details on how to create the token.
* `projects`: Map of a project name to project specific secrets.  The project specific secrets include:
  * `jira`: Optional Jira server and login information
  * `whitesource`: Optional whitesource server authentication information
  * `github_oauth`: Optional project specific GitHub OAuth token

### create findings-[project].yaml files for each project

The `findings-[project].yaml` file (where `[project]` is replaced with the project name used in the config file) contains information used in the generation of the HTML report.  The file contains a list of `findings` with the following fields:
* `id` Id unique to each finding
* `priority` Priority of the finding as displayed in the report
* `text` text used for the finding in the HTML report
* `title` optional field which, if included, will set the title of the ticket in JIRA

The `findings` elements contains one or more of the following matches fields.  A match is made if ALL of the match conditions are met (e.g. an AND of all matches). 
* `matches-license` license name that this finding applies to as it appears in Fossology or the license name in the `policies.licenses.name` field if there is a matching Fossology alias (see the `licenses` section of `policies` above.  
* `matches-path` pattern for matching file paths
  * Without special characters, the `matches-path` will match if it is contained within the full file path (e.g. a substring of the full file path)
  * With a `!` character at the start of the string, there will be a match if the file path does NOT contain the string
  * With a `$` at the end of the string, it will only match if the string is at the end of the file's path
* `matches-subproject` subproject the finding applies to

See the [findings-sample.yaml](findings-sample.yaml) for an example file.

### matches-[project].json files for each project

The `matches-[project].json` (where `[project]` is replaced with the project name used in the config file) file optionally store information for bulk matches.  The file contains a list of bulk matches with the following fields:
* `comment` Descriptive comment - such as the name of the header text being matched
* `text`: Regular expression of the text to match
* `actions`: List of actions with the following fields:
	* `action`: Action to be taken - one of:
		* `add`: Add a new element
		* FIXME: any others?
	* `license`: License ID

See the [matches-sample.json](matches-sample.json) for an example file.
