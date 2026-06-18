#!/usr/bin/env python3
"""One-time setup: save or check the Agnes AI API key.

The key is read from stdin by default so it never lands in shell history.

  # save a key (pipe it in — recommended)
  printf '%s' "$KEY" | python3 agnes_setup.py

  # ...or pass it explicitly
  python3 agnes_setup.py --key "sk-..."

  # check whether a key is already configured (never prints the key itself)
  python3 agnes_setup.py --check
"""
import argparse
import os
import sys

from agnes_common import CONFIG_DIR, CONFIG_PATH, load_api_key, die


def main():
    p = argparse.ArgumentParser(description="Save or check the Agnes AI API key.")
    p.add_argument("--check", action="store_true",
                   help="Only report whether a key is configured (exit 0 if set, 1 if not). "
                        "Never prints the key.")
    p.add_argument("--key", help="API key (prefer stdin to avoid shell history).")
    args = p.parse_args()

    if args.check:
        if load_api_key():
            print(f"OK: Agnes API key is configured ({CONFIG_PATH}).")
            return
        print(f"NOT SET: no key at {CONFIG_PATH} and AGNES_API_KEY is empty.", file=sys.stderr)
        sys.exit(1)

    key = args.key if args.key is not None else sys.stdin.read()
    key = key.strip()
    if not key:
        die("no key provided — pass it via --key or pipe it through stdin.")

    os.makedirs(CONFIG_DIR, exist_ok=True)
    # Create/rewrite with 0600 perms (secrets file).
    old_umask = os.umask(0o077)
    try:
        with open(CONFIG_PATH, "w") as f:
            f.write(key)
    finally:
        os.umask(old_umask)
    os.chmod(CONFIG_PATH, 0o600)

    print(f"Saved Agnes API key to {CONFIG_PATH} (perms 0600).")
    print("Run agnes_chat.py / agnes_image.py / agnes_video.py now — no re-entry needed.")


if __name__ == "__main__":
    main()
