# MCP Code Mode Demo

## Project Goal

This project demonstrates Anthropic's Code Mode MCP pattern — where an AI assistant gets two
tools (`list_api` + `execute_python`) instead of 15 individual tools — and measures the token
savings on apples-to-apples ML-ops scenarios using the Anthropic API. The benchmark runs the
same five realistic ML-ops prompts through both a classic 15-tool server and a Code Mode 2-tool
server, captures input/output token counts at every API turn, and renders a side-by-side report
so you can see exactly where the savings come from.

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │      mlops_backend/api.py    │
                    │   15 typed Python functions  │
                    └──────────┬──────────────────┘
                               │ imported by
            ┌──────────────────┼──────────────────┐
            │                  │                  │
  ┌─────────▼──────┐  ┌────────▼──────────┐      │
  │ classic_server  │  │ codemode_server   │      │
  │ 15 @mcp.tool   │  │ 2 tools only:     │      │
  │ functions      │  │  • list_api       │      │
  └────────────────┘  │  • execute_python │      │
                      └───────────────────┘      │
                                                  │
                      ┌───────────────────────────┘
                      │ bench/run_benchmark.py
                      │ Anthropic API + mcp stdio
                      │ Runs same 5 prompts through
                      │ both servers, captures usage
                      └──────────────────────────
```

---

## How Code Mode Differs from Classic Tool Use

**Classic server** exposes 15 individual MCP tools — one per ML-ops operation (e.g.,
`list_failed_jobs`, `get_model_metrics`, `trigger_retraining`, ...). When the model handles a
multi-step scenario it must call each tool in a separate API turn. Critically, every single
request carries the **full 15-tool JSON schema** in the system context, which inflates input
tokens on every turn.

**Code Mode server** exposes just 2 tools:

| Tool | Purpose |
|---|---|
| `list_api` | Returns the docstrings and signatures of all available backend functions |
| `execute_python` | Runs a snippet of Python code inside an isolated subprocess |

The model's workflow becomes:
1. Call `list_api` once to discover what functions exist.
2. Write a short Python script that calls several backend functions in sequence.
3. Call `execute_python` once — getting all results in a single round-trip.

This collapses a 4–6 turn classic conversation into 2–3 turns, and cuts per-turn token
overhead from a 15-tool schema down to a 2-tool schema. At scale the savings compound: fewer
turns means fewer full-context re-sends.

This follows the pattern described by Anthropic at:
https://www.anthropic.com/engineering/code-execution-with-mcp

---

## Sandbox Model

The `execute_python` tool runs submitted code in a subprocess with several guardrails.

### What IS enforced

- **Wall-clock timeout** (default 5 s) — the subprocess is killed if it runs long.
- **Restricted `__builtins__`** — the following are removed from the execution namespace:
  `__import__`, `open`, `eval`, `exec`, `getattr`. This blocks the most common escape hatches
  without requiring a full language sandbox.
- **Isolated environment and working directory** — the subprocess receives a clean `env` dict
  and runs in a neutral `cwd`, not the repo root.
- **`python -I` (isolated mode)** — ignores the parent process's `PYTHONPATH` and
  `site-packages`, so the executed code cannot import arbitrary installed packages.

### What is NOT enforced

- **CPU / memory caps** — Python's `resource` module is Unix-only. Windows has no equivalent
  in the standard library and Job Objects are not wired up here.
- **Network egress** — syscalls are not intercepted at the OS level. Code could open a socket
  if `socket` were importable (it isn't via `__import__` removal, but a determined attacker
  could work around this).

### Production recommendation

For a production Code Mode deployment exposed to arbitrary users:

- **Language-level isolation:** Cloudflare Workers, Pyodide-in-WASM, or Deno provide true
  sandboxing with memory/CPU limits and no native syscalls.
- **OS-level isolation:** `nsjail` (Linux) or Docker-per-call gives full process namespace
  isolation with network and filesystem controls.

### Why this demo is safe as-is

The only party submitting code to `execute_python` is Claude, acting on behalf of our own API
key. We are not exposing this endpoint to arbitrary external users. The guardrails are
sufficient for a controlled benchmark environment.

---

## Secrets Warning

**IMPORTANT — Read before cloning.**

- `.env` is listed in `.gitignore` and is **never committed**.
- Only `.env.example` (with placeholder values) lives in the repo.
- To run the benchmark you must:
  1. Copy `.env.example` to `.env`
  2. Replace the placeholder value with your real `ANTHROPIC_API_KEY`
- **Never run `git add .env`** — if you do, rotate your key immediately.

---

## Installation and Usage

```bash
# Install (from repo root, using existing venv):
codemodevenv\Scripts\python.exe -m pip install -e ".[dev]"

# Run tests:
codemodevenv\Scripts\python.exe -m pytest tests/ -v

# Run a server standalone (Ctrl-C to stop):
codemodevenv\Scripts\python.exe -m servers.classic_server
codemodevenv\Scripts\python.exe -m servers.codemode_server

# Run the full benchmark (requires ANTHROPIC_API_KEY in .env):
codemodevenv\Scripts\python.exe -m bench.run_benchmark

# Run a single scenario for quick testing:
codemodevenv\Scripts\python.exe -m bench.run_benchmark --scenarios failed_jobs_triage

# Generate report from a saved run:
codemodevenv\Scripts\python.exe -m bench.report bench/results/<timestamp>
```

---

## Results

_(Run the benchmark to populate this section.)_

<!-- After running `python -m bench.run_benchmark`, paste the table from
     bench/results/<timestamp>/report.md here. -->
