# Indexify Python Client


[![PyPI version](https://badge.fury.io/py/indexify.svg)](https://badge.fury.io/py/indexify)

## Installation

This is the Python client for interacting with the Indexify service.

To install it, simply run:

```shell
pip install indexify
```

## Usage

See the [getting started](https://getindexify.com/getting_started/) guide for examples of how to use the client.
Look at the [examples](examples) directory for more examples.

## Development

To install the client from this repository for development:

```shell
cd "path to this repository"
pip install -e .
```

Install and run the `poetry` package manager:

```shell
pip install poetry
poetry install
```

More information at [https://python-poetry.org/docs/](https://python-poetry.org/docs/).



### Environment Variables

IndexifyClient uses httpx under the hood, so there are many environment variables that can be used to configure the client. More information on supported environment variables can be found [here](https://www.python-httpx.org/environment_variables/).
