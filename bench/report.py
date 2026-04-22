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
