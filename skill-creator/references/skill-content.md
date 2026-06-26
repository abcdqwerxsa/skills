# High-value content: what to actually put in the skill

Distilled from Anthropic's "Lessons from building Claude Code." A skill folder's *shape* matters, but so does its *substance*. The highest-value content concentrates in five patterns — bake them in as you draft.

## 1. Don't restate what the model already knows

The model is already a strong general programmer with good code-search instincts — a skill that "teaches Python loops" is dead weight that just crowds the context. Spend your tokens on what the model *can't* infer: counter-intuitive internal conventions, non-obvious architecture constraints, hidden bugs. If a line would be true for any competent engineer reading the public docs, cut it.

## 2. Build a dense Gotchas/Pitfalls section — and keep feeding it

The single most valuable part of most skills is the gotchas: the places real agents (and humans) got burned. Treat errors during your eval runs as raw material — when a test run trips on something non-obvious, distill the trap into a one-line anti-example and add it to the skill. Good gotchas are concrete and irreducible:

> The subscriptions table is append-only. The row you want is the one with the max `version`, not the most recent `created_at`.
> The API gateway calls this field `@request_id`, but the billing service calls it `trace_id`. Same value — map it.

## 3. Make config self-initializing, never hardcoded

If the skill depends on a parameter (a Slack channel, a project ID, a region), don't bake the value — and never a secret — into the SKILL.md or a script. Drop a `config.json` placeholder in the skill directory and have the agent notice when it's missing and ask the user to fill it interactively. Secrets belong in environment variables or a secrets store, not in committed skill text.

## 4. Give the agent persistent memory across runs

For skills that run repeatedly (standups, rollups, oncall checks), let the agent keep a small log/state file so it can compare against last time — "what did I already report yesterday?" — instead of redoing work from scratch. Write this state to `${CLAUDE_PLUGIN_DATA}` (the skill/plugin's writable data path), not the skill's own source directory, so installed skills stay read-only and upgrades don't clobber logs.

## 5. Mount session-scoped hooks for safety-sensitive skills

For skills that touch destructive or production-critical operations, you can attach a `PreToolUse` hook that only lives while the skill is active — e.g. pause and demand confirmation when a command matches `rm -rf`, `DROP TABLE`, or a force-push to a production branch; or block edits to files outside a frozen scope while debugging. These hooks auto-unload when the skill ends, so they don't bleed into everyday work. Hook authoring is environment-specific, so check your runtime's hook docs rather than inventing a format here.
