import json, os, subprocess, sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNNER = Path(__file__).parent / "_sandbox_runner.py"

def run_sandboxed(code: str, timeout: float = 5.0) -> str:
    """Execute `code` in a fresh subprocess with a restricted namespace.
    Returns captured stdout, repr(result), or an ERROR string. Never raises."""
    env = {"PYTHONPATH": str(_REPO_ROOT)}
    if sys.platform == "win32" and "SystemRoot" in os.environ:
        env["SystemRoot"] = os.environ["SystemRoot"]
    if "MLOPS_API_URL" in os.environ:
        env["MLOPS_API_URL"] = os.environ["MLOPS_API_URL"]
    try:
        r = subprocess.run(
            [sys.executable, "-I", str(_RUNNER)],
            input=code, capture_output=True, text=True,
            timeout=timeout, cwd=str(_REPO_ROOT), env=env, check=False,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: sandbox exceeded {timeout}s wall-clock timeout"
    if r.returncode != 0 and not r.stdout:
        return f"ERROR: sandbox runner exit {r.returncode}: {r.stderr.strip()[:500]}"
    try:
        payload = json.loads(r.stdout)
    except json.JSONDecodeError:
        return f"ERROR: malformed sandbox output: {r.stdout[:500]!r}"
    if not payload["ok"]:
        return f"ERROR: {payload['error']}\n{payload.get('traceback','')}"
    if payload["stdout"].strip():
        return payload["stdout"]
    if payload.get("result"):
        return payload["result"]
    return "(no output — assign to `result` or use print())"
