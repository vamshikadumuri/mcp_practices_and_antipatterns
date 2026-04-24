# MCP Code Mode Demo

## Goal

Three MCP servers expose the same ML-ops Flask backend. Two focused comparisons
let an ML-ops team answer concrete questions about how they should build their
own MCP layer.

| # | Server | Tools | Role |
|---|---|---:|---|
| 1 | `rest_mirror_server` | 22 | What an auto-generating MCP gateway produces from the Swagger spec |
| 2 | `task_oriented_server` | 6 | Thoughtfully hand-designed workflow aggregates |
| 3 | `task_codemode_server` | 6 + 2 | Same 6 task tools, plus `list_api` + `execute_python` as an escape hatch |

**Comparison #1 — gateway-generated vs. hand-designed MCP**
Does the extra effort of writing task tools pay off vs. auto-generating from OpenAPI?

**Comparison #2 — task tools vs. task tools + Code Mode**
Does adding Code Mode earn its keep on top of a strong task-tool baseline?

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  mlops_backend/flask_app.py  — real Flask app (subprocess)  │
│  DRF-style endpoints over data/*.json                       │
│  "Production": fixed shape, fixed behavior.                 │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ HTTP (requests)
          ┌─────────────────┴────────────────────────┐
          │  mlops_backend/api.py                    │
          │  REST client ONLY — 1:1 with Flask.      │
          │  Preserves pagination envelopes exactly. │
          │  No unwrapping, no composition.          │
          └────┬───────────────────────────┬─────────┘
               │                           │
    ┌──────────▼────────────┐   ┌──────────▼──────────────────────┐
    │ rest_mirror_server.py │   │ servers/mlops.py                │
    │ 22 @mcp.tool          │   │ MCP-side helpers (NOT backend): │
    │ verbose OAS docstrings│   │  - pagination-unwrapping lists  │
    │ pagination envelopes  │   │  - 6 workflow aggregates        │
    │ stub write tools      │   └──────────┬──────────┬───────────┘
    └───────────────────────┘              │          │
                               ┌───────────▼──┐   ┌───▼───────────────────┐
                               │ task_oriented│   │ task_codemode_server  │
                               │ _server      │   │ 6 task tools          │
                               │ 6 @mcp.tool  │   │ + list_api            │
                               │              │   │ + execute_python      │
                               └──────────────┘   └───────────────────────┘
```

**The invariant:** `mlops_backend/api.py` is a pure REST client — nothing more.
Every MCP server builds its own helpers in `servers/mlops.py` on top of the fixed
backend. This mirrors production reality: the backend is owned by a different team
and its shape is fixed. The MCP layer is where you decide how to expose it.

---

## Comparison #1 — REST-mirror vs. Task-oriented

An auto-generating gateway (IBM mcp-context-forge, any OpenAPI→MCP converter)
applied to a Django/DRF Swagger spec produces tools like the REST-mirror server.
A human writing task tools produces the task-oriented server. Four things change
together:

| Dimension | REST-mirror | Task-oriented |
|---|---|---|
| Tool count | 22 | 6 |
| Schema per turn | Full 22-tool schema on every API call | 6 compact tool schemas |
| List responses | DRF pagination envelopes (`count/next/previous/results`) | Flat lists, fully unwrapped |
| Write stubs | Yes — `create_*`, `destroy_*`, `partial_update_*` inflate schema even if never called | No |

The agent working with REST-mirror must loop over pagination to collect all results,
call N+1 endpoints to answer a cross-resource question, and carry the bloated schema
on every turn. The task tool returns the complete answer in one call.

---

## Comparison #2 — Task-oriented vs. Task-oriented + Code Mode

The `task_codemode_server` carries the same 6 task tools plus two Code Mode tools:

| Tool | Purpose |
|---|---|
| `list_api` | Returns signatures and docstrings of all helpers in `servers/mlops.py` |
| `execute_python` | Runs a Python snippet in a sandboxed subprocess; `mlops` pre-imported |

On the five standard scenarios, both servers should perform similarly — the agent
uses the matching task tool in both cases. The sixth scenario (`model_failure_by_dataset`)
has no matching task tool: the `task_oriented_server` must stitch together multiple
primitives across turns, while `task_codemode_server` answers it in one
`execute_python` call. The schema overhead of carrying two extra tools on every turn
is the honest cost on the other side.

---

## "Production is fixed" framing

`mlops_backend/api.py` represents exactly what a production Flask/DRF app exposes
over HTTP. It is a 1:1 REST client — no pagination unwrapping, no composition, no
aggregation. Reading it alone, a reviewer sees only HTTP calls that mirror Flask
endpoints.

`servers/mlops.py` is what any MCP tool author would write on top of that fixed
backend: helpers that unwrap pagination, join resources, and compute workflow
aggregates. It is explicitly **not** part of the backend.

---

## Sandbox model

`execute_python` runs submitted code in a subprocess with these guardrails:

- **Wall-clock timeout** (5 s default) — subprocess is killed if exceeded
- **Restricted `__builtins__`** — `__import__`, `open`, `eval`, `exec`, `getattr` removed
- **Isolated environment** — clean env dict, neutral cwd, `python -I` (ignores PYTHONPATH/site-packages from parent)

CPU/memory caps and network egress are not enforced (no `resource` module on Windows).
For production, use Cloudflare Workers, Pyodide-in-WASM, or Docker-per-call.

---

## Secrets warning

`.env` is in `.gitignore` and never committed. To run the benchmark:

1. Copy `.env.example` to `.env`
2. Set `ANTHROPIC_API_KEY` to your real key
3. Save as **UTF-8** (not UTF-16 — Windows Notepad may default to UTF-16 with BOM)

---

## Installation and usage

```bash
# Install (venv must be active or use full path):
codemodevenv\Scripts\python.exe -m pip install -e ".[dev]"

# Verify tests pass:
codemodevenv\Scripts\python.exe -m pytest tests/ -v

# Run Flask standalone (Ctrl-C to stop):
codemodevenv\Scripts\python.exe -m mlops_backend.flask_app

# Run an MCP server standalone (Flask must be running first):
codemodevenv\Scripts\python.exe -m servers.rest_mirror_server
codemodevenv\Scripts\python.exe -m servers.task_oriented_server
codemodevenv\Scripts\python.exe -m servers.task_codemode_server

# Run the full 3-server benchmark (starts Flask automatically):
codemodevenv\Scripts\python.exe -m bench.run_benchmark

# Subset — comparison #1 only, one scenario:
codemodevenv\Scripts\python.exe -m bench.run_benchmark --servers rest_mirror task_oriented --scenarios failed_jobs_triage

# Comparison #2 only, novel scenario:
codemodevenv\Scripts\python.exe -m bench.run_benchmark --servers task_oriented task_codemode --scenarios model_failure_by_dataset

# Generate report from a saved run:
codemodevenv\Scripts\python.exe -m bench.report bench/results/<timestamp>
```

---

## Results

_(Run the benchmark to populate this section.)_

<!-- After running the benchmark, paste the Headline deltas + Totals table from
     bench/results/<timestamp>/report.md here. -->
