"""Real Flask ML-ops backend — DRF-style responses.

This is "production": fixed shape, fixed behavior. MCP tool authors
call this via HTTP (through mlops_backend/api.py). They do not modify this file.

Run standalone:
    python -m mlops_backend.flask_app
"""
import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from . import data

app = Flask(__name__)
_API_ROOT = os.getenv("MLOPS_API_URL", "http://127.0.0.1:7319")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _paginate(rows: list, page: int, page_size: int, base_path: str) -> dict:
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    base_url = _API_ROOT.rstrip("/") + base_path
    next_url = f"{base_url}?page={page+1}&page_size={page_size}" if end < total else None
    prev_url = f"{base_url}?page={page-1}&page_size={page_size}" if page > 1 else None
    return {"count": total, "next": next_url, "previous": prev_url, "results": rows[start:end]}


def _not_found(msg="Not found."):
    return jsonify({"detail": msg}), 404


def _bad_request(msg):
    return jsonify({"detail": msg}), 400


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Batch jobs
# ---------------------------------------------------------------------------

@app.route("/batch_jobs/")
def batch_jobs_list():
    status = request.args.get("status")
    model_id = request.args.get("model_id")
    submitted_after = request.args.get("submitted_after")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    rows = data.load("batch_jobs")
    if status:
        rows = [r for r in rows if r["status"] == status]
    if model_id:
        rows = [r for r in rows if r["model_id"] == model_id]
    if submitted_after:
        cutoff = datetime.fromisoformat(submitted_after.replace("Z", "+00:00"))
        rows = [r for r in rows
                if datetime.fromisoformat(r["submitted_at"].replace("Z", "+00:00")) >= cutoff]
    return jsonify(_paginate(rows, page, page_size, "/batch_jobs/"))


@app.route("/batch_jobs/<job_id>/")
def batch_jobs_retrieve(job_id):
    for r in data.load("batch_jobs"):
        if r["job_id"] == job_id:
            return jsonify(r)
    return _not_found()


@app.route("/batch_jobs/", methods=["POST"])
def batch_jobs_create():
    body = request.get_json(force=True) or {}
    model_id = body.get("model_id")
    dataset_id = body.get("dataset_id")
    if not model_id or not dataset_id:
        return _bad_request("model_id and dataset_id are required.")
    shards_total = int(body.get("shards_total", 16))
    return jsonify({
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
    }), 201


@app.route("/batch_jobs/<job_id>/", methods=["DELETE"])
def batch_jobs_destroy(job_id):
    for r in data.load("batch_jobs"):
        if r["job_id"] == job_id:
            return jsonify({"job_id": job_id, "status": "CANCELLED"})
    return _not_found()


@app.route("/batch_jobs/<job_id>/logs/")
def batch_jobs_logs(job_id):
    lines = int(request.args.get("lines", 50))
    for r in data.load("batch_jobs"):
        if r["job_id"] == job_id:
            header = f"[job {job_id} model={r['model_id']} status={r['status']}]"
            body = "\n".join(f"step {i:04d} loss=..." for i in range(lines))
            tail = f"\n{r.get('failure_reason', '')}" if r["status"] == "FAILED" else ""
            return jsonify({"job_id": job_id, "lines": lines, "content": header + "\n" + body + tail})
    return _not_found()


@app.route("/batch_jobs/<job_id>/retry_shards/", methods=["POST"])
def batch_jobs_retry_shards(job_id):
    for r in data.load("batch_jobs"):
        if r["job_id"] == job_id:
            if not r.get("shards_failed"):
                return _bad_request("Job has no failed shards.")
            return jsonify({
                "job_id": job_id,
                "retried_shards": r["shards_failed"],
                "new_job_id": f"{job_id}-r1",
            }), 201
    return _not_found()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@app.route("/models/")
def models_list():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    return jsonify(_paginate(data.load("models"), page, page_size, "/models/"))


@app.route("/models/<model_id>/")
def models_retrieve(model_id):
    for m in data.load("models"):
        if m["model_id"] == model_id:
            return jsonify(m)
    return _not_found()


@app.route("/models/", methods=["POST"])
def models_create():
    body = request.get_json(force=True) or {}
    name = body.get("name")
    version = body.get("version")
    if not name or not version:
        return _bad_request("name and version are required.")
    return jsonify({"model_id": "m-stub-new", "name": name, "version": version,
                    "status": "registered"}), 201


@app.route("/models/<model_id>/", methods=["PATCH"])
def models_partial_update(model_id):
    for m in data.load("models"):
        if m["model_id"] == model_id:
            body = request.get_json(force=True) or {}
            return jsonify({"model_id": model_id, "updated_fields": list(body.keys()), "status": "ok"})
    return _not_found()


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

@app.route("/datasets/")
def datasets_list():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    return jsonify(_paginate(data.load("datasets"), page, page_size, "/datasets/"))


@app.route("/datasets/<dataset_id>/")
def datasets_retrieve(dataset_id):
    for d in data.load("datasets"):
        if d["dataset_id"] == dataset_id:
            return jsonify(d)
    return _not_found()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/endpoints/")
def endpoints_list():
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    rows = data.load("endpoints")
    if status:
        rows = [r for r in rows if r["status"] == status]
    return jsonify(_paginate(rows, page, page_size, "/endpoints/"))


@app.route("/endpoints/<endpoint_id>/")
def endpoints_retrieve(endpoint_id):
    for e in data.load("endpoints"):
        if e["endpoint_id"] == endpoint_id:
            return jsonify(e)
    return _not_found()


@app.route("/endpoints/", methods=["POST"])
def endpoints_create():
    body = request.get_json(force=True) or {}
    name = body.get("name")
    model_id = body.get("model_id")
    if not name or not model_id:
        return _bad_request("name and model_id are required.")
    return jsonify({"endpoint_id": "ep-stub-new", "name": name, "model_id": model_id,
                    "status": "PENDING"}), 201


@app.route("/endpoints/<endpoint_id>/", methods=["DELETE"])
def endpoints_destroy(endpoint_id):
    for e in data.load("endpoints"):
        if e["endpoint_id"] == endpoint_id:
            return jsonify({"endpoint_id": endpoint_id, "status": "DECOMMISSIONED"})
    return _not_found()


@app.route("/endpoints/<endpoint_id>/", methods=["PATCH"])
def endpoints_partial_update(endpoint_id):
    for e in data.load("endpoints"):
        if e["endpoint_id"] == endpoint_id:
            body = request.get_json(force=True) or {}
            return jsonify({"endpoint_id": endpoint_id, "updated_fields": list(body.keys()), "status": "ok"})
    return _not_found()


@app.route("/endpoints/<endpoint_id>/metrics/")
def endpoints_metrics_list(endpoint_id):
    days = int(request.args.get("days", 7))
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    rows = [m for m in data.load("metrics") if m["endpoint_id"] == endpoint_id]
    rows.sort(key=lambda r: r["date"], reverse=True)
    rows = rows[:days]
    return jsonify(_paginate(rows, page, page_size, f"/endpoints/{endpoint_id}/metrics/"))


@app.route("/endpoints/<endpoint_id>/logs/")
def endpoints_logs(endpoint_id):
    lines = int(request.args.get("lines", 50))
    for e in data.load("endpoints"):
        if e["endpoint_id"] == endpoint_id:
            content = f"[endpoint {endpoint_id} model={e['model_id']}]\n" + \
                      "\n".join(f"req {i} 200 latency_ms=..." for i in range(lines))
            return jsonify({"endpoint_id": endpoint_id, "lines": lines, "content": content})
    return _not_found()


@app.route("/endpoints/<endpoint_id>/traffic/", methods=["PATCH"])
def endpoints_traffic_update(endpoint_id):
    for e in data.load("endpoints"):
        if e["endpoint_id"] == endpoint_id:
            body = request.get_json(force=True) or {}
            splits = body.get("splits", {})
            total = sum(splits.values()) if splits else 0
            if splits and abs(total - 100) > 0.01:
                return _bad_request("Percentages must sum to 100.")
            return jsonify({"endpoint_id": endpoint_id, "applied": splits, "status": "OK"})
    return _not_found()


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@app.route("/alerts/")
def alerts_list():
    severity = request.args.get("severity")
    fired_after = request.args.get("fired_after")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    rows = data.load("alerts")
    if severity:
        rows = [r for r in rows if r["severity"] == severity]
    if fired_after:
        cutoff = datetime.fromisoformat(fired_after.replace("Z", "+00:00"))
        rows = [r for r in rows
                if datetime.fromisoformat(r["fired_at"].replace("Z", "+00:00")) >= cutoff]
    return jsonify(_paginate(rows, page, page_size, "/alerts/"))


@app.route("/alerts/<alert_id>/")
def alerts_retrieve(alert_id):
    for a in data.load("alerts"):
        if a["alert_id"] == alert_id:
            return jsonify(a)
    return _not_found()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 7319))
    app.run(host="127.0.0.1", port=port, debug=False)
