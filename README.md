# scaffold

scaffold is a command-line tool to automate the process of running and clearing scans via Fossology, and preparing and publishing reports of the results.

## Installation

In order to use scaffold, you will need a [Fossology server](https://github.com/fossology/fossology) to perform the actual codebase scans. scaffold uses fossdriver (see below) which I have previously used for a Fossology server with version 3.6.0. It may work for later versions of Fossology, but I have not tested it with them.

You will also need a web server where HTML and XLSX files with reports will be made available. This web server should be configured such that your local system can either scp files to it or access the files locally.

You will also need a public GitHub org to host repos where SPDX files from the Fossology scans will be committed.

scaffold requires Python 3. You may want to create a [virtual environment](https://pypi.org/project/virtualenvwrapper/) for the installation.

Install the requirements from requirements.txt: `pip install -r requirements.txt`

You will also need to install [fossdriver](https://github.com/fossology/fossdriver), which is not currently available on PyPI and therefore must be installed manually. See the installation instructions shown there.

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
