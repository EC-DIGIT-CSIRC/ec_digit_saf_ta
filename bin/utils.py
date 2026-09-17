# Sysdiagnose Analysis Framework (SAF) Splunk Addon
# Copyright (EC DIGIT CSIRC 2025). Licensed under the EUPL-1.2 or later

#!/usr/bin/env python3

from logging import Formatter
from logging.handlers import RotatingFileHandler
from pathlib import Path
from configparser import ConfigParser
import os


def get_config(config_file: str = 'ec_digit_saf_ta_settings.conf') -> ConfigParser:
    """Load configuration from a file.
    Args:
        config_file (str): Name of the configuration file.
    Returns:
        ConfigParser: Loaded configuration object.
    """
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


def get_logging_filehandler(log_filename: str = 'ec_digit_saf_ta_read_cases.log',
                            max_size: int = 1, max_files: int = 2) -> RotatingFileHandler:
    """Create a rotating file handler for logging.
    Args:
        log_file (str): Name of the log file.
        max_size (int): Maximum size of the log file in MB before rotation.
        max_files (int): Number of backup files to keep.
    Returns:
        RotatingFileHandler: Configured file handler for logging.
    """
    splunk_home = Path(os.environ.get("SPLUNK_HOME", "/opt/splunk"))
    log_file = splunk_home / 'var' / 'log' / 'splunk' / log_filename

    # Ensure the log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(log_file, maxBytes=max_size*1024*1024, backupCount=max_files)
    handler.setFormatter(Formatter('%(asctime)s %(levelname)s %(module)s %(message)s'))

    return handler


def normalize_tags(tags: list) -> list:
    """Normalize a tags list into a canonical, comparable form.

    The cases.json file is loaded as a JSON object, so ``tags`` is already a
    list of strings. Normalization trims whitespace, drops empties, lowercases
    (tags are case-insensitive), de-duplicates, and sorts ascending. This makes
    reordering, duplication, and case changes count as no change.

    Args:
        tags: The tags value from a case (a list of tag strings). Callers are
              expected to pass a list; use ``[]`` for missing tags.
    Returns:
        list: Canonical, sorted, lowercased, de-duplicated list of tag strings.
              Empty list on empty input.
    """
    if not tags:
        return []

    canonical = set()
    for tag in tags:
        tag = str(tag).strip().lower()
        if tag:
            canonical.add(tag)

    return sorted(canonical)
