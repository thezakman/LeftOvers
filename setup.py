#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_namespace_packages

setup(
    name="LeftOvers",
    version="1.2.3",  # Updated to match current app_settings.py version
    description="An advanced scanner to find residual files on web servers",
    author="TheZakMan",
    packages=find_namespace_packages(include=["LeftOvers", "LeftOvers.*"]),
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
        "concurrent-futures-pool>=1.1.0",
    ],
    entry_points={
        "console_scripts": [
            "leftovers=LeftOvers.__main__:main",
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