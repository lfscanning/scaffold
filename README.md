# scaffold

scaffold is a command-line tool to automate the process of running and clearing scans via Fossology, and preparing and publishing reports of the results.

## Installation

In order to use scaffold, you will need a web server where HTML and XLSX files with reports will be made available. This web server should be configured such that your local system can either scp files to it or access the files locally.

You will also need a public GitHub org to host repos where SPDX files from the Fossology scans will be committed.

scaffold requires Python 3.11. You may want to create a [virtual environment](https://pypi.org/project/virtualenvwrapper/) for the installation.

Install the requirements from requirements.txt: `pip install -r requirements.txt`

In order to shorten the amount of typing, I typically create an alias to `sc` in my `~/.bashrc` for calls to run scaffold:

```
alias sc='python /INSTALL-LOCATION/scaffold/scaffold.py'
```

## Configuration

Running scaffold requires quite a lot of configuration. See [docs/config.md](docs/config.md) for more information about setup and configuration.

## Usage

After you've installed and configured scaffold, see [docs/usage.md](docs/usage.md) for details about how to use scaffold.

## License

scaffold is licensed under the [Apache License, version 2.0 (Apache-2.0)](./LICENSE.txt).
