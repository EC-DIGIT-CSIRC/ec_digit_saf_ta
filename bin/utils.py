# Sysdiagnose Analysis Framework (SAF) Splunk Addon
# Copyright (EC DIGIT CSIRC 2025). Licensed under the EUPL-1.2 or later

#!/usr/bin/env python3

from pathlib import Path
from configparser import ConfigParser

def get_config(config_file: str = 'ec_digit_saf_ta_settings.conf') -> ConfigParser:
    config = ConfigParser()
    # Local path first, then default path
    config_path = Path(__file__).parent.parent / 'local' / config_file
    if config_path.exists():
        config.read(config_path)
    # Default path
    else:
        config_path = Path(__file__).parent.parent / 'default' / config_file
        if config_path.exists():
            config.read(config_path)
        else:
            raise FileNotFoundError(f"Configuration file {config_file} not found.")
    return config
