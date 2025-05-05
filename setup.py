#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="LeftOvers",
    version="1.1.9",
    description="An advanced scanner to find residual files on web servers",
    author="TheZakMan",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests>=2.27.1",
        "colorama>=0.4.4",
        "rich>=12.0.0",
        "tqdm>=4.62.3",
        "urllib3>=1.26.8",
        "tldextract>=3.1.2",
        "pyOpenSSL>=22.0.0",
        "cryptography>=36.0.0",
        "concurrent-futures-pool>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "leftovers=LeftOvers.__main__:main",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="security, scanner, web, pentest, residual files, backups",
)