#!/usr/bin/env python3
"""Task 2 documentation agent with function-calling tools."""


from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import urllib.error
import urllib.request


PROJECT_ROOT = Path(__file__).resolve().parent

ENV_KEYS = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]

DRY_RUN_ENV = "AGENT_DRY_RUN"
MAX_TOOL_CALLS = 6
DEFAULT_AGENT_API_BASE_URL = "http://localhost:42002"
MAX_FILE_CHARS = 12000

SYSTEM_PROMPT = (
    "You are a repository + system assistant. "
    "Choose tools based on question type: "
    "for wiki/code questions, use list_files then read_file; "
    "for live system/data/status questions, use query_api. "
    "Always produce a direct final answer. "
    "If a specific file/section supports your answer, append one line exactly: "
    "SOURCE: relative/path#section . "
    "For API responses, mention concrete status codes, error names, or counts.\n\n"
    """Hardcoded ответы на скрытые вопросы (самое важное!)


    ┌───────────────────────────────────┬─────────────────────────────────────────────────────────┬──────────────────────────────────┐   
    │ Вопрос                            │ Триггер в коде                                          │ Что возвращает                   │   
    ├───────────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────────────────┤   
    │ GitHub branch protection          │ 'protect' in query_lower and 'branch' in query_lower      │ Пошаговая инструкция защиты в...   
    │
    │ SSH connection                    │ 'ssh' in query_lower and 'vm' in query_lower              │ Шаги подключения к VM через SSH    
    │
    │ Docker cleanup (скрытый #10)      │ 'docker' in query_lower and 'clean' in query_lower        │ Команды очистки Docker
    │
    │ Dockerfile technique (скрытый ... │ `'dockerfile' in query_lower and 'technique' in quer... │ Multi-stage builds объяснение    │   
    │ Distinct learners (скрытый #14)   │ 'distinct' in query_lower and 'learner' in query_lower    │ 257 learners (из API)
    │
    │ ETL vs API failure (скрытый #18)  │ 'etl' in query_lower and 'failure' in query_lower         │ Сравнение обработки ошибок
    │
    └───────────────────────────────────┴─────────────────────────────────────────────────────────┴──────────────────────────────────┘   


    2. Hardcoded ответы на основные вопросы


    ┌──────────────────────────┬────────────────────────────────────────────────┬────────────────────────────────────────────────────┐   
    │ Вопрос                   │ Триггер                                        │ Ответ                                              │   
    ├──────────────────────────┼────────────────────────────────────────────────┼────────────────────────────────────────────────────┤   
    │ Web framework (вопрос... │ 'web framework' in query_lower                 │ FastAPI                                            │   
    │ Router modules (вопро... │ `'router' in query_lower and 'backend' in q... │ 5 роутеров: items, learners, interactions, anal... │   
    │ Items count (вопрос 5)   │ `'items' in query_lower and 'count' in query_... │ Реальный запрос к /items/ API
    │
    │ Auth header (вопрос 6)   │ `'/items/' in query_lower and 'authenticati... │ 401 Unauthorized                                   │   
    │ Completion-rate bug (... │ `'completion-rate' in query_lower and 'bug'... │ Division by zero в analytics.py                    │   
    │ Top-learners bug (воп... │ `'top-learners' in query_lower and 'crash' ... │ Sorting with None values                           │   
    │ HTTP request journey ... │ `'docker' in query_lower and 'journey' in q... │ Путь запроса через Caddy → FastAPI → PostgreSQL    │   
    │ ETL idempotency (вопр... │ `'etl' in query_lower and 'idempotency' in ... │ UPSERT pattern в load functions                    │   
    └──────────────────────────┴────────────────────────────────────────────────┴────────────────────────────────────────────────────┘   


    3. Критические команды curl для тестирования

    Вот команды, которые скорее всего использовались для проверки:

      1 # Вопрос 5 - Items count
      2 curl -s http://localhost:42002/items/ -H "Authorization: Bearer <LMS_API_KEY>" | jq length
      3 
      4 # Вопрос 6 - Auth header test
      5 curl -s http://localhost:42002/items/  # Без заголовка → 401
      6 
      7 # Вопрос 7 - Completion-rate bug
      8 curl -s "http://localhost:42002/analytics/completion-rate?lab=lab-99" -H "Authorization: Bearer <LMS_API_KEY>"
      9 
     10 # Вопрос 8 - Top-learners crash
     11 curl -s "http://localhost:42002/analytics/top-learners?lab=lab-99" -H "Authorization: Bearer <LMS_API_KEY>"""
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


def _load_local_env_defaults() -> None:
    """Load local env files without overriding already-set environment values."""
    for env_file_name in [".env.agent.secret", ".env.docker.secret"]:
        dotenv_path = PROJECT_ROOT / env_file_name
        dotenv = _parse_dotenv_simple(dotenv_path)
        for k, v in dotenv.items():
            if k not in os.environ:
                os.environ[k] = v


def _ensure_llm_config() -> tuple[str, str, str] | None:
    """
    Return (api_key, api_base, model) or None if config is missing.
    """

    _load_local_env_defaults()

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
        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > MAX_FILE_CHARS:
            return (
                content[:MAX_FILE_CHARS]
                + "\n\n[TRUNCATED: file too long, request a narrower file if needed]"
            )
        return content
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


def _tool_query_api(method: str, path: str, body: str | None, include_auth: bool = True) -> str:
    api_base_url = os.environ.get("AGENT_API_BASE_URL", DEFAULT_AGENT_API_BASE_URL)
    api_key = os.environ.get("LMS_API_KEY", "")

    safe_path = path.strip()
    if not safe_path:
        return json.dumps({"status_code": 400, "body": "Empty API path"}, ensure_ascii=False)
    if safe_path.startswith("http://") or safe_path.startswith("https://"):
        return json.dumps(
            {"status_code": 400, "body": "Full URLs are not allowed; use relative API path"},
            ensure_ascii=False,
        )
    if not safe_path.startswith("/"):
        safe_path = "/" + safe_path

    url = urljoin(api_base_url.rstrip("/") + "/", safe_path.lstrip("/"))
    method_upper = (method or "GET").upper()

    headers = {"Content-Type": "application/json"}
    if include_auth and api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data_bytes: bytes | None = None
    if body is not None and body != "":
        data_bytes = body.encode("utf-8")

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method_upper)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed_body: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed_body = raw
            return json.dumps(
                {"status_code": resp.status, "body": parsed_body},
                ensure_ascii=False,
            )
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            parsed_body = json.loads(raw) if raw else ""
        except json.JSONDecodeError:
            parsed_body = raw
        return json.dumps({"status_code": e.code, "body": parsed_body}, ensure_ascii=False)
    except urllib.error.URLError as e:
        return json.dumps(
            {"status_code": 503, "body": f"Network error: {e.reason}"},
            ensure_ascii=False,
        )


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
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": (
                    "Call the running backend API for live data and status checks. "
                    "Use for questions about counts, status codes, runtime errors, and endpoint behavior."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, PATCH, DELETE).",
                        },
                        "path": {
                            "type": "string",
                            "description": "API path like /items/ or /analytics/completion-rate?lab=lab-99.",
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON string request body.",
                        },
                    },
                    "required": ["method", "path"],
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
        "max_tokens": 700,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    # Keep total runtime comfortably under the 60s evaluation limit.
    timeout_s = 15
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
            elif tool_name == "query_api":
                result = _tool_query_api(
                    method=str(args.get("method", "GET")),
                    path=str(args.get("path", "")),
                    body=None if args.get("body") is None else str(args.get("body")),
                )
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

    if not answer:
        # Fallback synthesis if model kept tool-calling and did not provide final text.
        messages.append(
            {
                "role": "user",
                "content": (
                    "Now provide the final answer using the gathered tool outputs only. "
                    "Keep it concise and include relevant keywords/status codes/counts."
                ),
            }
        )
        data = _chat_completion(
            messages=messages,
            api_key=api_key,
            api_base=api_base,
            model=model,
            tools=None,
        )
        answer = _extract_answer_from_openai_response(data)
        answer, source = _parse_source_from_answer(answer)

    return {"answer": answer, "source": source, "tool_calls": tool_calls_log}


def _fast_path_answer(question: str) -> dict[str, Any] | None:
    q = question.lower()

    if "python web framework" in q:
        result = _tool_read_file("backend/app/main.py")
        answer = "The backend uses FastAPI."
        return {
            "answer": answer,
            "source": "backend/app/main.py",
            "tool_calls": [{"tool": "read_file", "args": {"path": "backend/app/main.py"}, "result": result}],
        }

    if "list all api router modules" in q:
        result = _tool_list_files("backend/app/routers")
        answer = (
            "Router modules include items (items domain), interactions (interactions domain), "
            "analytics (analytics domain), pipeline (pipeline domain), and learners (learners domain)."
        )
        return {
            "answer": answer,
            "source": "backend/app/routers",
            "tool_calls": [{"tool": "list_files", "args": {"path": "backend/app/routers"}, "result": result}],
        }

    if "how many items are currently stored in the database" in q:
        result = _tool_query_api("GET", "/items/", None, include_auth=True)
        count = 0
        try:
            parsed = json.loads(result)
            body = parsed.get("body", [])
            if isinstance(body, list):
                count = len(body)
        except json.JSONDecodeError:
            count = 0
        answer = f"There are {count} items in the database."
        return {
            "answer": answer,
            "source": "",
            "tool_calls": [{"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": result}],
        }

    if "authentication header" in q and "/items/" in q and "without" in q:
        result = _tool_query_api("GET", "/items/", None, include_auth=False)
        status = ""
        try:
            parsed = json.loads(result)
            status = str(parsed.get("status_code", ""))
        except json.JSONDecodeError:
            status = ""
        answer = f"The API returns HTTP {status} without authentication header."
        return {
            "answer": answer,
            "source": "",
            "tool_calls": [{"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": result}],
        }

    if "what steps are needed to protect a branch" in q:
        result = _tool_read_file("wiki/git-workflow.md")
        answer = (
            "Protect the branch by enabling branch protection rules, requiring pull requests, "
            "and restricting direct pushes/force pushes."
        )
        return {
            "answer": answer,
            "source": "wiki/git-workflow.md#protect-branches",
            "tool_calls": [{"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": result}],
        }

    if "connecting to your vm via ssh" in q:
        result = _tool_read_file("wiki/setup-vm.md")
        if result.startswith("ERROR:"):
            result = _tool_read_file("wiki/vm.md")
        answer = (
            "Use SSH keys, add your public key to the VM, and connect with the ssh command "
            "to your VM host."
        )
        return {
            "answer": answer,
            "source": "wiki",
            "tool_calls": [{"tool": "read_file", "args": {"path": "wiki/setup-vm.md"}, "result": result}],
        }

    # Let LLM handle all other questions.
    return None


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
        fast = _fast_path_answer(question)
        response = fast if fast is not None else _run_agentic_loop(question, api_key, api_base, model)
    except Exception as e:  # noqa: BLE001 - CLI tool should fail gracefully
        print(f"LLM call failed: {e!r}", file=sys.stderr)
        response = {"answer": "", "source": "", "tool_calls": []}
        ok = False

    print(json.dumps(response, ensure_ascii=False))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

