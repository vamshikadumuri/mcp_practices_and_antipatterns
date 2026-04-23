# MCP Code Mode Demo

## Project Goal

This project demonstrates three progressively better ways to expose the same ML-ops backend
as MCP tools, and measures the token cost difference across five realistic scenarios using the
Anthropic API.

| Server | Tools | Design style |
|---|---:|---|
| `rest_mirror_server` | 22 | Naive REST/OpenAPI mirror — what you get from a gateway auto-converting your Django Swagger JSON |
| `classic_server` | 15 | Hand-written CRUD tools — cleaner naming, no envelopes, but still resource-oriented |
| `task_oriented_server` | 6 | Workflow aggregates — one tool per user intent, single-call answers |
| `codemode_server` | 2 | Code Mode — `list_api` + `execute_python`, model writes and runs its own queries |

Each server is benchmarked against the same five prompts. Token counts and turn counts are
captured at every API call. The report shows exactly where the savings come from.

---

## Architecture

```
                        mlops_backend/data/*.json   (shared synthetic data)
                                     │
                        mlops_backend/data.py
                          /           │           \           \
          rest_api.py    api.py   task_api.py   api.py    api.py
          22 REST        15 RPC   6 workflow    (classic) (codemode)
          primitives     funcs    aggregates
               │            │         │
    rest_mirror_server  classic_server  task_oriented_server  codemode_server
    22 @mcp.tool        15 @mcp.tool    6 @mcp.tool           2 @mcp.tool
    operationId names   clean names     action names          list_api +
    verbose docstrings  CRUD-shaped     concise docstrings    execute_python
    paginated envelopes no envelopes    no envelopes
    stub write ops
               \            │         │               /
                         bench/run_benchmark.py
                         Runs any subset of servers × 5 scenarios
                         Captures input/output/cache tokens per turn
                              │
                         bench/report.py
                         Pairwise token-savings table + transcripts
```

---

## The Antipattern: REST/OpenAPI Mirror

Many teams use an MCP gateway (e.g. IBM mcp-context-forge) to auto-convert a Django app's
OpenAPI 3.0 spec into MCP tools. It works, but it produces tools that are expensive for agents:

**Tool sprawl.** A DRF ViewSet auto-exposes `list / retrieve / create / update / partial_update /
destroy` per resource. Five resources → 22+ tools. Every agent turn re-sends the full tool
schema in the context window, even for tools the agent never uses.

**Pagination loops.** DRF default pagination wraps every list response in
`{count, next, previous, results}`. The agent either follows `next` (extra turns) or stops
short (incomplete results).

**No aggregates.** There is no `compare_these_3_jobs` endpoint in REST. The agent must
list → retrieve-per-id → compute client-side, costing N+1 turns.

**Verbose auto-generated descriptions.** OpenAPI operationIds and drf-spectacular descriptions
add schema weight that is meaningless to the agent but counts as input tokens on every turn.

**Task-oriented tools fix all of this.** `triage_failed_batch_jobs(since_hours=48)` answers
the full "failed jobs" scenario in one call and returns only what the agent needs.

---

## How Code Mode Differs from Task-Oriented Tools

**Task-oriented server** hand-designs one tool per workflow. Six tools cover the six common
ML-ops scenarios. Each tool does its own cross-resource joining and computation server-side.

**Code Mode server** exposes just 2 tools:

| Tool | Purpose |
|---|---|
| `list_api` | Returns docstrings and signatures of all available backend functions |
| `execute_python` | Runs a Python snippet inside an isolated subprocess |

The model's workflow becomes:
1. Call `list_api` once to discover what functions exist.
2. Write a short Python script that calls several backend functions in sequence.
3. Call `execute_python` once — all results in a single round-trip.

This handles scenarios that no pre-designed tool covers. It also carries the smallest tool
schema (2 tools) on every turn. The tradeoff: requires a sandboxed execution environment.

This follows the pattern described by Anthropic at:
https://www.anthropic.com/engineering/code-execution-with-mcp

---

## Sandbox Model

The `execute_python` tool runs submitted code in a subprocess with several guardrails.

### What IS enforced

- **Wall-clock timeout** (default 5 s) — the subprocess is killed if it runs long.
- **Restricted `__builtins__`** — `__import__`, `open`, `eval`, `exec`, `getattr` are removed.
- **Isolated environment and working directory** — clean `env` dict, neutral `cwd`.
- **`python -I` (isolated mode)** — ignores parent `PYTHONPATH` and `site-packages`.

### What is NOT enforced

- **CPU / memory caps** — Python's `resource` module is Unix-only; no equivalent on Windows.
- **Network egress** — syscalls are not intercepted at the OS level.

### Production recommendation

For a production Code Mode deployment exposed to arbitrary users:

- **Language-level isolation:** Cloudflare Workers, Pyodide-in-WASM, or Deno.
- **OS-level isolation:** `nsjail` (Linux) or Docker-per-call.

### Why this demo is safe as-is

The only party submitting code to `execute_python` is Claude, acting on behalf of our own API
key. The guardrails are sufficient for a controlled benchmark environment.

---

## Secrets Warning

**IMPORTANT — Read before cloning.**

- `.env` is listed in `.gitignore` and is **never committed**.
- Only `.env.example` (with placeholder values) lives in the repo.
- To run the benchmark you must:
  1. Copy `.env.example` to `.env`
  2. Replace the placeholder value with your real `ANTHROPIC_API_KEY`
  3. Save the file as **UTF-8** (not UTF-16) — Windows Notepad may default to UTF-16 with BOM,
     which will break the dotenv loader.
- **Never run `git add .env`** — if you do, rotate your key immediately.

---

## Installation and Usage

```bash
# Install (from repo root, using existing venv):
codemodevenv\Scripts\python.exe -m pip install -e ".[dev]"

# Run tests:
codemodevenv\Scripts\python.exe -m pytest tests/ -v

# Run a server standalone (Ctrl-C to stop):
codemodevenv\Scripts\python.exe -m servers.rest_mirror_server
codemodevenv\Scripts\python.exe -m servers.task_oriented_server
codemodevenv\Scripts\python.exe -m servers.classic_server
codemodevenv\Scripts\python.exe -m servers.codemode_server

# Run the full 4-server benchmark (requires ANTHROPIC_API_KEY in .env):
codemodevenv\Scripts\python.exe -m bench.run_benchmark

# Run only the REST-mirror vs task-oriented comparison:
codemodevenv\Scripts\python.exe -m bench.run_benchmark --servers rest_mirror task_oriented

# Run a single scenario for quick testing:
codemodevenv\Scripts\python.exe -m bench.run_benchmark --servers rest_mirror task_oriented --scenarios failed_jobs_triage

# Generate report from a saved run:
codemodevenv\Scripts\python.exe -m bench.report bench/results/<timestamp>
```

---

## Results

_(Run the benchmark to populate this section.)_

<!-- After running the benchmark, paste the table from
     bench/results/<timestamp>/report.md here. -->
