# Distribution and governance

Distilled from Anthropic's "Lessons from building Claude Code." Once a skill works, getting it into hands — and knowing whether it's actually used — is its own problem.

## Two distribution modes

Small teams check skills straight into the project repo under `.claude/skills/` so everyone in that repo gets them for free. As the number of skills and people grows, that bloats every workspace's context — at scale, move to a plugin marketplace so teammates install skills on demand and keep their working context lean.

## Organic, not centrally-gated

Rather than a review board approving every skill, let anyone drop a skill into a shared sandbox and self-promote it in a channel. When one proves broadly useful and gets real reuse, its author promotes it into the shared marketplace via PR. Skills earn their place through adoption, not permission.

## Measure triggering to find dead skills

A global `PreToolUse` hook can log which skills actually fire and how often — instrumentation, like product analytics. Comparing high-fire skills against near-zero-fire ones surfaces two failure modes cleanly:

- A skill that **never triggers** usually has a weak or misleading `description` — the model doesn't recognize when to use it. Run the Description Optimization loop on it.
- A skill that **triggers but gets ignored** is low practical value — a candidate for rework or retirement.

This skill can't ship the marketplace or the global hook for you, but when you package a skill here, that's the lifecycle it's entering: write it small, let it prove itself, and use triggering data to decide what to keep.
