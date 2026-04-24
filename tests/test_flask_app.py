import urllib.request
import json
import pytest


def _get(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def _post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()), r.status


def _get_404(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


@pytest.fixture
def base(flask_server):
    return flask_server.url


def test_health(base):
    data = _get(f"{base}/health")
    assert data["status"] == "ok"


def test_batch_jobs_list_pagination_envelope(base):
    data = _get(f"{base}/batch_jobs/")
    assert "count" in data
    assert "next" in data
    assert "previous" in data
    assert "results" in data
    assert isinstance(data["results"], list)


def test_batch_jobs_list_filter_by_status(base):
    data = _get(f"{base}/batch_jobs/?status=FAILED")
    assert all(r["status"] == "FAILED" for r in data["results"])


def test_batch_jobs_retrieve(base):
    data = _get(f"{base}/batch_jobs/bj-0001/")
    assert data["job_id"] == "bj-0001"


def test_batch_jobs_retrieve_404(base):
    assert _get_404(f"{base}/batch_jobs/no-such-job/") == 404


def test_batch_jobs_logs(base):
    data = _get(f"{base}/batch_jobs/bj-0001/logs/")
    assert "content" in data
    assert "job_id" in data


def test_models_list_pagination_envelope(base):
    data = _get(f"{base}/models/")
    assert "count" in data and "results" in data


def test_models_retrieve(base):
    data = _get(f"{base}/models/m-llama3-8b-ft/")
    assert data["model_id"] == "m-llama3-8b-ft"


def test_datasets_list(base):
    data = _get(f"{base}/datasets/")
    assert "count" in data and len(data["results"]) > 0


def test_endpoints_list_pagination_envelope(base):
    data = _get(f"{base}/endpoints/")
    assert "count" in data and "results" in data


def test_endpoints_metrics(base):
    data = _get(f"{base}/endpoints/ep-prod-chat/metrics/")
    assert "count" in data
    assert len(data["results"]) > 0
    assert "p99_ms" in data["results"][0]


def test_alerts_list_pagination_envelope(base):
    data = _get(f"{base}/alerts/")
    assert "count" in data and "results" in data


def test_alerts_filter_by_severity(base):
    data = _get(f"{base}/alerts/?severity=HIGH")
    assert all(r["severity"] == "HIGH" for r in data["results"])


def test_batch_jobs_create_stub(base):
    resp, status = _post(f"{base}/batch_jobs/", {"model_id": "m-test", "dataset_id": "ds-test"})
    assert status == 201
    assert resp["status"] == "PENDING"
