import argparse, asyncio, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, stdio_client
from bench.scenarios import SCENARIOS
from bench import flask_fixture

load_dotenv()
MODEL = os.getenv("BENCH_MODEL", "claude-sonnet-4-6")
MAX_TURNS = 20

SERVERS = {
    "rest_mirror":   ["-m", "servers.rest_mirror_server"],
    "task_oriented": ["-m", "servers.task_oriented_server"],
    "task_codemode": ["-m", "servers.task_codemode_server"],
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
    run_dir.mkdir(parents=True, exist_ok=True)
    selected = [s for s in SCENARIOS if s["id"] in args.scenarios]

    with flask_fixture.running(log_path=run_dir / "flask.log") as info:
        os.environ["MLOPS_API_URL"] = info.url
        for server_key in args.servers:
            for scenario in selected:
                print(f"[{server_key}] {scenario['id']} ...", flush=True)
                rec = await run_scenario(server_key, scenario, run_dir)
                print(f"  turns={rec['turns']} in={rec['usage']['input_tokens']} "
                      f"out={rec['usage']['output_tokens']} t={rec['wall_seconds']}s")
    print(f"\nResults: {run_dir}")

if __name__ == "__main__":
    asyncio.run(main())
