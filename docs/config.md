# scaffold configuration

## Overview

scaffold depends on having a local directory where all configuration and local scaffold activity is stored.

Within this directory, there will be a subdirectory for each monthly scan, named in the form `yyyy-mm/`. Each of these subdirectories has a primary configuration file `config.json`. This `config.json` file contains the information about scaffold's configuration, including an entry for each project and subproject that scaffold is scanning.

When scaffold is run from the command line, it will load in `config.json`; process the requested actions; and output a revised `config.json` file with the updated status details. It will also store a backup copy of the prior `config.json` file in the `backup/` subdirectory for that month, in case there are any errors that result in an invalid `config.json` file being outputted.

There are also some other configuration files containing secrets that should be stored in the user's home directory. These are also detailed below.

## Concepts

The following concepts are important in order to understand how scaffold's configuration is structured:

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
