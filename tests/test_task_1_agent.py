import json
import os
import subprocess
import sys
from pathlib import Path


def test_task_1_agent_outputs_json_with_required_fields() -> None:
    """
    Regression test for Task 1:
    - runs `agent.py` as a subprocess
    - parses stdout as JSON
    - asserts required fields exist and `tool_calls` is an empty array
    """

    # This file lives at: se-toolkit-lab-6/tests/test_*.py
    # project root is: se-toolkit-lab-6/
    project_root = Path(__file__).resolve().parents[1]
    agent_path = project_root / "agent.py"
    assert agent_path.exists()

    env = os.environ.copy()
    # Force the agent to run offline so the test doesn't require LLM credentials.
    env["AGENT_DRY_RUN"] = "1"
    env.pop("LLM_API_KEY", None)
    env.pop("LLM_API_BASE", None)
    env.pop("LLM_MODEL", None)

    question = "What does REST stand for?"

    result = subprocess.run(
        [sys.executable, str(agent_path), question],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, (result.stderr or result.stdout)

    stdout = (result.stdout or "").strip()
    assert stdout, "Agent produced no stdout"

    data = json.loads(stdout)
    assert "answer" in data
    assert "tool_calls" in data
    assert data["tool_calls"] == []

