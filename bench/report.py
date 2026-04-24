import argparse, json
from pathlib import Path
from collections import defaultdict

_PREFERRED_ORDER = ["rest_mirror", "task_oriented", "task_codemode"]

_HEADLINE_PAIRS = [
    ("rest_mirror",   "task_oriented", "#1 Gateway-generated vs. hand-designed MCP"),
    ("task_oriented", "task_codemode", "#2 Effect of adding Code Mode on top"),
]


def _server_order(servers: list[str]) -> list[str]:
    preferred = [s for s in _PREFERRED_ORDER if s in servers]
    rest = sorted(s for s in servers if s not in _PREFERRED_ORDER)
    return preferred + rest


def render(run_dir: Path) -> str:
    records = [json.loads(p.read_text()) for p in sorted(run_dir.glob("*.json"))]
    by_scenario = defaultdict(dict)
    for r in records:
        by_scenario[r["scenario_id"]][r["server"]] = r

    servers = _server_order(sorted({r["server"] for r in records}))

    md = [f"# Benchmark report — `{run_dir.name}`\n"]

    totals = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "turns": 0})
    for sid, runs in by_scenario.items():
        for server in servers:
            r = runs.get(server)
            if not r:
                continue
            u = r["usage"]
            t = totals[server]
            t["input_tokens"] += u["input_tokens"]
            t["output_tokens"] += u["output_tokens"]
            t["turns"] += r["turns"]

    md.append("## Headline deltas\n")
    for baseline, candidate, label in _HEADLINE_PAIRS:
        b = totals.get(baseline)
        c = totals.get(candidate)
        if not b or not c:
            continue
        b_total = b["input_tokens"] + b["output_tokens"]
        c_total = c["input_tokens"] + c["output_tokens"]
        if b_total == 0:
            continue
        saving = 1 - c_total / b_total
        md.append(
            f"**{label}** — {candidate} used {saving:.1%} fewer total tokens than {baseline} "
            f"({b['turns']} → {c['turns']} turns)"
        )
    md.append("")

    md.append("## Per-scenario results\n")
    md.append("| Scenario | Server | Turns | Input tok | Output tok | Cache read | Wall s |")
    md.append("|---|---|---:|---:|---:|---:|---:|")
    for sid, runs in by_scenario.items():
        for server in servers:
            r = runs.get(server)
            if not r:
                continue
            u = r["usage"]
            md.append(
                f"| {sid} | {server} | {r['turns']} | {u['input_tokens']} | "
                f"{u['output_tokens']} | {u.get('cache_read_input_tokens', 0)} | {r['wall_seconds']} |"
            )

    md.append("")
    md.append("## Totals")
    md.append("| Server | Total turns | Total input | Total output |")
    md.append("|---|---:|---:|---:|")
    for server in servers:
        t = totals[server]
        md.append(f"| {server} | {t['turns']} | {t['input_tokens']} | {t['output_tokens']} |")

    md.append("")
    md.append("## Token savings (pairwise)")
    any_savings = False
    for i, baseline in enumerate(servers):
        for candidate in servers[i + 1:]:
            b = totals[baseline]
            c = totals[candidate]
            b_total = b["input_tokens"] + b["output_tokens"]
            c_total = c["input_tokens"] + c["output_tokens"]
            if b_total == 0:
                continue
            saving = 1 - c_total / b_total
            md.append(f"- **{candidate}** used {saving:.1%} fewer total tokens than **{baseline}**")
            any_savings = True
    if not any_savings:
        md.append("_(Run multiple servers to see pairwise comparisons.)_")

    md.append("\n## Transcripts\n")
    for sid, runs in by_scenario.items():
        first_run = next(iter(runs.values()))
        md.append(f"### {sid}\n\n> {first_run['prompt']}\n")
        for server in servers:
            r = runs.get(server)
            if not r:
                continue
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
