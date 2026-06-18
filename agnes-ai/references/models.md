# Agnes AI — full API reference

Use this when the bundled scripts don't expose what you need (streaming in a
pipeline, multi-turn history, raw tool-calling loops, calling from inside a
program). Base URL for everything: `https://apihub.agnes-ai.com`. Auth header on
every request: `Authorization: Bearer $AGNES_API_KEY`.

**Key setup:** the agent should ask the user for their key once and save it with
`python3 scripts/agnes_setup.py` (stdin). The key is then read automatically from
the env var `AGNES_API_KEY` or `~/.config/agnes-ai/api_key`. See SKILL.md for the
full ask-once flow.

## Table of contents
1. [Text models (chat completions)](#1-text-models-chat-completions)
2. [Image models](#2-image-models)
3. [Video model](#3-video-model)
4. [Error codes](#4-error-codes)

---

## 1. Text models (chat completions)

Endpoint: `POST /v1/chat/completions` · Content-Type: `application/json` · OpenAI-compatible.

Models: **`agnes-2.0-flash`** (default — chat, coding, agents, reasoning, vision,
256K context / 65.5K max output), **`agnes-1.5-flash`** (lightweight, low latency).

### Request parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `model` | string | yes | `agnes-2.0-flash` or `agnes-1.5-flash` |
| `messages` | array | yes | `system` / `user` / `assistant` messages |
| `messages[].content` | string \| array | yes | Plain text, or array of `text` + `image_url` blocks |
| `temperature` | number | no | Randomness; lower = more deterministic |
| `top_p` | number | no | Nucleus sampling |
| `max_tokens` | number | no | Max generated tokens |
| `stream` | boolean | no | Stream tokens via SSE |
| `tools` | array | no | Tool/function definitions for tool-calling |
| `tool_choice` | string \| object | no | Control tool usage |
| `chat_template_kwargs` | object | no | `{"enable_thinking": true}` — thinking mode (OpenAI format) |
| `thinking` | object | no | `{"type":"enabled","budget_tokens":2048}` — thinking mode (Anthropic format) |

### Response

```json
{
  "id": "chatcmpl_xxx",
  "object": "chat.completion",
  "created": 1774432125,
  "model": "agnes-2.0-flash",
  "choices": [
    { "index": 0,
      "message": { "role": "assistant", "content": "..." },
      "finish_reason": "stop" }
  ],
  "usage": { "prompt_tokens": 35, "completion_tokens": 58, "total_tokens": 93 }
}
```

The assistant text is at `choices[0].message.content`.

### Minimal curl

```bash
curl https://apihub.agnes-ai.com/v1/chat/completions \
  -H "Authorization: Bearer $AGNES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"agnes-2.0-flash",
       "messages":[{"role":"user","content":"Hello!"}]}'
```

### Vision (image_url input)

`messages[].content` becomes an array of blocks. Image must be a public URL.

```json
{ "role": "user", "content": [
  { "type": "text", "text": "Describe this image." },
  { "type": "image_url", "image_url": { "url": "https://example.com/x.jpg" } }
]}
```

### Streaming

Set `"stream": true`. Response is a stream of SSE `data: {...}` chunks; each
chunk's token is at `choices[0].delta.content`. Terminate on `data: [DONE]`.

### Tool calling

Pass `tools` (OpenAI function-calling schema). The model returns
`choices[0].message.tool_calls`; run the tool, append the result as a
`{role:"tool","tool_call_id":...,"content":...}` message, and call again.

### Thinking mode (coding / reasoning / agents)

```json
{ "model": "agnes-2.0-flash", "messages": [...],
  "chat_template_kwargs": { "enable_thinking": true } }
```

For complex debugging/refactoring/multi-step agent tasks, raise the budget
accordingly (the OpenAI-format flag has no explicit budget; the Anthropic-format
`thinking.budget_tokens` field does — start at `2048`).

---

## 2. Image models

Endpoint: `POST /v1/images/generations` · Content-Type: `application/json`.

Models: **`agnes-image-2.1-flash`** (recommended — text-to-image + image-to-image,
high detail), **`agnes-image-2.0-flash`** (older).

### Request parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `model` | string | yes | `agnes-image-2.1-flash` |
| `prompt` | string | yes | Image instruction |
| `size` | string | yes | e.g. `1024x1024`, `1024x768` |
| `return_base64` | boolean | no | Text-to-image base64 output |
| `extra_body` | object | no | Holds `response_format` and img2img `image` |
| `extra_body.response_format` | string | no | `"url"` or `"b64_json"` |
| `extra_body.image` | string[] | no | Input images for img2img (public URL or `data:` URI) |

### Critical quirks (these bite people)

- **Never put `response_format` at the top level.** It goes inside `extra_body`.
  (For text-to-image base64 you can instead use top-level `return_base64: true`.)
- **Image-to-image does NOT use `tags: ["img2img"]`.** Just supply `image` in
  `extra_body`. Don't pass `tags` at all.
- For img2img, the input image goes in `extra_body.image` (an array), not at the
  top level.

### Text-to-image → base64

```bash
curl https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer $AGNES_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"agnes-image-2.1-flash","prompt":"a luminous floating city at sunrise",
       "size":"1024x768","return_base64":true}'
```

### Text-to-image → URL

```json
{ "model":"agnes-image-2.1-flash","prompt":"...","size":"1024x768",
  "extra_body":{"response_format":"url"} }
```

### Image-to-image (URL in, URL out)

```json
{ "model":"agnes-image-2.1-flash","prompt":"make it a rainy neon night, keep composition",
  "size":"1024x768",
  "extra_body":{ "image":["https://example.com/in.png"], "response_format":"url" } }
```

`data:image/png;base64,...` URIs are also accepted in `extra_body.image`.

### Response

```json
{ "created": 1780000000,
  "data": [{ "url": "https://storage.googleapis.com/agnes-aigc/xxx.png",
             "b64_json": null, "revised_prompt": null }] }
```

Read `data[0].url` or `data[0].b64_json` depending on the requested format.

### Prompt structure that works well

`[Subject] + [Scene/Environment] + [Style] + [Lighting] + [Composition] + [Quality]`

For img2img, state both the change AND what to preserve:
`"Transform into a cyberpunk night with neon reflections while preserving the
original composition and subject layout."`

Image generation can take several to tens of seconds; use a 60–360s client timeout.

---

## 3. Video model

**Async task API.** Create a task, poll until `completed`, then fetch the mp4.

Model: **`agnes-video-v2.0`** (supports text-to-video, image-to-video,
multi-image, keyframe animation).

### Endpoints

| Purpose | Method | URL |
|---|---|---|
| Create task | POST | `https://apihub.agnes-ai.com/v1/videos` |
| Retrieve (recommended) | GET | `https://apihub.agnes-ai.com/agnesapi?video_id=<VIDEO_ID>` |
| Retrieve (legacy) | GET | `https://apihub.agnes-ai.com/v1/videos/<TASK_ID>` |

You can add `&model_name=agnes-video-v2.0` to the recommended retrieve URL.

### Create-task parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `model` | string | yes | `agnes-video-v2.0` |
| `prompt` | string | yes | Video description |
| `image` | string \| array | no | Single URL (img2vid) — use top-level for one, `extra_body.image` array for many |
| `extra_body.image` | array | no | Multiple image URLs (multi-image / keyframe) |
| `extra_body.mode` | string | no | `"keyframes"` for keyframe animation |
| `width` / `height` | int | no | Default 1152 × 768. Snapped to nearest of 480p/720p/1080p tier |
| `num_frames` | int | no | **≤ 441, must be `8n+1`** (81, 121, 161, 241, 441) |
| `frame_rate` | number | no | 1–60, default 24 |
| `negative_prompt` | string | no | Content to avoid |
| `seed` | int | no | For reproducibility |
| `num_inference_steps` | int | no | Inference steps |

### Duration cheat-sheet (`seconds = num_frames / frame_rate`, at fps 24)

| Target | num_frames |
|---|---|
| ~3s | 81 |
| ~5s | 121 (default) |
| ~10s | 241 |
| ~18s | 441 (max) |

Recommended aspect ratios: `16:9` (landscape/YouTube), `9:16` (vertical/TikTok),
`1:1`, `4:3`, `3:4`. Note the server standardizes width/height to a supported
tier, so the returned `size`/`seconds` may differ slightly from your request —
trust the response fields.

### Create task → response

```json
{ "id": "task_...", "task_id": "task_...",
  "video_id": "video_...",            // <-- use this to retrieve
  "object": "video", "model": "agnes-video-v2.0",
  "status": "queued", "progress": 0,
  "created_at": 1780457477, "seconds": "10.0", "size": "1280x768" }
```

### Poll → completed response

```json
{ "video_id": "video_...", "status": "completed", "progress": 100,
  "seconds": "10.0", "size": "1280x768",
  "remixed_from_video_id": "https://storage.googleapis.com/agnes-aigc/.../video_xxx.mp4",
  "error": null }
```

The final mp4 URL is in **`remixed_from_video_id`** when `status == "completed"`.
(The docs sometimes call it `video_url`; check both.)

### Task statuses

`queued` → `in_progress` → `completed` (or `failed`).

### Prompt structure

`[Subject] + [Action] + [Scene] + [Camera movement] + [Lighting] + [Style]`

For img2vid, describe the motion and what should stay stable; for multi-image,
describe the relationship/transition between the inputs.

---

## 4. Error codes

| Status | Meaning |
|---|---|
| 400 | Invalid request — check parameters |
| 401 | Unauthorized — bad/missing API key |
| 404 | Task/video not found |
| 500 | Server error |
| 503 | Service busy — retry later |

The bundled scripts surface the HTTP code and a snippet of the error body on
stderr and exit non-zero, so failures are easy to diagnose in a shell loop.
