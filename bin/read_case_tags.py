# EC DIGIT CSIRC Add-on for Sysdiagnose Analysis Framework (SAF)
# Copyright (EC DIGIT CSIRC 2025). Licensed under the EUPL-1.2 or later

#!/usr/bin/env python3
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from utils import get_config, get_logging_filehandler, normalize_tags

STATE_PATH = Path(__file__).parent.parent / 'local' / 'tags_state.json'
CONFIG = get_config()

# Configure logging (own log file so the two scripted inputs do not interleave)
handler = get_logging_filehandler(
    log_filename='ec_digit_saf_ta_read_case_tags.log',
    max_size=max(CONFIG.getint("logging", "max_size_mb", fallback=1), 1),  # Ensure at least 1 MB
    max_files=max(CONFIG.getint("logging", "max_backup_files", fallback=2), 1)  # Ensure at least 1 backup file
)
logging.basicConfig(
    level=CONFIG.getint("logging", "level", fallback=logging.INFO),
    handlers=[handler]
)


def load_state() -> dict:
    """Load the last-known tags per case from a JSON file.

    Structure: serial_number -> {case_id: {"tags": [...]}}. The tags stored are
    the canonical (normalized) form as returned by normalize_tags.
    """
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load tags state file: {e}")
            return {}
    return {}


def save_state(state: dict) -> None:
    """Save the last-known tags per case to a JSON file."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save tags state file: {e}")


def main():
    state = load_state()  # dict: serial -> {case_id: {"tags": [...]}}
    # Get the root path from config, default to 'cases'
    root_path = Path(CONFIG.get("cases", "folder", fallback='/opt/sysdiagnose/cases'))
    total = 0
    for cases_file in root_path.rglob("cases.json"):
        logging.info(f"Processing tags from {cases_file}")
        try:
            with open(cases_file, "r") as f:
                cases = json.load(f)
            stats = {}
            for case_id, event in cases.items():
                root = event['serial_number']
                stats[root] = stats.get(root, 0)

                current = normalize_tags(event.get('tags', []))
                root_state = state.get(root, {})
                known = root_state.get(case_id)

                if known is None:
                    # First sighting. Emit a baseline only if there are tags;
                    # an empty baseline carries no information.
                    previous = []
                    if not current:
                        # Record the empty baseline so we do not re-evaluate the
                        # "first sighting" branch on every run, but emit nothing.
                        root_state[case_id] = {"tags": current}
                        state[root] = root_state
                        continue
                else:
                    previous = normalize_tags(known.get("tags"))
                    if current == previous:
                        # No normalized change (reorder/dup/case are no-ops).
                        continue

                added = sorted(set(current) - set(previous))
                removed = sorted(set(previous) - set(current))

                tag_event = {
                    'timestamp': datetime.now(timezone.utc).timestamp(),
                    'case_id': case_id,
                    'host': root,
                    'event_type': 'tags_changed',
                    'tags': current,
                    'tags_added': added,
                    'tags_removed': removed,
                    'previous_tags': previous,
                    'source': cases_file.as_posix(),
                }
                print(json.dumps(tag_event))

                # Update state
                root_state[case_id] = {"tags": current}
                state[root] = root_state
                stats[root] += 1

            # Logging stats
            for k, v in stats.items():
                msg = f"{v} tag changes recorded for {k}" if v > 0 else f"No tag changes for {k}"
                logging.info(msg)
            total += 1
        except Exception as e:
            logging.error(f"Failed to process cases file {cases_file}: {e}")

    logging.info(f"Total cases files processed for tags: {total}")
    # Persist state only if at least one file was processed; otherwise the root
    # path was unreachable and we must not wipe history.
    if total > 0:
        save_state(state)


if __name__ == "__main__":
    main()
