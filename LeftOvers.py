#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LeftOver
An advanced scanner to find residual files on web servers.
"""

import sys
import os

# Ensure root directory is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.cli import main

if __name__ == "__main__":
    main()