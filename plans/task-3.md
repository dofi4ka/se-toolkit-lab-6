# Implementation Plan: Task 3 (System Agent)

## Objective
Extend the Task 2 documentation agent so it can query the running backend API through a new `query_api` tool while keeping the same function-calling loop.

## Required additions
1. Add `query_api` function schema to LLM tool definitions.
2. Implement local `query_api` executor in `agent.py`:
   - reads `LMS_API_KEY` from environment variables (fallback: `.env.docker.secret` for local runs),
   - reads `AGENT_API_BASE_URL` from environment variables, defaulting to `http://localhost:42002`,
   - sends `Authorization: Bearer <LMS_API_KEY>`,
   - returns JSON string with `status_code` and `body`.
3. Update system prompt so model chooses:
   - `read_file`/`list_files` for wiki/source questions,
   - `query_api` for runtime/data/status questions.
4. Keep loop limit at 10 tool calls and preserve tool call logs.

## Path and API safety
- Keep existing path traversal protection for file tools (no escaping repository root).
- For `query_api`, require a relative API path (e.g., `/items/`) and always combine with `AGENT_API_BASE_URL` to avoid arbitrary host access.

## Benchmark baseline and diagnosis
Initial benchmark run (`uv run run_eval.py`):
- Score: **3/10**
- First failure: question about listing API router modules.
- Observed issue: model produced no final answer after tool usage for that question.

## Iteration strategy
1. Improve system prompt with explicit tool-selection rules and answer formatting.
2. Add robust fallback when loop ends without final answer (ask model for final synthesis from gathered tool outputs).
3. Re-run benchmark and inspect first failing question.
4. Repeat prompt/schema adjustments until at least local open-question threshold is met.

