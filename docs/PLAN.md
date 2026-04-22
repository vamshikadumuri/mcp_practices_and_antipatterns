# MCP Code Mode Demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two FastMCP servers over the same synthetic ML-ops dataset — a classic tool-per-operation server and a Code Mode server exposing `list_api` + `execute_python` — plus a benchmark harness that runs identical prompts through both via the Anthropic API and reports token deltas, so the team can see Code Mode's token savings on apples-to-apples scenarios.

**Architecture:**
- A shared `mlops_backend` package holds synthetic data (batch jobs, endpoints, models, datasets, metrics) and a typed Python API. Both servers call into it so results are identical.
- `servers/classic_server.py` wraps each backend function as an `@mcp.tool` (~15 tools).
- `servers/codemode_server.py` exposes two tools: `list_api(filter?)` returns compact signatures; `execute_python(code)` runs user code inside a restricted namespace where the backend module is pre-imported — only stdout / the `result` variable is returned to the model.
- `bench/run_benchmark.py` launches each server over stdio via the `mcp` Python SDK, runs a fixed set of multi-step ML-ops scenarios through `claude-sonnet-4-6`, and captures `usage` from every API response into a side-by-side markdown report.

**Tech Stack:** Python 3.11+, FastMCP 3.x, `mcp` Python SDK (stdio client), `anthropic` SDK, `pytest`, `python-dotenv`. Existing `codemodevenv/` Windows venv.

**Plan-mode note:** This plan lives at `C:\Users\vamsh\.claude\plans\i-have-a-requirement-curious-deer.md` (plan mode's designated file). When execution begins, copy it into the repo as `docs/PLAN.md` for teammates to read.

---

## File Structure

```
mcp_code_mode/
├── README.md                        # Project overview + run instructions
├── pyproject.toml                   # Deps: fastmcp, mcp, anthropic, pytest, python-dotenv
├── .env.example                     # ANTHROPIC_API_KEY=
├── .gitignore                       # venv, .env, __pycache__, bench/results/
├── docs/
│   ├── PLAN.md                      # Copy of this plan
│   └── TRANSCRIPTS.md               # Auto-generated side-by-side transcripts (Task 9)
├── mlops_backend/
│   ├── __init__.py                  # Re-exports the typed API
│   ├── data.py                      # Synthetic dataset loader (reads data/*.json)
│   ├── api.py                       # Typed functions: list_batch_jobs, get_job_logs, ...
│   └── data/                        # Fixture JSON: batch_jobs.json, endpoints.json, models.json, datasets.json, metrics.json, alerts.json
├── servers/
│   ├── classic_server.py            # FastMCP server exposing ~15 tools (1:1 with api.py)
│   └── codemode_server.py           # FastMCP server exposing list_api + execute_python
├── bench/
│   ├── scenarios.py                 # List of 5 benchmark prompts (identical for both servers)
│   ├── run_benchmark.py             # Agent loop + stdio MCP client + usage capture
│   ├── report.py                    # Renders results/*.json into docs/TRANSCRIPTS.md + summary table
│   └── results/                     # .gitignored, raw run outputs
└── tests/
    ├── test_backend.py              # Unit tests for mlops_backend.api
    ├── test_classic_server.py       # In-process FastMCP client hitting classic tools
    └── test_codemode_server.py      # In-process FastMCP client; exercises list_api + execute_python
```

---

## Critical Files to Get Right

- `mlops_backend/api.py` — single source of truth. Classic tools are a thin wrapper; Code Mode exposes the same names via `execute_python`. Signatures must match.
- `servers/codemode_server.py` — the sandbox namespace design is the whole point. `execute_python` must (a) pre-import `mlops_backend.api as mlops`, (b) capture `stdout`, (c) return either the `result` variable or captured stdout, (d) never leak intermediate data into the return payload.
- `bench/run_benchmark.py` — the agent loop must correctly accumulate `response.usage.input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` across **every** turn (including tool-result turns), not just the first. This is the number the team will see.

---

## Task 1: Project scaffold and dependencies

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`, `mlops_backend/__init__.py`, `servers/__init__.py`, `bench/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "mcp-code-mode-demo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastmcp>=3.2.0",
  "mcp>=1.2.0",
  "anthropic>=0.40.0",
  "python-dotenv>=1.0.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Write `.gitignore`** — the `.env` line is load-bearing; never remove it.

```
codemodevenv/
__pycache__/
*.pyc
.env
.env.*
!.env.example
bench/results/
.pytest_cache/
.claude/settings.local.json
```

- [ ] **Step 3: Write `.env.example`** — placeholder only, no real secrets. This file IS committed; the real `.env` is NOT.

```
ANTHROPIC_API_KEY=sk-ant-REPLACE_ME
BENCH_MODEL=claude-sonnet-4-6
```

- [ ] **Step 3a: Verify key cannot be committed**

Before any `git add`, run these two checks and proceed only if both pass:

```bash
# 1. Confirm .env is ignored (if you have one locally):
git check-ignore -v .env   # expected: prints the .gitignore rule that matches
# 2. Confirm no accidental key literal is staged anywhere:
git diff --cached | grep -E 'sk-ant-[A-Za-z0-9_-]{20,}' && echo "SECRET DETECTED — ABORT" || echo "clean"
```

If the second command prints `SECRET DETECTED`, unstage that file and fix before committing.

- [ ] **Step 4: Install deps**

Run: `codemodevenv/Scripts/python.exe -m pip install -e ".[dev]"`
Expected: installs fastmcp, mcp, anthropic.

- [ ] **Step 5: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold project and pin deps"
```

---

## Task 2: Synthetic ML-ops dataset

**Files:**
- Create: `mlops_backend/data/batch_jobs.json`, `endpoints.json`, `models.json`, `datasets.json`, `metrics.json`, `alerts.json`
- Create: `mlops_backend/data.py`

**Data design rules:** enough rows to make filtering meaningful but small enough to fit in memory. Target: 40 batch jobs (mix of SUCCEEDED/FAILED/RUNNING across 5 models, last 7 days), 8 endpoints (with daily metrics for 14 days), 5 models, 6 datasets, 12 alerts.

- [ ] **Step 1: Write `mlops_backend/data/batch_jobs.json`** with 40 records of this shape:

```json
{
  "job_id": "bj-0001",
  "model_id": "m-llama3-8b-ft",
  "dataset_id": "ds-support-tickets",
  "status": "FAILED",
  "submitted_at": "2026-04-20T14:02:00Z",
  "finished_at": "2026-04-20T14:47:12Z",
  "shards_total": 32,
  "shards_failed": 5,
  "gpu_hours": 12.4,
  "cost_usd": 38.70,
  "failure_reason": "CUDA OOM on shard 17"
}
```

Include a realistic mix: ~25% FAILED (with varied `failure_reason` — "CUDA OOM", "tokenizer mismatch", "dataset schema drift", "worker preempted"), ~10% RUNNING, rest SUCCEEDED.

- [ ] **Step 2: Write `endpoints.json`** with 8 entries:

```json
{
  "endpoint_id": "ep-prod-chat",
  "model_id": "m-llama3-8b-ft",
  "traffic_split": {"m-llama3-8b-ft": 90, "m-llama3-8b-ft-v2": 10},
  "replicas": 6,
  "created_at": "2026-03-15T00:00:00Z",
  "status": "HEALTHY"
}
```

- [ ] **Step 3: Write `models.json`** (5 models with `model_id`, `base`, `task`, `size_params`, `owner`), `datasets.json` (6 datasets with `dataset_id`, `rows`, `schema_version`, `tags`), `alerts.json` (12 alerts with `alert_id`, `endpoint_id`, `severity`, `fired_at`, `message`).

- [ ] **Step 4: Write `metrics.json`** — per-endpoint daily rollups for 14 days:

```json
{
  "endpoint_id": "ep-prod-chat",
  "date": "2026-04-21",
  "qps": 142.3,
  "p50_ms": 310,
  "p99_ms": 1180,
  "error_rate": 0.004,
  "tokens_out": 18400000
}
```

- [ ] **Step 5: Write `mlops_backend/data.py`**

```python
import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"

@lru_cache(maxsize=None)
def load(name: str) -> list[dict]:
    return json.loads((_DATA_DIR / f"{name}.json").read_text())
```

- [ ] **Step 6: Commit**

```bash
git add mlops_backend/
git commit -m "feat(backend): add synthetic ml-ops fixtures + loader"
```

---

## Task 3: Typed backend API (TDD)

**Files:**
- Create: `tests/test_backend.py`
- Create: `mlops_backend/api.py`
- Modify: `mlops_backend/__init__.py` (re-export)

- [ ] **Step 1: Write failing tests** in `tests/test_backend.py`:

```python
from mlops_backend import api

def test_list_batch_jobs_filters_by_status():
    failed = api.list_batch_jobs(status="FAILED")
    assert all(j["status"] == "FAILED" for j in failed)
    assert len(failed) > 0

def test_list_batch_jobs_filters_by_model():
    jobs = api.list_batch_jobs(model_id="m-llama3-8b-ft")
    assert all(j["model_id"] == "m-llama3-8b-ft" for j in jobs)

def test_get_batch_job_returns_single_record():
    j = api.get_batch_job("bj-0001")
    assert j["job_id"] == "bj-0001"

def test_get_endpoint_metrics_window():
    rows = api.get_endpoint_metrics("ep-prod-chat", days=7)
    assert len(rows) == 7
    assert all("p99_ms" in r for r in rows)

def test_compare_runs_returns_diff():
    diff = api.compare_runs(["bj-0001", "bj-0002"])
    assert "gpu_hours" in diff and "cost_usd" in diff
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `codemodevenv/Scripts/python.exe -m pytest tests/test_backend.py -v`
Expected: `ImportError` / `AttributeError` on `api.*`.

- [ ] **Step 3: Implement `mlops_backend/api.py`**

```python
from datetime import datetime, timedelta, timezone
from . import data

def list_batch_jobs(status: str | None = None, model_id: str | None = None,
                    since_hours: int | None = None) -> list[dict]:
    rows = data.load("batch_jobs")
    if status:
        rows = [r for r in rows if r["status"] == status]
    if model_id:
        rows = [r for r in rows if r["model_id"] == model_id]
    if since_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        rows = [r for r in rows
                if datetime.fromisoformat(r["submitted_at"].replace("Z", "+00:00")) >= cutoff]
    return rows

def get_batch_job(job_id: str) -> dict:
    for r in data.load("batch_jobs"):
        if r["job_id"] == job_id:
            return r
    raise KeyError(job_id)

def get_batch_job_logs(job_id: str, lines: int = 50) -> str:
    job = get_batch_job(job_id)
    # Synthetic deterministic logs
    header = f"[job {job_id} model={job['model_id']} status={job['status']}]"
    body = "\n".join(f"step {i:04d} loss=... " for i in range(lines))
    tail = f"\n{job.get('failure_reason','')}" if job["status"] == "FAILED" else ""
    return header + "\n" + body + tail

def retry_failed_shards(job_id: str) -> dict:
    job = get_batch_job(job_id)
    return {"job_id": job_id, "retried_shards": job.get("shards_failed", 0), "new_job_id": f"{job_id}-r1"}

def list_models() -> list[dict]: return data.load("models")
def get_model(model_id: str) -> dict:
    for m in data.load("models"):
        if m["model_id"] == model_id: return m
    raise KeyError(model_id)

def list_datasets() -> list[dict]: return data.load("datasets")
def get_dataset(dataset_id: str) -> dict:
    for d in data.load("datasets"):
        if d["dataset_id"] == dataset_id: return d
    raise KeyError(dataset_id)

def list_endpoints(status: str | None = None) -> list[dict]:
    rows = data.load("endpoints")
    return [r for r in rows if not status or r["status"] == status]

def get_endpoint(endpoint_id: str) -> dict:
    for e in data.load("endpoints"):
        if e["endpoint_id"] == endpoint_id: return e
    raise KeyError(endpoint_id)

def get_endpoint_metrics(endpoint_id: str, days: int = 7) -> list[dict]:
    rows = [m for m in data.load("metrics") if m["endpoint_id"] == endpoint_id]
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows[:days]

def update_traffic_split(endpoint_id: str, splits: dict) -> dict:
    return {"endpoint_id": endpoint_id, "applied": splits, "status": "OK"}

def tail_endpoint_logs(endpoint_id: str, lines: int = 50) -> str:
    ep = get_endpoint(endpoint_id)
    return f"[endpoint {endpoint_id} model={ep['model_id']}]\n" + \
           "\n".join(f"req {i} 200 latency_ms=..." for i in range(lines))

def list_alerts(severity: str | None = None) -> list[dict]:
    rows = data.load("alerts")
    return [r for r in rows if not severity or r["severity"] == severity]

def compare_runs(job_ids: list[str]) -> dict:
    jobs = [get_batch_job(j) for j in job_ids]
    return {
        "job_ids": job_ids,
        "gpu_hours": {j["job_id"]: j["gpu_hours"] for j in jobs},
        "cost_usd": {j["job_id"]: j["cost_usd"] for j in jobs},
        "status": {j["job_id"]: j["status"] for j in jobs},
    }
```

- [ ] **Step 4: Update `mlops_backend/__init__.py`**

```python
from . import api  # noqa: F401
```

- [ ] **Step 5: Run tests, confirm pass**

Run: `codemodevenv/Scripts/python.exe -m pytest tests/test_backend.py -v`
Expected: all 5 pass.

- [ ] **Step 6: Commit**

```bash
git add mlops_backend/api.py mlops_backend/__init__.py tests/test_backend.py
git commit -m "feat(backend): typed ml-ops api with unit tests"
```

---

## Task 4: Classic MCP server

**Files:**
- Create: `servers/classic_server.py`
- Create: `tests/test_classic_server.py`

- [ ] **Step 1: Write failing in-process client test**

```python
import pytest
from fastmcp import Client
from servers.classic_server import mcp

@pytest.mark.asyncio
async def test_classic_exposes_expected_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert {"list_batch_jobs", "get_batch_job", "list_endpoints",
                "get_endpoint_metrics", "compare_runs"} <= names

@pytest.mark.asyncio
async def test_classic_list_batch_jobs_failed():
    async with Client(mcp) as client:
        res = await client.call_tool("list_batch_jobs", {"status": "FAILED"})
        assert res.data  # FastMCP returns parsed data
        assert all(j["status"] == "FAILED" for j in res.data)
```

- [ ] **Step 2: Run, confirm fail** (module missing).

- [ ] **Step 3: Implement `servers/classic_server.py`**

```python
from fastmcp import FastMCP
from mlops_backend import api

mcp = FastMCP("mlops-classic")

@mcp.tool
def list_batch_jobs(status: str | None = None, model_id: str | None = None,
                    since_hours: int | None = None) -> list[dict]:
    """List batch inference jobs, optionally filtered by status / model / recency."""
    return api.list_batch_jobs(status, model_id, since_hours)

@mcp.tool
def get_batch_job(job_id: str) -> dict:
    """Fetch a single batch job by id."""
    return api.get_batch_job(job_id)

@mcp.tool
def get_batch_job_logs(job_id: str, lines: int = 50) -> str:
    """Return the last N log lines for a batch job."""
    return api.get_batch_job_logs(job_id, lines)

@mcp.tool
def retry_failed_shards(job_id: str) -> dict:
    """Retry only the failed shards of a batch job."""
    return api.retry_failed_shards(job_id)

@mcp.tool
def list_models() -> list[dict]:
    """List all registered models."""
    return api.list_models()

@mcp.tool
def get_model(model_id: str) -> dict:
    """Fetch a model by id."""
    return api.get_model(model_id)

@mcp.tool
def list_datasets() -> list[dict]:
    """List all datasets."""
    return api.list_datasets()

@mcp.tool
def get_dataset(dataset_id: str) -> dict:
    """Fetch a dataset by id."""
    return api.get_dataset(dataset_id)

@mcp.tool
def list_endpoints(status: str | None = None) -> list[dict]:
    """List online serving endpoints."""
    return api.list_endpoints(status)

@mcp.tool
def get_endpoint(endpoint_id: str) -> dict:
    """Fetch a single endpoint."""
    return api.get_endpoint(endpoint_id)

@mcp.tool
def get_endpoint_metrics(endpoint_id: str, days: int = 7) -> list[dict]:
    """Daily QPS / p50 / p99 / error-rate rollups for an endpoint."""
    return api.get_endpoint_metrics(endpoint_id, days)

@mcp.tool
def update_traffic_split(endpoint_id: str, splits: dict) -> dict:
    """Apply a new traffic split across model versions for an endpoint."""
    return api.update_traffic_split(endpoint_id, splits)

@mcp.tool
def tail_endpoint_logs(endpoint_id: str, lines: int = 50) -> str:
    """Tail recent request logs for an endpoint."""
    return api.tail_endpoint_logs(endpoint_id, lines)

@mcp.tool
def list_alerts(severity: str | None = None) -> list[dict]:
    """List firing alerts, optionally filtered by severity."""
    return api.list_alerts(severity)

@mcp.tool
def compare_runs(job_ids: list[str]) -> dict:
    """Compare GPU hours, cost, and status across N batch jobs."""
    return api.compare_runs(job_ids)

if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: Run tests**

Run: `codemodevenv/Scripts/python.exe -m pytest tests/test_classic_server.py -v`
Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add servers/classic_server.py tests/test_classic_server.py
git commit -m "feat(classic): expose ml-ops api as 15 @mcp.tool functions"
```

---

## Task 5: Code Mode MCP server with real subprocess sandbox

**Files:**
- Create: `servers/_sandbox_runner.py` (child-process entry point)
- Create: `servers/sandbox.py` (parent-side helper)
- Create: `servers/codemode_server.py`
- Create: `tests/test_sandbox.py`
- Create: `tests/test_codemode_server.py`

**Sandbox design (real, not `exec()`-in-process):**

Every `execute_python` call spawns a short-lived child Python process and feeds the code in over stdin. The child:
1. Runs the code in a namespace whose `__builtins__` is a curated dict — no `__import__`, `open`, `eval`, `exec`, `compile`, `input`, `breakpoint`, `help`, `getattr` (reducing attribute-chain escapes).
2. Pre-imports `mlops_backend.api as mlops` so the LLM has the intended API and only that API.
3. Captures stdout and either the `result` variable; emits a single JSON line on its real stdout.

The parent enforces:
- **Wall-clock timeout** (default 5s) via `subprocess.run(timeout=)` → prevents infinite loops.
- **Minimal env** (`PYTHONPATH`, `SystemRoot` on Windows, nothing else) → no inherited secrets, no `HTTP_PROXY`, etc.
- **Cwd = workspace root** → relative paths resolve to our repo, not arbitrary locations.
- **Captured stdout/stderr** → parent process is never corrupted by child output.

**What this does NOT defend against (document in README):**
- A determined adversary could still reach network syscalls via unusual attribute chains (Python's introspection surface is vast). For true production Code Mode, use a language-level isolate (Cloudflare Workers / Deno / Pyodide-in-WASM) or OS-level isolation (nsjail, Docker per call, Windows Job Objects). This demo prioritizes clarity over impregnability and is safe because the only code runner is Claude against our own API.
- CPU/memory caps (Python's `resource` module is Unix-only; Windows needs Job Objects via pywin32). Timeout is our only cap here.

- [ ] **Step 1: Write `servers/_sandbox_runner.py`** (the child process — this file is the only place `exec` runs)

```python
"""Sandbox runner. Reads user code from stdin, runs it with a curated
__builtins__ and only `mlops` pre-imported, emits JSON result on stdout.
Never import this module into the parent process."""
import builtins, contextlib, io, json, sys, traceback
from mlops_backend import api as mlops

# Curated builtins — only safe primitives. No __import__, open, eval,
# exec, compile, input, getattr, setattr, delattr, breakpoint, help,
# vars, globals, locals, object.__subclasses__ reachers, etc.
_SAFE_NAMES = [
    "abs","all","any","ascii","bin","bool","bytes","callable","chr",
    "dict","divmod","enumerate","filter","float","format","frozenset",
    "hash","hex","id","int","isinstance","issubclass","iter","len","list",
    "map","max","min","next","oct","ord","pow","print","range","repr",
    "reversed","round","set","slice","sorted","str","sum","tuple","zip",
    "True","False","None","Exception","ValueError","KeyError","TypeError",
    "IndexError","StopIteration","ArithmeticError","ZeroDivisionError",
]
SAFE_BUILTINS = {name: getattr(builtins, name) for name in _SAFE_NAMES}

def main() -> None:
    code = sys.stdin.read()
    buf = io.StringIO()
    env = {"mlops": mlops, "__builtins__": SAFE_BUILTINS}
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(code, "<codemode>", "exec"), env)
        payload = {"ok": True, "stdout": buf.getvalue(),
                   "result": repr(env["result"]) if "result" in env else None}
    except BaseException as e:  # catch SystemExit too
        payload = {"ok": False,
                   "error": f"{type(e).__name__}: {e}",
                   "traceback": traceback.format_exc(limit=3),
                   "stdout": buf.getvalue()}
    sys.stdout.write(json.dumps(payload))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `servers/sandbox.py`** (parent-side helper)

```python
import json, os, subprocess, sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNNER = Path(__file__).parent / "_sandbox_runner.py"

def run_sandboxed(code: str, timeout: float = 5.0) -> str:
    """Execute `code` in a fresh subprocess with a restricted namespace.
    Returns captured stdout, repr(result), or an ERROR string. Never raises."""
    env = {"PYTHONPATH": str(_REPO_ROOT)}
    if sys.platform == "win32" and "SystemRoot" in os.environ:
        env["SystemRoot"] = os.environ["SystemRoot"]  # required for Windows subprocess
    try:
        r = subprocess.run(
            [sys.executable, "-I", str(_RUNNER)],  # -I = isolated mode
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
```

- [ ] **Step 3: Write failing sandbox tests** in `tests/test_sandbox.py`

```python
from servers.sandbox import run_sandboxed

def test_sandbox_runs_basic_code():
    out = run_sandboxed("print(2 + 2)")
    assert out.strip() == "4"

def test_sandbox_returns_result_variable():
    out = run_sandboxed("result = sum(range(10))")
    assert "45" in out

def test_sandbox_has_mlops_preimported():
    out = run_sandboxed("print(len(mlops.list_models()))")
    assert out.strip() == "5"

def test_sandbox_blocks_import_statement():
    out = run_sandboxed("import os\nprint(os.getcwd())")
    assert out.startswith("ERROR:")
    assert "__import__" in out or "ImportError" in out or "NameError" in out

def test_sandbox_blocks_open_builtin():
    out = run_sandboxed("open('/etc/passwd')")
    assert out.startswith("ERROR:") and "open" in out

def test_sandbox_blocks_eval_and_exec():
    assert run_sandboxed("eval('1+1')").startswith("ERROR:")
    assert run_sandboxed("exec('print(1)')").startswith("ERROR:")

def test_sandbox_enforces_timeout():
    out = run_sandboxed("while True: pass", timeout=1.0)
    assert "timeout" in out.lower()

def test_sandbox_isolates_state_between_calls():
    run_sandboxed("result = 42")           # set
    out = run_sandboxed("print(result)")   # next call
    assert out.startswith("ERROR:") or "NameError" in out
```

- [ ] **Step 4: Run — confirm tests fail** (no `servers.sandbox` yet if out of order, or confirm they pass after step 2).

Run: `codemodevenv/Scripts/python.exe -m pytest tests/test_sandbox.py -v`
Expected: all 8 pass. If `test_sandbox_blocks_import_statement` fails with stdout instead of ERROR, that is a security regression — stop and fix before proceeding.

- [ ] **Step 5: Write `servers/codemode_server.py`**

```python
import inspect
from fastmcp import FastMCP
from mlops_backend import api as mlops
from servers.sandbox import run_sandboxed

mcp = FastMCP("mlops-codemode")

_EXPORTED = [
    "list_batch_jobs", "get_batch_job", "get_batch_job_logs", "retry_failed_shards",
    "list_models", "get_model", "list_datasets", "get_dataset",
    "list_endpoints", "get_endpoint", "get_endpoint_metrics",
    "update_traffic_split", "tail_endpoint_logs", "list_alerts", "compare_runs",
]

def _signatures(filter: str | None = None) -> str:
    lines = []
    for name in _EXPORTED:
        if filter and filter not in name:
            continue
        fn = getattr(mlops, name)
        sig = inspect.signature(fn)
        doc = (inspect.getdoc(fn) or "").splitlines()[0]
        lines.append(f"mlops.{name}{sig}  # {doc}".rstrip())
    return "\n".join(lines)

@mcp.tool
def list_api(filter: str | None = None) -> str:
    """Return one-line signatures for every callable in the `mlops` module.

    Call this first to discover the API, then call `execute_python` with code
    that uses the signatures. Optionally filter by substring on the name.
    """
    return _signatures(filter)

@mcp.tool
def execute_python(code: str) -> str:
    """Run Python in a sandboxed subprocess. `mlops` is pre-imported; no other
    imports are available. Returns captured stdout, else repr(`result`).
    Intermediate variables stay inside the sandbox and are discarded after
    each call — there is no cross-call state."""
    return run_sandboxed(code)

if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 6: Write failing server tests** in `tests/test_codemode_server.py`

```python
import pytest
from fastmcp import Client
from servers.codemode_server import mcp

@pytest.mark.asyncio
async def test_codemode_exposes_two_tools():
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
        assert names == {"list_api", "execute_python"}

@pytest.mark.asyncio
async def test_list_api_returns_compact_signatures():
    async with Client(mcp) as client:
        res = await client.call_tool("list_api", {})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "list_batch_jobs(" in text and "compare_runs(" in text

@pytest.mark.asyncio
async def test_list_api_filter():
    async with Client(mcp) as client:
        res = await client.call_tool("list_api", {"filter": "endpoint"})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "list_endpoints" in text and "list_batch_jobs" not in text

@pytest.mark.asyncio
async def test_execute_python_uses_sandbox():
    async with Client(mcp) as client:
        code = ("failed = mlops.list_batch_jobs(status='FAILED')\n"
                "print(f'{len(failed)} failed jobs')\n")
        res = await client.call_tool("execute_python", {"code": code})
        assert "failed jobs" in (res.data if isinstance(res.data, str) else str(res.data))

@pytest.mark.asyncio
async def test_execute_python_blocks_import():
    async with Client(mcp) as client:
        res = await client.call_tool("execute_python", {"code": "import os"})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert text.startswith("ERROR:")
```

- [ ] **Step 7: Run all tests**

Run: `codemodevenv/Scripts/python.exe -m pytest tests/ -v`
Expected: everything green.

- [ ] **Step 8: Commit**

```bash
git add servers/_sandbox_runner.py servers/sandbox.py servers/codemode_server.py \
        tests/test_sandbox.py tests/test_codemode_server.py
git commit -m "feat(codemode): subprocess sandbox + list_api/execute_python tools"
```

---

## Task 6: Benchmark scenarios

**Files:**
- Create: `bench/scenarios.py`

- [ ] **Step 1: Write `bench/scenarios.py`**

```python
SCENARIOS = [
    {
        "id": "failed_jobs_triage",
        "prompt": (
            "Look at batch inference jobs from the last 48 hours. "
            "Group the FAILED ones by failure_reason, show counts, and "
            "tell me the single most common failure mode and which model_id is most affected."
        ),
    },
    {
        "id": "top_endpoints_latency",
        "prompt": (
            "For the 3 online endpoints with the highest average QPS over the past 7 days, "
            "report their p99 latency trend day-over-day and flag any whose p99 doubled."
        ),
    },
    {
        "id": "model_cost_audit",
        "prompt": (
            "For every model_id, compute total GPU-hours and total cost across all its batch jobs. "
            "Rank models by cost descending and note any model whose average cost-per-job exceeds $50."
        ),
    },
    {
        "id": "alert_correlation",
        "prompt": (
            "Cross-reference HIGH-severity alerts from the last 14 days with endpoint metrics: "
            "for each alerted endpoint, show the metric row from the day the alert fired."
        ),
    },
    {
        "id": "compare_reruns",
        "prompt": (
            "Find the two most recent FAILED batch jobs on model m-llama3-8b-ft, "
            "compare their GPU hours and cost, and recommend whether to retry failed shards "
            "or resubmit the full job."
        ),
    },
]
```

- [ ] **Step 2: Commit**

```bash
git add bench/scenarios.py
git commit -m "feat(bench): add 5 multi-step ml-ops scenarios"
```

---

## Task 7: Benchmark harness

**Files:**
- Create: `bench/run_benchmark.py`

Design notes:
- Uses `mcp` SDK's `stdio_client` + `ClientSession` (not FastMCP's in-process client) so we exercise the real wire protocol.
- Spawns each server with `sys.executable -m servers.classic_server` / `servers.codemode_server`.
- Converts MCP tool list → Anthropic `tools=[{name, description, input_schema}]`.
- Runs an agent loop: while last response has `stop_reason == "tool_use"`, dispatch each `tool_use` block via `session.call_tool`, append `tool_result` blocks, call `messages.create` again.
- Accumulates `usage.input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` across every turn.
- Writes per-(server, scenario) JSON to `bench/results/<timestamp>/<server>__<scenario>.json` containing: prompt, turns, usage totals, final assistant text, list of (tool_name, args) calls, wall-clock seconds.

- [ ] **Step 1: Write `bench/run_benchmark.py`**

```python
import argparse, asyncio, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from bench.scenarios import SCENARIOS

load_dotenv()
MODEL = os.getenv("BENCH_MODEL", "claude-sonnet-4-6")
MAX_TURNS = 20

SERVERS = {
    "classic":  ["-m", "servers.classic_server"],
    "codemode": ["-m", "servers.codemode_server"],
}

def mcp_tools_to_anthropic(tools):
    return [{"name": t.name,
             "description": t.description or "",
             "input_schema": t.inputSchema}
            for t in tools]

def extract_text(blocks):
    return "".join(b.text for b in blocks if b.type == "text")

async def run_scenario(server_key: str, scenario: dict, out_dir: Path):
    params = StdioServerParameters(command=sys.executable, args=SERVERS[server_key])
    client = Anthropic()
    usage_totals = {"input_tokens": 0, "output_tokens": 0,
                    "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    tool_calls = []
    t0 = time.time()

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = mcp_tools_to_anthropic((await session.list_tools()).tools)

            messages = [{"role": "user", "content": scenario["prompt"]}]
            final_text = ""

            for _ in range(MAX_TURNS):
                resp = client.messages.create(
                    model=MODEL, max_tokens=2048, tools=tools, messages=messages,
                )
                u = resp.usage
                for k in usage_totals:
                    usage_totals[k] += getattr(u, k, 0) or 0

                if resp.stop_reason != "tool_use":
                    final_text = extract_text(resp.content)
                    break

                messages.append({"role": "assistant", "content": resp.content})
                tool_results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    tool_calls.append({"name": block.name, "input": block.input})
                    result = await session.call_tool(block.name, block.input)
                    payload = "".join(c.text for c in result.content if c.type == "text") \
                              or json.dumps([c.model_dump() for c in result.content], default=str)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                         "content": payload,
                                         "is_error": bool(result.isError)})
                messages.append({"role": "user", "content": tool_results})

    record = {
        "server": server_key, "scenario_id": scenario["id"], "model": MODEL,
        "prompt": scenario["prompt"], "usage": usage_totals,
        "turns": (len(messages) + 1) // 2, "tool_calls": tool_calls,
        "final_text": final_text, "wall_seconds": round(time.time() - t0, 2),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{server_key}__{scenario['id']}.json").write_text(json.dumps(record, indent=2))
    return record

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--servers", nargs="+", default=list(SERVERS))
    ap.add_argument("--scenarios", nargs="+", default=[s["id"] for s in SCENARIOS])
    args = ap.parse_args()

    run_dir = Path("bench/results") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    selected = [s for s in SCENARIOS if s["id"] in args.scenarios]
    for server_key in args.servers:
        for scenario in selected:
            print(f"[{server_key}] {scenario['id']} ...", flush=True)
            rec = await run_scenario(server_key, scenario, run_dir)
            print(f"  turns={rec['turns']} in={rec['usage']['input_tokens']} "
                  f"out={rec['usage']['output_tokens']} t={rec['wall_seconds']}s")
    print(f"\nResults: {run_dir}")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Smoke test** (requires `ANTHROPIC_API_KEY`)

Run: `codemodevenv/Scripts/python.exe -m bench.run_benchmark --scenarios failed_jobs_triage`
Expected: two JSON files written under `bench/results/<ts>/`; classic run has more turns than codemode run.

- [ ] **Step 3: Commit**

```bash
git add bench/run_benchmark.py
git commit -m "feat(bench): stdio MCP + anthropic agent loop with usage capture"
```

---

## Task 8: Report renderer

**Files:**
- Create: `bench/report.py`

- [ ] **Step 1: Write `bench/report.py`**

```python
import argparse, json
from pathlib import Path
from collections import defaultdict

def render(run_dir: Path) -> str:
    records = [json.loads(p.read_text()) for p in sorted(run_dir.glob("*.json"))]
    by_scenario = defaultdict(dict)
    for r in records:
        by_scenario[r["scenario_id"]][r["server"]] = r

    md = [f"# Benchmark report — `{run_dir.name}`\n",
          "| Scenario | Server | Turns | Input tok | Output tok | Cache read | Wall s |",
          "|---|---|---:|---:|---:|---:|---:|"]
    totals = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "turns": 0})
    for sid, runs in by_scenario.items():
        for server in ("classic", "codemode"):
            r = runs.get(server)
            if not r: continue
            u = r["usage"]
            md.append(f"| {sid} | {server} | {r['turns']} | {u['input_tokens']} | "
                      f"{u['output_tokens']} | {u.get('cache_read_input_tokens',0)} | {r['wall_seconds']} |")
            t = totals[server]
            t["input_tokens"] += u["input_tokens"]; t["output_tokens"] += u["output_tokens"]
            t["turns"] += r["turns"]
    md.append("")
    md.append("## Totals")
    md.append("| Server | Total turns | Total input | Total output |")
    md.append("|---|---:|---:|---:|")
    for server, t in totals.items():
        md.append(f"| {server} | {t['turns']} | {t['input_tokens']} | {t['output_tokens']} |")
    if "classic" in totals and "codemode" in totals:
        c, cm = totals["classic"], totals["codemode"]
        saving = 1 - (cm["input_tokens"] + cm["output_tokens"]) / max(1, c["input_tokens"] + c["output_tokens"])
        md.append(f"\n**Code Mode saved {saving:.1%} of total tokens vs. classic.**")

    md.append("\n## Transcripts\n")
    for sid, runs in by_scenario.items():
        md.append(f"### {sid}\n\n> {runs[next(iter(runs))]['prompt']}\n")
        for server in ("classic", "codemode"):
            r = runs.get(server)
            if not r: continue
            md.append(f"#### {server}\n")
            md.append("**Tool calls:**\n")
            for tc in r["tool_calls"]:
                md.append(f"- `{tc['name']}({json.dumps(tc['input'])[:120]})`")
            md.append(f"\n**Final answer:**\n\n{r['final_text']}\n")
    return "\n".join(md)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("docs/TRANSCRIPTS.md"))
    args = ap.parse_args()
    args.out.write_text(render(args.run_dir), encoding="utf-8")
    print(f"Wrote {args.out}")
```

- [ ] **Step 2: Run report against smoke-test results**

Run: `codemodevenv/Scripts/python.exe -m bench.report bench/results/<ts>`
Expected: `docs/TRANSCRIPTS.md` written with side-by-side table.

- [ ] **Step 3: Commit**

```bash
git add bench/report.py docs/TRANSCRIPTS.md
git commit -m "feat(bench): markdown report with per-scenario + total deltas"
```

---

## Task 9: README and full benchmark run

**Files:**
- Modify: `README.md`
- Copy: plan into `docs/PLAN.md`

- [ ] **Step 1: Write `README.md`** with:
  - Project goal (1 paragraph)
  - Two-server architecture diagram in ASCII
  - How Code Mode differs, with short quotes from the [Anthropic](https://www.anthropic.com/engineering/code-execution-with-mcp) and [Cloudflare](https://blog.cloudflare.com/code-mode-mcp/) posts
  - **Sandbox section:** describe the subprocess isolation model, what's enforced (timeout, restricted builtins, isolated env/cwd, `python -I`), and what's explicitly NOT (CPU/mem cap, network egress). Recommend Cloudflare Workers / Pyodide / nsjail for production.
  - **Secrets:** loud warning that `.env` is gitignored, only `.env.example` is committed, and the pre-commit / pre-push checks from Tasks 1 and 10.
  - Install (`pip install -e ".[dev]"`), how to run each server standalone (`python -m servers.classic_server`), how to run the benchmark end-to-end.
  - "Results" section embedding the latest summary table from `docs/TRANSCRIPTS.md`.

- [ ] **Step 2: Copy plan for teammates**

Run: `cp "C:/Users/vamsh/.claude/plans/i-have-a-requirement-curious-deer.md" docs/PLAN.md`

- [ ] **Step 3: Run full benchmark**

Run: `codemodevenv/Scripts/python.exe -m bench.run_benchmark`
Then: `codemodevenv/Scripts/python.exe -m bench.report bench/results/<latest>`

- [ ] **Step 4: Commit**

```bash
git add README.md docs/PLAN.md docs/TRANSCRIPTS.md
git commit -m "docs: readme, plan copy, and first benchmark report"
```

---

## Task 10: Git setup for user to push

**The user chose "Just init locally, I'll push myself" — do not create a remote or push.**
**API-key safety rule (non-negotiable):** never `git add .env`, never `git add -A` without first confirming `.env` is gitignored. Only `.env.example` with a placeholder value ever gets committed.

- [ ] **Step 1: Final secrets sweep across every commit**

```bash
# Scan every commit on the branch for accidental keys:
git log -p | grep -nE 'sk-ant-[A-Za-z0-9_-]{20,}' && echo "SECRET IN HISTORY — ABORT" || echo "history clean"
# Confirm .env is ignored:
git check-ignore -v .env 2>/dev/null || echo "(no local .env file — fine)"
# Confirm .env is NOT tracked:
git ls-files | grep -E '^\.env$' && echo "TRACKED .env — ABORT" || echo ".env not tracked"
```

All three must be clean before pushing.

- [ ] **Step 2: Confirm working tree clean**

Run: `git status`
Expected: `nothing to commit, working tree clean`.

- [ ] **Step 3: Print push instructions for the user** (do not execute):

```
To push to GitHub:
  1. Create an empty repo on github.com (e.g. mcp-code-mode-demo) — do NOT add README/license.
  2. git remote add origin git@github.com:<you>/mcp-code-mode-demo.git
  3. git branch -M main
  4. git push -u origin main
```

---

## Verification

End-to-end verification that should all pass before declaring the demo ready:

1. **Unit tests:** `pytest tests/ -v` — all backend + both server tests green.
2. **Classic server boots standalone:** `python -m servers.classic_server` starts without error (Ctrl-C to exit). Same for `servers.codemode_server`.
3. **Benchmark run:** `python -m bench.run_benchmark` completes all 5 scenarios × 2 servers without errors. Each scenario produces two JSON records under `bench/results/<ts>/`.
4. **Token delta is material:** In the generated `docs/TRANSCRIPTS.md`, Code Mode total input tokens should be meaningfully lower than classic (expect ~40–80% reduction on multi-step scenarios; exact figure depends on model behavior). Turn count for Code Mode should be ≤ 3 on every scenario; classic is typically 4–10.
5. **Transcripts are readable:** each scenario section shows the tool-call sequence for both servers and the final answer — so a teammate can literally read why Code Mode used fewer turns.

---

## Out of scope (intentionally)

- Language-level isolate sandboxing (Cloudflare Workers / Deno / Pyodide-in-WASM). The subprocess + curated-builtins sandbox in Task 5 is real process isolation with a wall-clock timeout; the README documents the residual risks (no CPU/mem cap on Windows, network syscalls not blocked) and points to proper isolates for production.
- HTTP / SSE transport (stdio only — the benchmark wants deterministic subprocess lifetime).
- CI wiring / GitHub Actions.
- Multi-model comparison — benchmark runs `claude-sonnet-4-6` only, configurable via `BENCH_MODEL`.
