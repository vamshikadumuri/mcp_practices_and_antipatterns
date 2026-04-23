"""
Task-oriented workflow surface — one aggregate per ML-ops user workflow.

Each function answers a complete scenario in a single call, doing all the
cross-resource joining and computation on the server side so the agent
never needs to loop or paginate.
"""
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from . import data


def triage_failed_batch_jobs(
    since_hours: int = 48,
    model_id: str | None = None,
) -> dict:
    """Group failed batch jobs by failure reason; identify most common failure and most affected model."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    rows = [
        r for r in data.load("batch_jobs")
        if r["status"] == "FAILED"
        and datetime.fromisoformat(r["submitted_at"].replace("Z", "+00:00")) >= cutoff
        and (model_id is None or r["model_id"] == model_id)
    ]

    by_reason: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        reason = r.get("failure_reason") or "unknown"
        by_reason[reason].append(r["model_id"])

    ranked = sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True)
    by_failure_reason = [
        {"reason": reason, "count": len(models), "models_affected": sorted(set(models))}
        for reason, models in ranked
    ]

    model_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        model_counts[r["model_id"]] += 1
    most_affected = max(model_counts, key=model_counts.__getitem__) if model_counts else None

    return {
        "since_hours": since_hours,
        "total_failed": len(rows),
        "by_failure_reason": by_failure_reason,
        "most_common_reason": ranked[0][0] if ranked else None,
        "most_affected_model_id": most_affected,
    }


def endpoint_latency_trends(top_n: int = 3, days: int = 7) -> dict:
    """Return top-N endpoints by average QPS with daily p99 trend and a doubled-p99 flag."""
    metrics = data.load("metrics")
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [m for m in metrics if m["date"] >= cutoff_date]

    avg_qps: dict[str, list[float]] = defaultdict(list)
    for m in recent:
        avg_qps[m["endpoint_id"]].append(m["qps"])

    top_ids = sorted(avg_qps, key=lambda eid: sum(avg_qps[eid]) / len(avg_qps[eid]), reverse=True)[:top_n]

    results = []
    for eid in top_ids:
        ep_rows = sorted(
            [m for m in recent if m["endpoint_id"] == eid],
            key=lambda m: m["date"],
        )
        p99_series = [{"date": m["date"], "p99_ms": m["p99_ms"]} for m in ep_rows]
        first_p99 = ep_rows[0]["p99_ms"] if ep_rows else 0
        last_p99 = ep_rows[-1]["p99_ms"] if ep_rows else 0
        results.append({
            "endpoint_id": eid,
            "avg_qps": round(sum(avg_qps[eid]) / len(avg_qps[eid]), 1),
            "p99_trend_ms": p99_series,
            "p99_doubled": last_p99 >= 2 * first_p99,
        })

    return {"days": days, "top_n": top_n, "endpoints": results}


def model_cost_report(threshold_per_job_usd: float = 50.0) -> dict:
    """Rank models by total cost across batch jobs; flag those whose average cost per job exceeds the threshold."""
    jobs = data.load("batch_jobs")

    totals: dict[str, dict] = defaultdict(lambda: {"gpu_hours": 0.0, "cost_usd": 0.0, "jobs": 0})
    for j in jobs:
        m = j["model_id"]
        totals[m]["gpu_hours"] += j.get("gpu_hours") or 0.0
        totals[m]["cost_usd"] += j.get("cost_usd") or 0.0
        totals[m]["jobs"] += 1

    ranked = sorted(totals.items(), key=lambda x: x[1]["cost_usd"], reverse=True)
    rows = []
    for model_id, t in ranked:
        avg = t["cost_usd"] / t["jobs"] if t["jobs"] else 0.0
        rows.append({
            "model_id": model_id,
            "total_gpu_hours": round(t["gpu_hours"], 2),
            "total_cost_usd": round(t["cost_usd"], 2),
            "jobs_count": t["jobs"],
            "avg_cost_per_job_usd": round(avg, 2),
            "exceeds_threshold": avg > threshold_per_job_usd,
        })

    return {"threshold_per_job_usd": threshold_per_job_usd, "models": rows}


def correlate_alerts_with_metrics(severity: str = "HIGH", since_days: int = 14) -> list[dict]:
    """For each alert of the given severity in the last N days, return the endpoint metric row from the day the alert fired."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    alerts = [
        a for a in data.load("alerts")
        if a["severity"] == severity
        and datetime.fromisoformat(a["fired_at"].replace("Z", "+00:00")) >= cutoff
    ]

    metrics_by_ep_date: dict[tuple, dict] = {}
    for m in data.load("metrics"):
        metrics_by_ep_date[(m["endpoint_id"], m["date"])] = m

    results = []
    for a in alerts:
        fired_date = a["fired_at"][:10]
        metric = metrics_by_ep_date.get((a["endpoint_id"], fired_date))
        results.append({
            "alert": a,
            "endpoint_id": a["endpoint_id"],
            "metric_on_fired_date": metric,
        })

    return results


def compare_recent_failed_jobs(model_id: str, n: int = 2) -> dict:
    """Compare the N most recent failed jobs for a model and recommend retry-shards vs full resubmit."""
    jobs = [
        j for j in data.load("batch_jobs")
        if j["model_id"] == model_id and j["status"] == "FAILED"
    ]
    jobs.sort(key=lambda j: j["submitted_at"], reverse=True)
    selected = jobs[:n]

    if len(selected) < 2:
        return {"model_id": model_id, "jobs": selected, "deltas": {}, "recommendation": "insufficient_data"}

    a, b = selected[0], selected[1]
    deltas = {
        "gpu_hours_delta": round((a.get("gpu_hours") or 0) - (b.get("gpu_hours") or 0), 2),
        "cost_usd_delta": round((a.get("cost_usd") or 0) - (b.get("cost_usd") or 0), 2),
    }

    # If fewer than 30% of shards failed, retrying shards is cheaper
    shard_fail_ratio = (a.get("shards_failed") or 0) / max(a.get("shards_total") or 1, 1)
    recommendation = "retry_shards" if shard_fail_ratio < 0.3 else "resubmit_full_job"

    return {
        "model_id": model_id,
        "jobs": selected,
        "deltas": deltas,
        "recommendation": recommendation,
        "shard_fail_ratio": round(shard_fail_ratio, 2),
    }


def apply_traffic_split(endpoint_id: str, splits: dict) -> dict:
    """Apply a traffic split across model versions for an endpoint."""
    return {"endpoint_id": endpoint_id, "applied": splits, "status": "OK"}
