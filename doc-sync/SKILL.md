---
name: doc-sync
description: Keep project usage documentation in sync after code changes. Use this whenever a git commit (or finished piece of work) ADDS a new feature, CHANGES an existing feature's behavior/mode/usage, or REMOVES a feature, and the user-facing usage docs (README, docs/, VitePress/Docusaurus sites, guides, API usage notes) may now be stale. Also use it after the user finishes/ships a feature or deletes functionality — even if they never mention "docs". Auto-triggered after `git commit` via a PostToolUse hook; also available manually as `/sync-docs`.
---

# doc-sync

Keep **usage documentation** honest after the code it describes changes.

The problem this skill exists to solve: developers ship features, change behavior, and
delete things, but the docs lag behind — so users follow instructions that no longer match
reality. This skill is the bridge: detect that a doc-relevant change happened, then propose
targeted doc edits and apply them **only after the human approves**.

Scope: **user-facing usage docs only** (README, guides, docs site, "how to use X").
Architecture / internal design docs are out of scope unless explicitly asked.

## The five-step process

Follow these in strict order. The ordering matters — each step is a gate that protects the
user's time and the docs' integrity.

### Step 1 — Triage (do this silently; do NOT ask anything yet)

The reason triage comes first and is silent: a project commits many times a day, and most
commits (refactors, tests, dep bumps, formatting) do **not** affect usage docs. Asking the
user a question for every commit would be exhausting and wrong. So classify first, talk later.

Find the change:
- If triggered right after a commit: `git show --stat HEAD` + `git log -1 --pretty=%B`.
- If invoked manually via `/sync-docs` with no clear target: check `git log -n 5 --oneline`
  and `git status`; if still unclear, ask the user *which* change they want documented.

Classify each changed file / the commit's intent:

| Change | Doc action |
|---|---|
| NEW user-facing feature added | needs doc — **add** a section |
| EXISTING feature behavior / mode / usage changed | needs doc — **update** a section |
| Feature / endpoint / file removed | needs doc — **remove** the section |
| Internal refactor, tests, dependency bumps, formatting, chore | **no doc update** |
| Bug fix with no observable behavior change | **no doc update** |
| Docs-only commit | **no doc update** |

Decision:
- If nothing needs a doc update → reply **one line**: `✓ 无需更新文档：<one-clause reason>`
  and STOP. Do not proceed to Step 2.
- Otherwise → go to Step 2.

### Step 2 — Ask for the doc path (every time)

Ask the user directly: **「项目文档路径是哪个?」**. Ask this on every invocation — the user
wants to confirm the target each run rather than trust a cached path.

Accept a single file (`README.md`) or a directory (`docs/`, `docs-site/docs/`). If they give
a directory, you'll need to figure out which file inside is relevant in Step 3.

### Step 3 — Locate the relevant section(s)

Read the doc(s) at the path the user gave. Find the section(s) that correspond to the changed
feature (by heading, by topic, by command/endpoint name).

- If a matching section exists → note it for editing.
- If none exists → flag `需新增小节` and pick a sensible place to insert one.

### Step 4 — Propose the edits (do NOT write to disk yet)

Show concrete, reviewable proposed changes — `before/after` blocks or diff-style — for each
section you intend to touch. For each, one line on **what** changes and **why** it follows
from the code change.

Then explicitly ask for a decision: **「确认 / 调整 / 取消」**.

The reason for this gate: usage docs are the contract between the project and its users.
Wrong instructions mislead real people, so a human signs off before anything is written. Do
not call `Edit`/`Write` until you receive an explicit "确认".

### Step 5 — Apply on approval

Only after explicit confirmation, apply the approved edits with `Edit`/`Write`.

Then report in **one line** what you changed: `✓ 已更新 <file> — <section>`. Done.

## Notes & edge cases

- **Large commits** (many features at once): summarize the changes, then ask the user which
  parts they want documented rather than silently editing many sections.
- **Multiple doc-relevant changes**: propose all of them together in Step 4 so the user can
  approve/adjust/cancel in one pass.
- **User cancels at any step**: stop immediately. No partial edits.
- **Path points to a doc that doesn't exist**: report it, ask whether to create it.
- Never broaden scope to architecture/internal docs unless the user explicitly asks.
