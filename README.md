# NovelSearch

[![PyPI](https://img.shields.io/pypi/v/NovelSearch.svg)](https://pypi.org/project/NovelSearch/)
[![Changelog](https://img.shields.io/github/v/release/RKeelan/NovelSearch?include_prereleases&label=changelog)](https://github.com/RKeelan/NovelSearch/releases)
[![Tests](https://github.com/RKeelan/NovelSearch/actions/workflows/test.yml/badge.svg)](https://github.com/RKeelan/NovelSearch/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/RKeelan/NovelSearch/blob/master/LICENSE)

Search for novels

## Installation

Install this tool using `pip`:
```bash
pip install NovelSearch
```
## Usage

For help, run:
```bash
NovelSearch --help
```
You can also use:
```bash
python -m NovelSearch --help
```
## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:
```bash
cd NovelSearch
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
