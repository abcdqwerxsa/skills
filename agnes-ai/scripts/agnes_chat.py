#!/usr/bin/env python3
"""Call an Agnes AI text model (agnes-2.0-flash / agnes-1.5-flash).

OpenAI-compatible Chat Completions wrapper. Reads the API key from the
AGNES_API_KEY environment variable and prints the assistant's reply to stdout.

Zero third-party dependencies (stdlib only) so it runs anywhere with python3.

Examples
  agnes_chat.py "Explain attention in 3 sentences"
  agnes_chat.py "Refactor this" --system "senior python dev" --thinking
  agnes_chat.py "What is in this image" --image https://example.com/x.png
  agnes_chat.py "Return a JSON user object" --json
  echo "long prompt text" | agnes_chat.py -
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

from agnes_common import die, require_api_key

API_BASE = "https://apihub.agnes-ai.com/v1/chat/completions"
DEFAULT_MODEL = "agnes-2.0-flash"


def build_payload(args, user_text):
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})

    # Vision: attach an image_url block alongside the text instruction.
    if args.image:
        content = []
        if user_text:
            content.append({"type": "text", "text": user_text})
        for url in args.image:
            content.append({"type": "image_url", "image_url": {"url": url}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_text})

    payload = {
        "model": args.model,
        "messages": messages,
    }
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    if args.max_tokens is not None:
        payload["max_tokens"] = args.max_tokens
    if args.top_p is not None:
        payload["top_p"] = args.top_p

    # Force structured JSON output when requested.
    if args.json:
        payload["response_format"] = {"type": "json_object"}
        # Nudge the model to actually produce JSON.
        messages[0:0] = [{"role": "system",
                          "content": "Respond with valid JSON only, no markdown fences."}]

    # Thinking mode helps with coding / reasoning / multi-step agent tasks.
    if args.thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": True}

    return payload


def read_prompt(args):
    if not args.prompt:
        die("no prompt given. Pass a prompt string, or '-' to read from stdin.")
    if args.prompt == "-":
        data = sys.stdin.read().strip()
        if not data:
            die("stdin was empty")
        return data
    return args.prompt


def main():
    p = argparse.ArgumentParser(description="Call an Agnes AI text model.")
    p.add_argument("prompt", nargs="?", help="The user prompt. Use '-' to read from stdin.")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"Model name (default: {DEFAULT_MODEL}). Also: agnes-1.5-flash.")
    p.add_argument("--system", help="System prompt / persona.")
    p.add_argument("--image", action="append", default=[],
                   help="Public image URL for vision input (repeatable).")
    p.add_argument("--temperature", type=float, help="Sampling temperature.")
    p.add_argument("--top-p", type=float, help="Nucleus sampling top_p.")
    p.add_argument("--max-tokens", type=int, help="Max tokens to generate.")
    p.add_argument("--thinking", action="store_true",
                   help="Enable thinking mode (better for coding/reasoning).")
    p.add_argument("--json", action="store_true",
                   help="Force JSON object output.")
    p.add_argument("--show-usage", action="store_true",
                   help="Print token usage to stderr after the reply.")
    p.add_argument("--timeout", type=int, default=120,
                   help="HTTP timeout in seconds (default: 120).")
    args = p.parse_args()

    api_key = require_api_key()

    payload = build_payload(args, read_prompt(args))
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_BASE,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "replace")
        die(f"HTTP {e.code} from Agnes: {err_body[:500]}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        die(f"unexpected response shape: {json.dumps(data)[:500]}")

    print(content)
    if args.show_usage:
        usage = data.get("usage")
        if usage:
            print(f"\n[usage] {json.dumps(usage)}", file=sys.stderr)


if __name__ == "__main__":
    main()
