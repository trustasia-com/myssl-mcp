#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author: Hsiang Chen (hchen90)
# date: 2025-04-15

import json
import os

CONFIG_FILE = "config.json"


def load_config() -> dict:
    """Load configuration from a JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save configuration to a JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
