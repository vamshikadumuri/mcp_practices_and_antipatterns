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
