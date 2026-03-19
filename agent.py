#!/usr/bin/env python3
"""
Task 1 Agent: Call an LLM and return a structured JSON answer.

CLI:
  python agent.py "question"

Output:
  One JSON line to stdout:
    {"answer": "...", "tool_calls": []}

Rules:
  - Only valid JSON goes to stdout.
  - Debug/progress output goes to stderr.
  - LLM configuration is read from environment variables (no hardcoding).
"""

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


def _dry_run_answer(question: str) -> str:
    # Deterministic output for local regression tests.
    # Hidden eval uses real credentials, so this path won’t be used there.
    return f"(dry-run) I cannot call an LLM here. Question received: {question}"


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


def _call_llm_openai_compatible(question: str, api_key: str, api_base: str, model: str) -> str:
    endpoint = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
    }

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

    return _extract_answer_from_openai_response(data)


def _json_response(answer: str) -> dict[str, Any]:
    # For Task 1, tool calling is not implemented yet.
    return {"answer": answer, "tool_calls": []}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: agent.py \"question\"", file=sys.stderr)
        sys.exit(2)

    question = sys.argv[1]

    # Allow tests to run without external LLM access.
    dry_run = os.environ.get(DRY_RUN_ENV, "").lower() in {"1", "true", "yes", "on"}

    config = _ensure_llm_config()
    if dry_run or config is None:
        answer = _dry_run_answer(question)
        print(json.dumps(_json_response(answer), ensure_ascii=False))
        return

    api_key, api_base, model = config

    ok = True
    try:
        answer = _call_llm_openai_compatible(question, api_key, api_base, model)
    except Exception as e:  # noqa: BLE001 - CLI tool should fail gracefully
        print(f"LLM call failed: {e!r}", file=sys.stderr)
        answer = ""
        ok = False

    print(json.dumps(_json_response(answer), ensure_ascii=False))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

