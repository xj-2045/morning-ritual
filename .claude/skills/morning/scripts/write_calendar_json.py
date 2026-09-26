#!/usr/bin/env python3
"""Write .tmp/calendar.json from the raw Google Calendar MCP list_events response.

Why this exists: previously the /morning ritual required hand-retyping every
calendar event into a Python heredoc to produce .tmp/calendar.json — error-prone
(one typo and the board shows wrong data). This script accepts the raw MCP
response (or a bare events array) and writes the clean array the HTML generator
expects.

Usage (pipe the raw list_events JSON on stdin):
    pbpaste | python3 .claude/skills/morning/scripts/write_calendar_json.py
    python3 .claude/skills/morning/scripts/write_calendar_json.py < raw_response.json

Accepts either:
  - the full MCP object: {"events": [...], ...}
  - a bare list of event objects: [...]
"""
import json
import sys
from pathlib import Path

# .tmp lives at the workspace root (two levels up from scripts/ -> skills/morning,
# then up to .claude, then to workspace root). Resolve relative to this file so the
# script is portable regardless of the current working directory.
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
OUT_PATH = WORKSPACE_ROOT / ".tmp" / "calendar.json"


def extract_events(payload):
    """Return the events list from either a full MCP object or a bare array."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        events = payload.get("events")
        if isinstance(events, list):
            return events
        raise ValueError("JSON object has no 'events' array")
    raise ValueError(f"Unexpected JSON top-level type: {type(payload).__name__}")


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit("No input received on stdin. Pipe the list_events JSON in.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"Could not parse stdin as JSON: {exc}")

    events = extract_events(payload)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(events, indent=2))
    print(f"calendar.json written — {len(events)} events → {OUT_PATH}")


if __name__ == "__main__":
    main()
