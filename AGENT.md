# Agent Architecture (Task 1)

## What `agent.py` does
`agent.py` is a command-line program that takes a user question and calls an OpenAI-compatible chat-completions endpoint.

It prints **one** JSON line to stdout:
`{"answer": "...", "tool_calls": []}`

Any debug/progress output is sent to stderr so stdout stays machine-readable.

## LLM configuration (env-driven)
The agent does not hardcode any LLM credentials or model details. It reads:

- `LLM_API_KEY`
- `LLM_API_BASE`
- `LLM_MODEL`

These are expected to be present in the environment when the autochecker evaluates your agent.

For local convenience, if any of the above keys are missing, `agent.py` will also try to load them from `.env.agent.secret` using a small `KEY=VALUE` parser (but it will never hardcode provider values itself).

## Request details
The agent sends a `POST` request to:
`{LLM_API_BASE}/chat/completions`

Payload:
- `model`: `LLM_MODEL`
- `messages`: a minimal system prompt plus the user question
- `temperature`: `0.2`

The agent extracts the final assistant text from `choices[0].message.content`.

## Dry-run mode (tests only)
For development/testing (and to keep regression tests offline), if `AGENT_DRY_RUN=1` is set, the agent skips the network call and returns a deterministic placeholder answer while still outputting valid JSON with `tool_calls: []`.

