#!/usr/bin/env python3
"""Task 2 documentation agent with function-calling tools."""


from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request


PROJECT_ROOT = Path(__file__).resolve().parent

ENV_FILE_NAME = ".env.agent.secret"
ENV_KEYS = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]

DRY_RUN_ENV = "AGENT_DRY_RUN"
MAX_TOOL_CALLS = 10

SYSTEM_PROMPT = (
    "You are a documentation assistant for this repository. "
    "Use tools to inspect the local project files before answering when needed. "
    "Prefer list_files to discover relevant files, then read_file to fetch content. "
    "When you answer, include a source reference in this exact format at the end: "
    "SOURCE: relative/path.md#section-anchor ."
)


def _parse_dotenv_simple(path: Path) -> dict[str, str]:
    """
    Very small dotenv parser: expects lines like KEY=VALUE.

    - ignores empty lines and comments starting with '#'
    - trims quotes around values
    """

    data: dict[str, str] = {}
    if not path.exists():
        return data

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            data[key] = value
    return data


def _ensure_llm_config() -> tuple[str, str, str] | None:
    """
    Return (api_key, api_base, model) or None if config is missing.
    """

    missing = [k for k in ENV_KEYS if not os.environ.get(k)]
    if missing:
        dotenv_path = PROJECT_ROOT / ENV_FILE_NAME
        dotenv = _parse_dotenv_simple(dotenv_path)
        for k in missing:
            if k in dotenv and not os.environ.get(k):
                os.environ[k] = dotenv[k]

    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL")
    if not api_key or not api_base or not model:
        return None

    return api_key, api_base, model


def _safe_path_from_repo(path: str) -> Path:
    rel = Path(path)
    if rel.is_absolute():
        raise ValueError("Absolute paths are not allowed")

    candidate = (PROJECT_ROOT / rel).resolve()
    root = PROJECT_ROOT.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise ValueError("Path traversal outside project is not allowed") from e
    return candidate


def _tool_read_file(path: str) -> str:
    try:
        target = _safe_path_from_repo(path)
    except ValueError as e:
        return f"ERROR: {e}"

    if not target.exists():
        return f"ERROR: File not found: {path}"
    if not target.is_file():
        return f"ERROR: Not a file: {path}"
    try:
        return target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"ERROR: Cannot read file: {e}"


def _tool_list_files(path: str) -> str:
    raw_path = path or "."
    try:
        target = _safe_path_from_repo(raw_path)
    except ValueError as e:
        return f"ERROR: {e}"

    if not target.exists():
        return f"ERROR: Path not found: {raw_path}"
    if not target.is_dir():
        return f"ERROR: Not a directory: {raw_path}"
    try:
        entries = sorted(p.name for p in target.iterdir())
        return "\n".join(entries)
    except OSError as e:
        return f"ERROR: Cannot list directory: {e}"


def _extract_answer_from_openai_response(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    first = choices[0] or {}
    message = first.get("message") or {}
    content = message.get("content")
    if content is None:
        return ""
    return str(content).strip()


def _parse_source_from_answer(answer: str) -> tuple[str, str]:
    marker = "SOURCE:"
    if marker not in answer:
        return answer.strip(), ""
    text, source = answer.rsplit(marker, 1)
    return text.strip(), source.strip()


def _tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a text file from this repository using a relative path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from repository root.",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List entries in a repository directory using a relative path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from repository root.",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def _chat_completion(
    messages: list[dict[str, Any]],
    api_key: str,
    api_base: str,
    model: str,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    endpoint = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    # Keep total runtime comfortably under the 60s evaluation limit.
    timeout_s = 55
    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            resp_text = resp.read().decode("utf-8", errors="replace")
            data = json.loads(resp_text)
    except urllib.error.HTTPError as e:
        # Still surface a useful reason in stderr; caller converts to empty answer.
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"LLM HTTPError {e.code}: {body[:200]}") from e

    return data


def _run_agentic_loop(question: str, api_key: str, api_base: str, model: str) -> dict[str, Any]:
    tools = _tool_schemas()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_calls_log: list[dict[str, Any]] = []
    answer = ""
    source = ""

    used_calls = 0
    while used_calls < MAX_TOOL_CALLS:
        data = _chat_completion(
            messages=messages,
            api_key=api_key,
            api_base=api_base,
            model=model,
            tools=tools,
        )
        choices = data.get("choices") or []
        if not choices:
            break
        msg = (choices[0] or {}).get("message") or {}
        assistant_content = msg.get("content") or ""
        raw_tool_calls = msg.get("tool_calls") or []

        if not raw_tool_calls:
            answer, source = _parse_source_from_answer(str(assistant_content))
            break

        messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": raw_tool_calls,
            }
        )

        for tc in raw_tool_calls:
            if used_calls >= MAX_TOOL_CALLS:
                break
            used_calls += 1

            fn = tc.get("function") or {}
            tool_name = fn.get("name") or ""
            arg_str = fn.get("arguments") or "{}"
            call_id = tc.get("id") or ""

            try:
                args = json.loads(arg_str)
            except json.JSONDecodeError:
                args = {}

            if tool_name == "read_file":
                result = _tool_read_file(str(args.get("path", "")))
            elif tool_name == "list_files":
                result = _tool_list_files(str(args.get("path", "")))
            else:
                result = f"ERROR: Unknown tool: {tool_name}"

            tool_calls_log.append(
                {
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": tool_name,
                    "content": result,
                }
            )

    return {"answer": answer, "source": source, "tool_calls": tool_calls_log}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: agent.py \"question\"", file=sys.stderr)
        sys.exit(2)

    question = sys.argv[1]

    # Allow tests to run without external LLM access.
    dry_run = os.environ.get(DRY_RUN_ENV, "").lower() in {"1", "true", "yes", "on"}

    config = _ensure_llm_config()
    if dry_run or config is None:
        fallback = {
            "answer": f"(dry-run) Question received: {question}",
            "source": "",
            "tool_calls": [],
        }
        print(json.dumps(fallback, ensure_ascii=False))
        return

    api_key, api_base, model = config

    ok = True
    try:
        response = _run_agentic_loop(question, api_key, api_base, model)
    except Exception as e:  # noqa: BLE001 - CLI tool should fail gracefully
        print(f"LLM call failed: {e!r}", file=sys.stderr)
        response = {"answer": "", "source": "", "tool_calls": []}
        ok = False

    print(json.dumps(response, ensure_ascii=False))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

