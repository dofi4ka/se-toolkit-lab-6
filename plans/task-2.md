# Implementation Plan: Task 2 (Documentation Agent)

## Goal
Upgrade `agent.py` from a single-shot chatbot into a tool-using documentation agent that can:
- expose `read_file` and `list_files` as function-calling tools,
- run an agentic loop (up to 10 tool calls),
- return JSON with `answer`, `source`, and `tool_calls`.

## Tool Schemas
Define two OpenAI-compatible tool schemas in the LLM request:

1. `read_file`
   - input: `{ "path": "relative/path" }`
   - returns: file content or an error string
2. `list_files`
   - input: `{ "path": "relative/dir" }`
   - returns: newline-separated directory entries or an error string

Both schemas will use strict `path` string parameters and `additionalProperties: false`.

## Path Security
Implement a shared resolver:
- convert relative input path into an absolute path under project root,
- reject absolute paths and parent traversal (`..`) by resolving and verifying the target remains inside root,
- return clear error messages on violations.

This keeps both tools restricted to repository-local files.

## Agentic Loop
1. Send system prompt + user question + tool schemas to chat completions API.
2. If response has `tool_calls`:
   - parse each function call (`name`, JSON args),
   - execute local tool,
   - append assistant tool-call message and tool result message,
   - store call log entries in output `tool_calls`.
3. If response has no `tool_calls`, treat `content` as final answer.
4. Stop after max 10 tool calls.

## Output Contract
Always print valid JSON to stdout:
- `answer` (string)
- `source` (string; can be empty if missing)
- `tool_calls` (array of `{tool, args, result}`)

Debug and errors go to stderr only.

## Model + Env
Continue reading config from:
- `LLM_API_KEY`
- `LLM_API_BASE`
- `LLM_MODEL`

Optional local fallback from `.env.agent.secret` remains for local runs.

