#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="LeftOvers",
    version="0.1.0",
    description="Um scanner avançado para encontrar arquivos residuais em servidores web",
    author="thezakman",
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
            "leftovers=LeftOvers:main",
        ],
    },
    python_requires=">=3.6",
)