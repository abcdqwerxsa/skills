#!/usr/bin/env python3
"""Generate a video with Agnes AI (agnes-video-v2.0).

Agnes video generation is ASYNCHRONOUS: this script submits a task, polls until
it finishes, then downloads the .mp4. Zero third-party dependencies (stdlib only).

Supports text-to-video, image-to-video, multi-image, and keyframe animation.
num_frames must follow the 8n+1 rule (81, 121, 161, 241, 441); seconds =
num_frames / frame_rate.

Examples
  agnes_video.py "a cat walking on a beach at sunset" -o cat.mp4
  agnes_video.py "the woman turns to camera" --image https://x.com/in.png -o out.mp4
  agnes_video.py "morph scene A into scene B" --image https://a.png https://b.png -o out.mp4
  agnes_video.py "smooth keyframe transition" --keyframes https://a.png https://b.png -o out.mp4
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

from agnes_common import die, require_api_key

CREATE_URL = "https://apihub.agnes-ai.com/v1/videos"
POLL_URL = "https://apihub.agnes-ai.com/agnesapi?video_id={vid}"
POLL_LEGACY_URL = "https://apihub.agnes-ai.com/v1/videos/{tid}"
DEFAULT_MODEL = "agnes-video-v2.0"


def build_payload(args):
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "num_frames": args.frames,
        "frame_rate": args.fps,
    }
    if args.width and args.height:
        payload["width"] = args.width
        payload["height"] = args.height
    if args.negative_prompt:
        payload["negative_prompt"] = args.negative_prompt
    if args.seed is not None:
        payload["seed"] = args.seed

    if args.keyframes:
        payload["extra_body"] = {"image": list(args.keyframes), "mode": "keyframes"}
    elif args.image:
        # Single URL -> top-level `image`; multiple URLs -> extra_body.image array.
        if len(args.image) == 1:
            payload["image"] = args.image[0]
        else:
            payload["extra_body"] = {"image": list(args.image)}
    return payload


def api_request(url, api_key, method="GET", body=None, timeout=120):
    data = None
    headers = {"Authorization": f"Bearer {api_key}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "replace")
        die(f"HTTP {e.code} from Agnes: {err_body[:500]}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")


def extract_video_url(result):
    """The docs are inconsistent about which field holds the final URL.
    Check the known field plus a couple of fallbacks so we're robust."""
    for key in ("remixed_from_video_id", "video_url", "url"):
        val = result.get(key)
        if isinstance(val, str) and val.lower().endswith(".mp4"):
            return val
    # Some responses nest the URL under a video object.
    vid = result.get("video")
    if isinstance(vid, dict):
        for key in ("url", "video_url", "remixed_from_video_id"):
            val = vid.get(key)
            if isinstance(val, str) and val.lower().endswith(".mp4"):
                return val
    return None


def main():
    p = argparse.ArgumentParser(description="Generate a video with Agnes AI.")
    p.add_argument("prompt", help="Description of the desired video.")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL}).")
    p.add_argument("--image", action="append", default=[],
                   help="Image URL for image-to-video (repeatable for multi-image).")
    p.add_argument("--keyframes", action="append", default=[],
                   help="Keyframe image URLs for keyframe animation (repeatable).")
    p.add_argument("--frames", type=int, default=121,
                   help="num_frames, 8n+1 rule: 81/121/161/241/441 (default 121 ~5s).")
    p.add_argument("--fps", type=float, default=24, help="Frame rate 1-60 (default 24).")
    p.add_argument("--width", type=int, help="Video width (e.g. 1152).")
    p.add_argument("--height", type=int, help="Video height (e.g. 768).")
    p.add_argument("--negative-prompt", help="Describe content to avoid.")
    p.add_argument("--seed", type=int, help="Random seed for reproducibility.")
    p.add_argument("-o", "--output", default="agnes_video.mp4",
                   help="Output file path (default: agnes_video.mp4).")
    p.add_argument("--poll-interval", type=int, default=10,
                   help="Seconds between status polls (default 10).")
    p.add_argument("--max-wait", type=int, default=1200,
                   help="Give up after this many seconds (default 1200).")
    args = p.parse_args()

    # Validate the 8n+1 rule early so we fail fast with a helpful message.
    if (args.frames - 1) % 8 != 0 or args.frames < 9:
        die(f"num_frames must follow the 8n+1 rule (9, 17, ..., 81, 121, 161, 241, 441). "
            f"Got {args.frames}.")

    api_key = require_api_key()

    payload = build_payload(args)
    print(f"submitting video task ({args.frames} frames @ {args.fps} fps "
          f"= ~{args.frames / args.fps:.1f}s)...", file=sys.stderr)
    created = api_request(CREATE_URL, api_key, method="POST", body=payload)

    video_id = created.get("video_id")
    task_id = created.get("task_id") or created.get("id")
    if not video_id and not task_id:
        die(f"task created but no video_id/task_id returned: {json.dumps(created)[:400]}")
    print(f"task submitted. video_id={video_id} task_id={task_id}", file=sys.stderr)

    start = time.monotonic()
    last_status = None
    while True:
        if time.monotonic() - start > args.max_wait:
            die(f"timed out after {args.max_wait}s while status={last_status}. "
                f"video_id={video_id} — re-run / poll manually later.")

        time.sleep(args.poll_interval)
        if video_id:
            result = api_request(POLL_URL.format(vid=video_id), api_key)
        else:
            result = api_request(POLL_LEGACY_URL.format(tid=task_id), api_key)

        status = result.get("status", last_status)
        progress = result.get("progress")
        if status != last_status or progress is not None:
            print(f"  status={status} progress={progress}", file=sys.stderr)
            last_status = status

        if status == "failed":
            die(f"video generation failed: {json.dumps(result.get('error'))[:300]}")
        if status == "completed":
            video_url = extract_video_url(result)
            if not video_url:
                die(f"completed but no .mp4 URL found in response: {json.dumps(result)[:500]}")
            print(f"downloading video...", file=sys.stderr)
            req = urllib.request.Request(video_url)
            with urllib.request.urlopen(req, timeout=300) as r:
                blob = r.read()
            with open(args.output, "wb") as f:
                f.write(blob)
            print(os.path.abspath(args.output))
            return


if __name__ == "__main__":
    main()
