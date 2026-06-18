---
name: agnes-ai
description: Call the Agnes AI free multimodal API (text, image, video) via ready-to-run scripts. Use this whenever the user wants to use Agnes, get a free/no-cost AI API, run chat/code/agent/reasoning/vision tasks on a free model, or generate images or videos for free — e.g. "use a free LLM", "generate an image for free", "make a video with Agnes", "call agnes-2.0-flash", or any request to use Agnes's models. Agnes (by Sapiens AI) is OpenAI-compatible and currently offers free text, image, and video generation. Invoke this skill before writing any curl/HTTP calls to agnes-ai.com so you use the bundled, tested scripts instead.
---

# agnes-ai

Call Agnes AI's **free** multimodal models (text, image, video) from the command
line. Agnes is OpenAI-compatible, so the text endpoint works as a drop-in, and
all three modalities are free during the current access period.

This skill bundles three zero-dependency Python scripts that handle auth,
request shaping, and the awkward parts of the Agnes API (image `response_format`
placement, video's async task + `8n+1` frame rule). **Prefer running these
scripts over hand-writing curl** — they encode the gotchas for you.

Scripts are stdlib-only: run them with plain `python3` (no install step).

## First-time setup — ASK the user for their API key ONCE

Before calling any Agnes endpoint, make sure a key is configured. It persists at
`~/.config/agnes-ai/api_key` (0600 perms), so this only happens **once per
machine** — never pester the user for the key on later runs.

1. Silently check whether a key is already configured:
   ```bash
   python3 <skill_dir>/scripts/agnes_setup.py --check
   ```
   Exit code 0 = a key is set → skip to "Quick start" without bothering the user.

2. If it reports **NOT SET**, you MUST **ask the user** for their Agnes API key.
   Do not invent, guess, or proceed without one. Tell them where to get it:
   https://agnes-ai.com → **Settings → API Keys → Create new secret key**.

3. Once the user gives you the key, save it — pipe it through stdin so it never
   lands in shell history:
   ```bash
   printf '%s' "<THE_KEY_THE_USER_GAVE_YOU>" | python3 <skill_dir>/scripts/agnes_setup.py
   ```

4. Re-run `--check` to confirm, then proceed to the scripts below.

Every script loads the key automatically (env var `AGNES_API_KEY` first, then the
config file) — so after setup you never ask again. Power users may alternatively
just `export AGNES_API_KEY=...` and skip the config file.

The scripts live in the `scripts/` subfolder of this skill's directory. In the
examples below, **`<skill_dir>`** means this skill's own directory (the harness
tells you the base path when the skill loads — e.g. `/root/skills/agnes-ai`). If
you're unsure of the exact path, find it with:
`find / -name agnes_chat.py -path '*agnes-ai*' 2>/dev/null`

## Quick start — pick the modality

### 1. Text / chat / coding / vision — `agnes-2.0-flash`

The general-purpose model: chat, multi-turn, coding, reasoning, agent/tool-calling,
and image understanding (256K context, 65.5K max output). Free.

```bash
# plain Q&A
python3 <skill_dir>/scripts/agnes_chat.py "Explain RAG in three sentences"

# persona + thinking mode (better for coding / multi-step reasoning)
python3 <skill_dir>/scripts/agnes_chat.py "Refactor this function for readability" \
  --system "senior python engineer" --thinking

# vision: pass a public image URL
python3 <skill_dir>/scripts/agnes_chat.py "What UI element is broken here?" \
  --image https://example.com/screenshot.png

# structured output
python3 <skill_dir>/scripts/agnes_chat.py "Return a JSON user profile for a fictional user" --json

# long prompt via stdin
echo "$(cat big_context.txt)" | python3 <skill_dir>/scripts/agnes_chat.py - --system "summarize"
```

The script prints **only** the assistant's reply to stdout (so it's easy to
capture into a variable or file). Flags: `--model agnes-1.5-flash` (lighter,
lower latency), `--system`, `--image` (repeatable), `--temperature`, `--top-p`,
`--max-tokens`, `--thinking`, `--json`, `--show-usage`. Run `--help` for the
full list.

### 2. Image generation / editing — `agnes-image-2.1-flash`

Text-to-image and image-to-image. Saves a PNG to disk and prints the absolute path.

```bash
# text-to-image
python3 <skill_dir>/scripts/agnes_image.py "a neon koi fish, cinematic realism" -o koi.png

# different aspect ratio
python3 <skill_dir>/scripts/agnes_image.py "wide cyberpunk skyline" --size 1024x768 -o city.png

# image-to-image (transform an existing image)
python3 <skill_dir>/scripts/agnes_image.py "turn it into a rainy neon night, keep composition" \
  --image https://example.com/input.png -o out.png
```

Flags: `--size` (default `1024x1024`; also `1024x768`, `768x1024`), `--image`
(repeatable, for img2img), `-o/--output`, `--url` (print URL instead of saving).

### 3. Video generation — `agnes-video-v2.0`

Async: the script submits a task, polls until completion, then downloads the
`.mp4`. Supports text-to-video, image-to-video, multi-image, and keyframe
animation. Free.

```bash
# text-to-video (~5s by default)
python3 <skill_dir>/scripts/agnes_video.py "a cat walking on a beach at sunset, golden light" -o cat.mp4

# image-to-video (animate one image)
python3 <skill_dir>/scripts/agnes_video.py "the woman slowly turns to the camera" \
  --image https://example.com/pic.png -o out.mp4

# keyframe animation (smooth transition between two frames)
python3 <skill_dir>/scripts/agnes_video.py "smooth cinematic transition" \
  --keyframes https://example.com/kf1.png https://example.com/kf2.png -o out.mp4
```

Duration = `num_frames / frame_rate`. `num_frames` **must** follow the `8n+1`
rule (valid: 81, 121, 161, 241, 441). The script validates this and fails fast
with a clear message. `--frames 121 --fps 24` ≈ 5s; see the reference doc for
the full duration table. Video generation can take minutes — the script polls
every 10s (override with `--poll-interval`) and gives up after 20 min
(`--max-wait`).

## Choosing a model

| Need | Model | Notes |
|---|---|---|
| Chat, coding, agents, reasoning, vision | `agnes-2.0-flash` | Default. 256K ctx, 65.5K out. Tool-calling + streaming supported. |
| Light/cheap/fast text | `agnes-1.5-flash` | Lower latency, lighter weight. |
| Image gen or edit | `agnes-image-2.1-flash` | Text-to-image + image-to-image. (2.0-flash also exists.) |
| Video | `agnes-video-v2.0` | Async task API. |

## When the scripts aren't enough

If the user needs something the CLI flags don't expose — streaming tokens in a
pipeline, multi-turn message history, raw tool-calling loops, or calling from
inside another program — read `references/models.md`. It has the full endpoint
reference, all request parameters, response shapes, and copy-paste curl for
text / image / video so you can call the API directly. Use raw HTTP only when
the scripts genuinely can't express what you need.

## Gotchas worth remembering

- **Image `response_format` must NOT be top-level.** Text-to-image uses
  top-level `return_base64: true`; image-to-image puts both the input `image`
  array and `response_format` inside `extra_body`. The script handles this.
- **Video is asynchronous.** Always create a task, then poll. New integrations
  should retrieve via `video_id` (`GET /agnesapi?video_id=...`), not the legacy
  `/v1/videos/{task_id}`.
- **Video `num_frames` follows `8n+1`** and must be ≤ 441. The script enforces this.
- **Vision needs a *publicly accessible* URL** — no login/cookies/hotlink protection,
  or the model can't read it. Standard JPG/PNG/WebP only.
- **Image URLs for img2img / video must also be public.** If a local file must be
  used, host it (or base64-encode it for image img2img via a `data:` URI).
- All endpoints are under `https://apihub.agnes-ai.com`.
