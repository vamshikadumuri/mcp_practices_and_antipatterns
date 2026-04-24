"""MCP-server-side helpers over mlops_backend.api.

NOT part of the backend. This is what an MCP tool author writes on top of the
fixed production REST API: pagination unwrapping, cross-resource joins, and
workflow aggregates.

Pre-imported into the Code Mode sandbox as `mlops`. Also imported by
task_oriented_server and task_codemode_server for their task tool bodies.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from mlops_backend import api as _api


# ---------------------------------------------------------------------------
# Pagination-unwrapping list helpers
# ---------------------------------------------------------------------------

def _collect(fetch_page):
    """Collect all pages into a flat list."""
    rows, page = [], 1
    while True:
        resp = fetch_page(page)
        rows.extend(resp["results"])
        if not resp["next"]:
            return rows
        page += 1

def _since_hours_iso(h):
    return (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat()


def list_batch_jobs(status=None, model_id=None, since_hours=None):
    """Return all batch jobs as a flat list, optionally filtered."""
    sa = _since_hours_iso(since_hours) if since_hours else None
    return _collect(lambda p: _api.list_batch_jobs(
        status=status, model_id=model_id, submitted_after=sa, page=p, page_size=100))

def get_batch_job(job_id):
    """Retrieve a single batch job by id."""
    return _api.retrieve_batch_job(job_id)

def get_batch_job_logs(job_id, lines=50):
    """Return log text (string) for a batch job."""
    return _api.retrieve_batch_job_logs(job_id, lines=lines)["content"]

def retry_failed_shards(job_id):
    """Retry only the failed shards of a batch job."""
    return _api.retry_batch_job_shards(job_id)

def list_models():
    """Return all models as a flat list."""
    return _collect(lambda p: _api.list_models(page=p, page_size=100))

def get_model(model_id):
    """Retrieve a single model by id."""
    return _api.retrieve_model(model_id)

def list_datasets():
    """Return all datasets as a flat list."""
    return _collect(lambda p: _api.list_datasets(page=p, page_size=100))

def get_dataset(dataset_id):
    """Retrieve a single dataset by id."""
    return _api.retrieve_dataset(dataset_id)

def list_endpoints(status=None):
    """Return all endpoints as a flat list, optionally filtered by status."""
    return _collect(lambda p: _api.list_endpoints(status=status, page=p, page_size=100))

def get_endpoint(endpoint_id):
    """Retrieve a single endpoint by id."""
    return _api.retrieve_endpoint(endpoint_id)

def get_endpoint_metrics(endpoint_id, days=7):
    """Return all metric rows for an endpoint as a flat list."""
    return _collect(lambda p: _api.list_endpoint_metrics(
        endpoint_id, days=days, page=p, page_size=100))

def update_traffic_split(endpoint_id, splits):
    """Apply a traffic split across model versions for an endpoint."""
    return _api.update_endpoint_traffic(endpoint_id, splits)

def tail_endpoint_logs(endpoint_id, lines=50):
    """Return log text (string) for an endpoint."""
    return _api.retrieve_endpoint_logs(endpoint_id, lines=lines)["content"]

def list_alerts(severity=None):
    """Return all alerts as a flat list, optionally filtered by severity."""
    return _collect(lambda p: _api.list_alerts(severity=severity, page=p, page_size=100))

def compare_runs(job_ids):
    """Compare multiple batch jobs by gpu_hours, cost_usd, and status."""
    jobs = [get_batch_job(j) for j in job_ids]
    return {
        "job_ids": job_ids,
        "gpu_hours": {j["job_id"]: j["gpu_hours"] for j in jobs},
        "cost_usd":  {j["job_id"]: j["cost_usd"]  for j in jobs},
        "status":    {j["job_id"]: j["status"]    for j in jobs},
    }


# ---------------------------------------------------------------------------
# Task / workflow aggregates
# ---------------------------------------------------------------------------

def triage_failed_batch_jobs(since_hours=48, model_id=None):
    """Group failed batch jobs by failure reason; return counts, most common failure, most affected model."""
    jobs = list_batch_jobs(status="FAILED", model_id=model_id, since_hours=since_hours)
    by_reason = defaultdict(list)
    for j in jobs:
        reason = j.get("failure_reason") or "unknown"
        by_reason[reason].append(j["model_id"])

    ranked = sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True)
    by_failure_reason = [
        {"reason": r, "count": len(ms), "models_affected": sorted(set(ms))}
        for r, ms in ranked
    ]
    model_counts = Counter(j["model_id"] for j in jobs)
    most_affected = model_counts.most_common(1)[0][0] if model_counts else None

    return {
        "since_hours": since_hours,
        "total_failed": len(jobs),
        "by_failure_reason": by_failure_reason,
        "most_common_reason": ranked[0][0] if ranked else None,
        "most_affected_model_id": most_affected,
    }


def endpoint_latency_trends(top_n=3, days=7):
    """Return top-N endpoints by avg QPS with daily p99 trend and a doubled-p99 flag."""
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    all_endpoints = list_endpoints()
    all_metrics = []
    for ep in all_endpoints:
        all_metrics.extend(get_endpoint_metrics(ep["endpoint_id"], days=days))

    recent = [m for m in all_metrics if m["date"] >= cutoff_date]

    avg_qps = defaultdict(list)
    for m in recent:
        avg_qps[m["endpoint_id"]].append(m["qps"])

    top_ids = sorted(avg_qps, key=lambda eid: sum(avg_qps[eid]) / len(avg_qps[eid]), reverse=True)[:top_n]

    results = []
    for eid in top_ids:
        ep_rows = sorted([m for m in recent if m["endpoint_id"] == eid], key=lambda m: m["date"])
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


def model_cost_report(threshold_per_job_usd=50.0):
    """Rank models by total cost across batch jobs; flag those whose avg cost-per-job exceeds the threshold."""
    jobs = list_batch_jobs()
    totals = defaultdict(lambda: {"gpu_hours": 0.0, "cost_usd": 0.0, "jobs": 0})
    for j in jobs:
        m = j["model_id"]
        totals[m]["gpu_hours"] += j.get("gpu_hours") or 0.0
        totals[m]["cost_usd"]  += j.get("cost_usd")  or 0.0
        totals[m]["jobs"] += 1

    ranked = sorted(totals.items(), key=lambda x: x[1]["cost_usd"], reverse=True)
    rows = []
    for mid, t in ranked:
        avg = t["cost_usd"] / t["jobs"] if t["jobs"] else 0.0
        rows.append({
            "model_id": mid,
            "total_gpu_hours": round(t["gpu_hours"], 2),
            "total_cost_usd": round(t["cost_usd"], 2),
            "jobs_count": t["jobs"],
            "avg_cost_per_job_usd": round(avg, 2),
            "exceeds_threshold": avg > threshold_per_job_usd,
        })
    return {"threshold_per_job_usd": threshold_per_job_usd, "models": rows}


def correlate_alerts_with_metrics(severity="HIGH", since_days=14):
    """For each alert of the given severity in the last N days, return the endpoint metric row from the day it fired."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    alerts = [
        a for a in list_alerts(severity=severity)
        if datetime.fromisoformat(a["fired_at"].replace("Z", "+00:00")) >= cutoff
    ]

    results = []
    for a in alerts:
        fired_date = a["fired_at"][:10]
        metrics = get_endpoint_metrics(a["endpoint_id"], days=since_days)
        metric = next((m for m in metrics if m["date"] == fired_date), None)
        results.append({
            "alert": a,
            "endpoint_id": a["endpoint_id"],
            "metric_on_fired_date": metric,
        })
    return results


def compare_recent_failed_jobs(model_id, n=2):
    """Compare the N most recent failed jobs for a model and recommend retry-shards vs full resubmit."""
    jobs = [j for j in list_batch_jobs(status="FAILED", model_id=model_id)]
    jobs.sort(key=lambda j: j["submitted_at"], reverse=True)
    selected = jobs[:n]

    if len(selected) < 2:
        return {"model_id": model_id, "jobs": selected, "deltas": {}, "recommendation": "insufficient_data"}

    a, b = selected[0], selected[1]
    deltas = {
        "gpu_hours_delta": round((a.get("gpu_hours") or 0) - (b.get("gpu_hours") or 0), 2),
        "cost_usd_delta":  round((a.get("cost_usd")  or 0) - (b.get("cost_usd")  or 0), 2),
    }
    shard_fail_ratio = (a.get("shards_failed") or 0) / max(a.get("shards_total") or 1, 1)
    recommendation = "retry_shards" if shard_fail_ratio < 0.3 else "resubmit_full_job"
    return {
        "model_id": model_id,
        "jobs": selected,
        "deltas": deltas,
        "recommendation": recommendation,
        "shard_fail_ratio": round(shard_fail_ratio, 2),
    }


def apply_traffic_split(endpoint_id, splits):
    """Apply a traffic split across model versions for an endpoint."""
    return update_traffic_split(endpoint_id, splits)
