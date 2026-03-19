# Implementation Plan: Task 1 (Call an LLM from Code)

## Goal
Build a minimal Python CLI (`agent.py`) that:
1. Accepts a `question` as the first command-line argument.
2. Calls an OpenAI-compatible chat-completions endpoint on a configured LLM provider.
3. Prints **exactly one** JSON line to stdout:
   `{"answer": "...", "tool_calls": []}`
4. Sends any debug/progress output to stderr only.

## LLM Provider Choice
- Provider: **Qwen Code** (recommended) using the **OpenAI-compatible** proxy endpoint.
- Model: configured by `LLM_MODEL` (example: `qwen3-coder-plus`).
- API base URL: configured by `LLM_API_BASE` and assumed to already include `/v1`.

## Environment Variables (must not be hardcoded)
The agent will read these from `os.environ`:
- `LLM_API_KEY` (API key)
- `LLM_API_BASE` (endpoint base URL, typically ending in `/v1`)
- `LLM_MODEL` (model name)

If the env vars are not set locally, the agent will optionally load them from `.env.agent.secret` as a convenience, but the evaluation system will inject values via environment variables.

## Data Flow
1. Parse `question = sys.argv[1]`.
2. Load LLM configuration from environment variables.
3. Construct a chat-completions request:
   - `model = LLM_MODEL`
   - `messages = [{"role":"system","content":"You are a helpful assistant."}, {"role":"user","content":question}]`
   - No tool/function calling yet (this task always returns `tool_calls: []`).
4. Call `POST {LLM_API_BASE}/chat/completions` (endpoint assembled from base + `/chat/completions`).
5. Extract the final assistant text from `choices[0].message.content`.
6. Print JSON:
   - `answer`: extracted text (stripped)
   - `tool_calls`: always `[]`
7. Exit with code `0` on success.

## Failure Handling
- If config is missing, the agent will run in a deterministic "dry-run" mode for local development/testing and still output valid JSON with the required fields.
- If the HTTP call fails, the agent will still output valid JSON (with possibly an empty `answer`) and write error details to stderr.

## Regression Test Strategy
Add one pytest regression test that:
1. Runs `agent.py` as a subprocess.
2. Forces dry-run mode (so tests don’t require real LLM credentials).
3. Parses stdout as JSON.
4. Asserts the presence of `answer` and `tool_calls` and that `tool_calls == []`.

