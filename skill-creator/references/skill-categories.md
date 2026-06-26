# Skill categories: what kind of skill is this?

Distilled from Anthropic's "Lessons from building Claude Code." The category of skill you're building shapes what content matters most — high-value skills cluster into a few recognizable types.

## The nine categories

- **Library & API reference** — how to correctly call a specific library/CLI/SDK, especially internal ones or public ones with trapdoor edge cases. Core content = code snippets + gotchas.
- **Product verification** — how to test that a code change actually works (Playwright, tmux, smoke flows with an assertion at each step). *This category has the largest impact on agent output quality — when you're unsure where to invest polish, invest here.*
- **Data fetching & analysis** — wire the agent into monitoring/analytics stacks (authenticated query tools, dashboard IDs, canonical SQL/workflows).
- **Business process automation** — collapse a repeating team workflow into one instruction; usually keeps a log so the agent can reason across runs.
- **Scaffolding & templates** — generate boilerplate that conforms to org conventions, with natural-language conditionals.
- **Code quality & review** — enforce style/test norms; often spawns an adversarial reviewer subagent.
- **CI/CD & deployment** — packaging, canary/release, smoke-after-deploy, auto-rollback on regression.
- **Troubleshooting runbooks** — feed in an alert/symptom, correlate metrics + topology + history, output a structured diagnosis.
- **Infrastructure operations** — routine maintenance; for destructive tasks, bake in strict guardrails and explicit confirmation.

## Two practical notes

1. **Verification skills punch above their weight** — they're worth disproportionate effort. If you're choosing where to polish deeply, a skill that closes the loop on "does my change actually work" pays back the most.
2. **A skill that spans several categories tends to confuse triggering** — "everything for X" skills usually undertrigger because the model can't tell when they apply. Aim for a single, sharp category, and split the skill if the scope sprawls.
