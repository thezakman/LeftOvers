#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

from setuptools import setup

# Single source of truth: read the version straight from __version__.py so it
# never drifts from pyproject.toml / the package's __version__.
_version_text = (Path(__file__).parent / "__version__.py").read_text(encoding="utf-8")
_version_match = re.search(
    r'^__version__\s*=\s*["\']([^"\']+)["\']', _version_text, re.MULTILINE
)
if not _version_match:
    raise RuntimeError("Unable to find __version__ in __version__.py")
VERSION = _version_match.group(1)

setup(
    name="LeftOvers",
    version=VERSION,
    description="An advanced scanner to find residual files on web servers",
    author="TheZakMan",
    packages=["leftovers", "leftovers.core", "leftovers.utils"],
    package_dir={
        "leftovers": ".",
        "leftovers.core": "core",
        "leftovers.utils": "utils",
    },
    py_modules=["leftovers.LeftOvers", "leftovers.app_settings"],
    include_package_data=True,
    install_requires=[
        "requests>=2.31.0",
        "colorama>=0.4.6",
        "rich>=13.4.2",
        "tqdm>=4.66.1",
        "urllib3>=2.0.4",
        "tldextract>=3.4.4",
        "pyOpenSSL>=23.2.0",
        "cryptography>=41.0.3",
    ],
    entry_points={
        "console_scripts": [
            "leftovers=leftovers.core.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="security, scanner, web, pentest, residual files, backups",
)