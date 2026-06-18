"""Shared helpers for Agnes AI scripts: API-key loading and setup-aware errors.

Key resolution order:
  1. `AGNES_API_KEY` environment variable
  2. config file at `~/.config/agnes-ai/api_key` (written by agnes_setup.py)

The intended flow (driven by the skill instructions, not the scripts) is: the
agent asks the user for their key ONCE, saves it with agnes_setup.py, and from
then on every script just loads it via require_api_key() below.
"""
import os
import sys

CONFIG_DIR = os.path.expanduser("~/.config/agnes-ai")
CONFIG_PATH = os.path.join(CONFIG_DIR, "api_key")
GET_KEY_URL = "https://agnes-ai.com  (developer dashboard -> Settings -> API Keys)"


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_api_key():
    """Return the API key from the env var or config file, or None if unset."""
    key = os.environ.get("AGNES_API_KEY")
    if key and key.strip():
        return key.strip()
    try:
        with open(CONFIG_PATH, "r") as f:
            key = f.read().strip()
        if key:
            return key
    except OSError:
        pass
    return None


def require_api_key():
    """Load the key or exit with a clear 'ask the user + run setup' hint."""
    key = load_api_key()
    if key:
        return key
    die(
        "Agnes API key is not configured yet.\n"
        "Ask the user for their key once (get it at " + GET_KEY_URL + "), then save it:\n"
        "    printf '%s' \"<KEY>\" | python3 <skill_dir>/scripts/agnes_setup.py\n"
        "Or check whether one is already saved:\n"
        "    python3 <skill_dir>/scripts/agnes_setup.py --check\n"
        f"The key is stored at {CONFIG_PATH} (perms 0600) and never asked again."
    )
