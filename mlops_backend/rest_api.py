"""
REST primitive surface — mirrors what a Django + DRF ViewSet app would expose.

Each list op returns the DRF default pagination envelope:
  {count, next, previous, results}

Stub write ops (create_*, partial_update_*, destroy_*) return placeholder responses;
they exist so the OpenAPI spec — and therefore every MCP tool schema — is complete,
even though no benchmark scenario ever calls them. That unreduced schema overhead is
exactly the antipattern this module is here to demonstrate.
"""
from datetime import datetime, timezone
from . import data

_API_ROOT = "http://api.local"


def _paginate(rows: list[dict], page: int, page_size: int, base_url: str) -> dict:
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]
    next_url = f"{base_url}?page={page+1}&page_size={page_size}" if end < total else None
    prev_url = f"{base_url}?page={page-1}&page_size={page_size}" if page > 1 else None
    return {"count": total, "next": next_url, "previous": prev_url, "results": page_rows}


# ---------------------------------------------------------------------------
# Batch jobs
# ---------------------------------------------------------------------------

def list_batch_jobs(
    status: str | None = None,
    model_id: str | None = None,
    submitted_after: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    rows = data.load("batch_jobs")
    if status:
        rows = [r for r in rows if r["status"] == status]
    if model_id:
        rows = [r for r in rows if r["model_id"] == model_id]
    if submitted_after:
        cutoff = datetime.fromisoformat(submitted_after.replace("Z", "+00:00"))
        rows = [r for r in rows
                if datetime.fromisoformat(r["submitted_at"].replace("Z", "+00:00")) >= cutoff]
    return _paginate(rows, page, page_size, f"{_API_ROOT}/batch_jobs/")


def retrieve_batch_job(job_id: str) -> dict:
    for r in data.load("batch_jobs"):
        if r["job_id"] == job_id:
            return r
    raise KeyError(job_id)


def create_batch_job(model_id: str, dataset_id: str, shards_total: int = 16) -> dict:
    return {
        "job_id": "bj-stub-new",
        "model_id": model_id,
        "dataset_id": dataset_id,
        "status": "PENDING",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "shards_total": shards_total,
        "shards_failed": 0,
        "gpu_hours": None,
        "cost_usd": None,
        "failure_reason": None,
    }


def destroy_batch_job(job_id: str) -> dict:
    return {"job_id": job_id, "status": "CANCELLED"}


def retrieve_batch_job_logs(job_id: str, lines: int = 50) -> dict:
    job = retrieve_batch_job(job_id)
    header = f"[job {job_id} model={job['model_id']} status={job['status']}]"
    body = "\n".join(f"step {i:04d} loss=..." for i in range(lines))
    tail = f"\n{job.get('failure_reason', '')}" if job["status"] == "FAILED" else ""
    return {"job_id": job_id, "lines": lines, "content": header + "\n" + body + tail}


def retry_batch_job_shards(job_id: str) -> dict:
    job = retrieve_batch_job(job_id)
    return {"job_id": job_id, "retried_shards": job.get("shards_failed", 0), "new_job_id": f"{job_id}-r1"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def list_models(page: int = 1, page_size: int = 20) -> dict:
    return _paginate(data.load("models"), page, page_size, f"{_API_ROOT}/models/")


def retrieve_model(model_id: str) -> dict:
    for m in data.load("models"):
        if m["model_id"] == model_id:
            return m
    raise KeyError(model_id)


def create_model(name: str, version: str) -> dict:
    return {"model_id": "m-stub-new", "name": name, "version": version, "status": "registered"}


def partial_update_model(model_id: str, **fields) -> dict:
    return {"model_id": model_id, "updated_fields": list(fields.keys()), "status": "ok"}


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

def list_datasets(page: int = 1, page_size: int = 20) -> dict:
    return _paginate(data.load("datasets"), page, page_size, f"{_API_ROOT}/datasets/")


def retrieve_dataset(dataset_id: str) -> dict:
    for d in data.load("datasets"):
        if d["dataset_id"] == dataset_id:
            return d
    raise KeyError(dataset_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def list_endpoints(status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    rows = data.load("endpoints")
    if status:
        rows = [r for r in rows if r["status"] == status]
    return _paginate(rows, page, page_size, f"{_API_ROOT}/endpoints/")


def retrieve_endpoint(endpoint_id: str) -> dict:
    for e in data.load("endpoints"):
        if e["endpoint_id"] == endpoint_id:
            return e
    raise KeyError(endpoint_id)


def create_endpoint(name: str, model_id: str) -> dict:
    return {"endpoint_id": "ep-stub-new", "name": name, "model_id": model_id, "status": "PENDING"}


def destroy_endpoint(endpoint_id: str) -> dict:
    return {"endpoint_id": endpoint_id, "status": "DECOMMISSIONED"}


def partial_update_endpoint(endpoint_id: str, **fields) -> dict:
    return {"endpoint_id": endpoint_id, "updated_fields": list(fields.keys()), "status": "ok"}


def list_endpoint_metrics(
    endpoint_id: str, days: int = 7, page: int = 1, page_size: int = 20
) -> dict:
    rows = [m for m in data.load("metrics") if m["endpoint_id"] == endpoint_id]
    rows.sort(key=lambda r: r["date"], reverse=True)
    rows = rows[:days]
    return _paginate(rows, page, page_size, f"{_API_ROOT}/endpoints/{endpoint_id}/metrics/")


def retrieve_endpoint_logs(endpoint_id: str, lines: int = 50) -> dict:
    ep = retrieve_endpoint(endpoint_id)
    content = f"[endpoint {endpoint_id} model={ep['model_id']}]\n" + \
              "\n".join(f"req {i} 200 latency_ms=..." for i in range(lines))
    return {"endpoint_id": endpoint_id, "lines": lines, "content": content}


def update_endpoint_traffic(endpoint_id: str, splits: dict) -> dict:
    return {"endpoint_id": endpoint_id, "applied": splits, "status": "OK"}


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def list_alerts(
    severity: str | None = None,
    fired_after: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    rows = data.load("alerts")
    if severity:
        rows = [r for r in rows if r["severity"] == severity]
    if fired_after:
        cutoff = datetime.fromisoformat(fired_after.replace("Z", "+00:00"))
        rows = [r for r in rows
                if datetime.fromisoformat(r["fired_at"].replace("Z", "+00:00")) >= cutoff]
    return _paginate(rows, page, page_size, f"{_API_ROOT}/alerts/")


def retrieve_alert(alert_id: str) -> dict:
    for a in data.load("alerts"):
        if a["alert_id"] == alert_id:
            return a
    raise KeyError(alert_id)
