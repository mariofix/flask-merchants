# flask-merchants

This project is under development, not for production use.

[![PyPI version](https://badge.fury.io/py/flask-merchants.svg)](https://badge.fury.io/py/flask-merchants)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/flask-merchants.svg)](https://pypi.org/project/flask-merchants/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A unified payment processing toolkit for Flask/Flask-Admin applications, inspired by [django-payments](jazzband/django-payments).

## Overview

flask-merchants is an all-in-one payment processing solution designed to integrate seamlessly with Flask/Flask-Admin applications.
This modular payment integration system aims to simplify the implementation of various payment gateways and provide a
flexible interface for handling different payment methods.

## Features

- Easy integration with Flask applications
- Support for multiple payment gateways
- Customizable payment workflows
- Webhook handling for payment status updates
- Extensible architecture for adding new payment providers
- Unified API across different payment services

## Installation

```bash
pip install flask-merchants
```

## Quick Start

```python
from flask_merchants import Merchants

```

## Documentation

For detailed documentation, please visit [our documentation site](https://mariofix.github.io/flask-merchants).

## License

Merchants is released under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgements

This project was inspired by the [django-payments](https://github.com/jazzband/django-payments) library and aims to provide similar functionality for Flask
applications, some parts were made with Claude and/or ChatGPT.

## Changelog

See the [CHANGELOG](CHANGELOG) file for more details.
