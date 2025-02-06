# scaffold

scaffold is a command-line tool to automate the process of running and clearing scans via Fossology, and preparing and publishing reports of the results.

## Installation

In order to use scaffold, you will need a web server where HTML and XLSX files with reports will be made available. This web server should be configured such that your local system can either scp files to it or access the files locally.

You will also need a public GitHub org to host repos where SPDX files from the Fossology scans will be committed.

scaffold requires Python 3.11. You may want to create a [virtual environment](https://pypi.org/project/virtualenvwrapper/) for the installation.

Install the requirements from requirements.txt: `pip install -r requirements.txt`

In order to shorten the amount of typing, I typically create an alias to `sc` in my `~/.bashrc` for calls to run scaffold:

```shell
alias sc='python /INSTALL-LOCATION/scaffold/scaffold.py'
```

### Sbom

To use the `sbom` command, [trivy](https://aquasecurity.github.io/trivy), [NPM](https://www.npmjs.com/), [Go](https://go.dev/), [parlay](https://github.com/snyk/parlay) and [cdsbom](https://github.com/jeffmendoza/cdsbom) must be installed on the local machine.

The current version of Trivy and Parlay requires Go version 1.22.X installed on the target machine.

To install Trivy:

```shell
git clone --depth 1 --branch v0.54.0 https://github.com/aquasecurity/trivy.git
cd trivy
go install ./cmd/trivy
```

The location of the Trivy command needs to be added to the config file and/or as an environment variable `TRIVY_EXEC_PATH`.

To install Parlay:

```shell
git clone --depth 1 --branch v0.5.1 https://github.com/snyk/parlay.git
cd parlay
go install .
```

The location of the Parlay command needs to be added to the config file and/or as an environment variable `PARLAY_EXEC_PATH`.

To install cdsbom:
```shell
git clone --depth 1 https://github.com/jeffmendoza/cdsbom.git
cd cdsbom
go install .
```
The location of the cdsbom command needs to be added to the config file and/or as an environment variable `CDSBOM_EXEC_PATH`.

In addition [NPM](https://www.npmjs.com/) must be installed.

The location of the NPM command needs to be added to the config file or as an environment variable `NPM_EXEC_PATH`.

## Configuration

Running scaffold requires quite a lot of configuration. See [docs/config.md](docs/config.md) for more information about setup and configuration.

## Usage

After you've installed and configured scaffold, see [docs/usage.md](docs/usage.md) for details about how to use scaffold.

## License

scaffold is licensed under the [Apache License, version 2.0 (Apache-2.0)](./LICENSE.txt).
