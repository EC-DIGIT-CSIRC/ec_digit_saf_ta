# EC DIGIT CSIRC Add-on for Sysdiagnose Analysis Framework (SAF)
# Copyright (EC DIGIT CSIRC 2025). Licensed under the EUPL-1.2 or later

#!/usr/bin/env python3
from datetime import datetime
import json
import logging
from pathlib import Path

from utils import get_config, get_logging_filehandler

STATE_PATH = Path(__file__).parent.parent / 'local' / 'cases_state.json'
CONFIG = get_config()

# Configure logging
handler = get_logging_filehandler(
    max_size=max(CONFIG.getint("logging", "max_size_mb", fallback=1), 1),  # Ensure at least 1 MB
    max_files=max(CONFIG.getint("logging", "max_backup_files", fallback=2), 1) # Ensure at least 1 backup file
)
logging.basicConfig(
    level=CONFIG.getint("logging", "level", fallback=logging.INFO),
    handlers=[handler]
)

def load_state() -> dict:
    """Load the state of processed case IDs per cases folder from a JSON file."""
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                raw = json.load(f)
                # Convert lists to sets for easier processing
                return {k: set(v) for k, v in raw.items()}
        except Exception as e:
            logging.error(f"Failed to load state file: {e}")
            return {}
    return {}

def save_state(state: dict) -> None:
    """Save the state of processed case IDs per cases folder to a JSON file."""
    try:
        # Convert sets to lists for JSON serialization
        with open(STATE_PATH, "w") as f:
            json.dump({k: list(v) for k, v in state.items()}, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save state file: {e}")

def main():
    processed_case_ids = load_state()  # dict: root -> set(case_id)
    # Get the root path from config, default to 'cases'
    root_path = Path(CONFIG.get("cases", "folder", fallback='/cases'))
    # Find all cases.json files recursively
    total = 0
    for cases_file in root_path.rglob("cases.json"):
        logging.info(f"Processing cases from {cases_file}")
        root = cases_file.parent.name
        try:
            with open(cases_file, "r") as f:
                cases = json.load(f)
                root_cases = processed_case_ids.get(root, set())
                cached_root_cases = len(root_cases)
                for case_id, event in cases.items():
                    if case_id in root_cases:
                        logging.warning(f"Skipping already processed case id: {case_id} for {root}")
                        continue
                    # Add fields
                    event['timestamp'] = datetime.strptime(event['date'], "%Y-%m-%dT%H:%M:%S.%f%z").timestamp()
                    event['host'] = root
                    event['case_id'] = case_id
                    event['source'] = cases_file.as_posix()
                    print(json.dumps(event))
                    root_cases.add(case_id)
                processed_case_ids[root] = root_cases
                logging.info(
                    f"Processed {len(cases)} cases for {root}, "
                    f"newly added {len(root_cases) - cached_root_cases} cases.")
            total += 1
        except Exception as e:
            logging.error(f"Failed to process cases file {cases_file}: {e}")

    logging.info(f"Total cases files processed: {total}")
    # Save the state of processed case IDs or clear if no cases were processed
    save_state(processed_case_ids if total > 0 else {})


if __name__ == "__main__":
    main()