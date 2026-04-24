"""REST client for the mlops_backend Flask app.

One function per endpoint. Return shapes match Flask's responses exactly:
pagination envelopes on list endpoints, raw dicts on retrieve/create/update/delete,
{"job_id", "lines", "content"} on log endpoints. Nothing is unwrapped, composed,
or aggregated here — that is MCP-server code's job.
"""
import os
import requests

_BASE = os.getenv("MLOPS_API_URL", "http://127.0.0.1:7319")
_TIMEOUT = 10.0


def _get(path, **params):
    params = {k: v for k, v in params.items() if v is not None}
    r = requests.get(f"{_BASE}{path}", params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()

def _post(path, json=None):
    r = requests.post(f"{_BASE}{path}", json=json, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()

def _patch(path, json=None):
    r = requests.patch(f"{_BASE}{path}", json=json, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()

def _delete(path):
    r = requests.delete(f"{_BASE}{path}", timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


# --- Batch jobs ------------------------------------------------------------

def list_batch_jobs(status=None, model_id=None, submitted_after=None, page=1, page_size=20):
    return _get("/batch_jobs/", status=status, model_id=model_id,
                submitted_after=submitted_after, page=page, page_size=page_size)

def retrieve_batch_job(job_id):
    return _get(f"/batch_jobs/{job_id}/")

def create_batch_job(model_id, dataset_id, shards_total=16):
    return _post("/batch_jobs/", {"model_id": model_id, "dataset_id": dataset_id,
                                   "shards_total": shards_total})

def destroy_batch_job(job_id):
    return _delete(f"/batch_jobs/{job_id}/")

def retrieve_batch_job_logs(job_id, lines=50):
    return _get(f"/batch_jobs/{job_id}/logs/", lines=lines)

def retry_batch_job_shards(job_id):
    return _post(f"/batch_jobs/{job_id}/retry_shards/")


# --- Models ----------------------------------------------------------------

def list_models(page=1, page_size=20):
    return _get("/models/", page=page, page_size=page_size)

def retrieve_model(model_id):
    return _get(f"/models/{model_id}/")

def create_model(name, version):
    return _post("/models/", {"name": name, "version": version})

def partial_update_model(model_id, **fields):
    return _patch(f"/models/{model_id}/", fields)


# --- Datasets --------------------------------------------------------------

def list_datasets(page=1, page_size=20):
    return _get("/datasets/", page=page, page_size=page_size)

def retrieve_dataset(dataset_id):
    return _get(f"/datasets/{dataset_id}/")


# --- Endpoints -------------------------------------------------------------

def list_endpoints(status=None, page=1, page_size=20):
    return _get("/endpoints/", status=status, page=page, page_size=page_size)

def retrieve_endpoint(endpoint_id):
    return _get(f"/endpoints/{endpoint_id}/")

def create_endpoint(name, model_id):
    return _post("/endpoints/", {"name": name, "model_id": model_id})

def destroy_endpoint(endpoint_id):
    return _delete(f"/endpoints/{endpoint_id}/")

def partial_update_endpoint(endpoint_id, **fields):
    return _patch(f"/endpoints/{endpoint_id}/", fields)

def list_endpoint_metrics(endpoint_id, days=7, page=1, page_size=20):
    return _get(f"/endpoints/{endpoint_id}/metrics/", days=days, page=page, page_size=page_size)

def retrieve_endpoint_logs(endpoint_id, lines=50):
    return _get(f"/endpoints/{endpoint_id}/logs/", lines=lines)

def update_endpoint_traffic(endpoint_id, splits):
    return _patch(f"/endpoints/{endpoint_id}/traffic/", {"splits": splits})


# --- Alerts ----------------------------------------------------------------

def list_alerts(severity=None, fired_after=None, page=1, page_size=20):
    return _get("/alerts/", severity=severity, fired_after=fired_after,
                page=page, page_size=page_size)

def retrieve_alert(alert_id):
    return _get(f"/alerts/{alert_id}/")
