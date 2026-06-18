#!/usr/bin/env python3
"""Generate or edit an image with Agnes AI (agnes-image-2.1-flash).

Supports text-to-image and image-to-image. Saves the result to a file and
prints the path to stdout. Zero third-party dependencies (stdlib only).

Key API quirk handled here: Agnes does NOT accept `response_format` at the top
level. For text-to-image we use the top-level `return_base64: true`; for
image-to-image we put everything (input image + response_format) inside
`extra_body`.

Examples
  agnes_image.py "a neon koi fish, cinematic" -o koi.png
  agnes_image.py "a poster" --size 1024x1024 -o poster.png
  agnes_image.py "make it night, neon rain" --image https://x.com/in.png -o out.png
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

from agnes_common import die, require_api_key

API_BASE = "https://apihub.agnes-ai.com/v1/images/generations"
DEFAULT_MODEL = "agnes-image-2.1-flash"


def build_payload(args):
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
    }
    if args.image:
        # Image-to-image: input images + output format both live in extra_body.
        payload["extra_body"] = {
            "image": list(args.image),
            "response_format": "b64_json",
        }
    else:
        # Text-to-image: simplest reliable path is base64 straight back.
        payload["return_base64"] = True
    return payload


def fetch_url(url, timeout):
    # The returned image URL is a PUBLIC storage object. Sending the API's
    # Bearer token here makes the bucket return 401, so fetch it unauthenticated.
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    p = argparse.ArgumentParser(description="Generate/edit an image with Agnes AI.")
    p.add_argument("prompt", help="Text instruction for the image.")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL}).")
    p.add_argument("--size", default="1024x1024",
                   help="Output size, e.g. 1024x1024, 1024x768, 768x1024.")
    p.add_argument("--image", action="append", default=[],
                   help="Input image URL for image-to-image (repeatable).")
    p.add_argument("-o", "--output", default="agnes_image.png",
                   help="Output file path (default: agnes_image.png).")
    p.add_argument("--url", action="store_true",
                   help="Print the generated image URL instead of saving a file.")
    p.add_argument("--timeout", type=int, default=180,
                   help="HTTP timeout in seconds (default: 180).")
    args = p.parse_args()

    api_key = require_api_key()

    body = json.dumps(build_payload(args)).encode("utf-8")
    req = urllib.request.Request(
        API_BASE,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    print(f"generating image ({'img2img' if args.image else 'txt2img'}, "
          f"{args.size})...", file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "replace")
        die(f"HTTP {e.code} from Agnes: {err_body[:500]}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")

    try:
        item = data["data"][0]
    except (KeyError, IndexError):
        die(f"unexpected response shape: {json.dumps(data)[:500]}")

    img_url = item.get("url")
    b64 = item.get("b64_json")

    if img_url and not b64:
        if args.url:
            print(img_url)
            return
        print(f"downloading {img_url} ...", file=sys.stderr)
        img_bytes = fetch_url(img_url, args.timeout)
        with open(args.output, "wb") as f:
            f.write(img_bytes)
        print(os.path.abspath(args.output))
        return

    if b64:
        with open(args.output, "wb") as f:
            f.write(base64.b64decode(b64))
        print(os.path.abspath(args.output))
        return

    die(f"response had neither url nor b64_json: {json.dumps(item)[:300]}")


if __name__ == "__main__":
    main()
