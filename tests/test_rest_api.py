import pytest
from mlops_backend import rest_api


def test_list_batch_jobs_returns_envelope():
    result = rest_api.list_batch_jobs()
    assert "count" in result
    assert "next" in result
    assert "previous" in result
    assert "results" in result
    assert isinstance(result["results"], list)


def test_list_batch_jobs_pagination():
    result = rest_api.list_batch_jobs(page=1, page_size=2)
    assert len(result["results"]) <= 2
    if result["count"] > 2:
        assert result["next"] is not None


def test_list_batch_jobs_filter_status():
    result = rest_api.list_batch_jobs(status="FAILED")
    for r in result["results"]:
        assert r["status"] == "FAILED"


def test_list_batch_jobs_filter_model_id():
    result = rest_api.list_batch_jobs(model_id="m-llama3-8b-ft")
    for r in result["results"]:
        assert r["model_id"] == "m-llama3-8b-ft"


def test_retrieve_batch_job():
    jobs = rest_api.list_batch_jobs()["results"]
    assert jobs, "Need at least one job in test data"
    job_id = jobs[0]["job_id"]
    result = rest_api.retrieve_batch_job(job_id)
    assert result["job_id"] == job_id


def test_retrieve_batch_job_not_found():
    with pytest.raises(KeyError):
        rest_api.retrieve_batch_job("bj-nonexistent")


def test_create_batch_job_stub():
    result = rest_api.create_batch_job("m-test", "ds-test", shards_total=8)
    assert result["model_id"] == "m-test"
    assert result["status"] == "PENDING"


def test_destroy_batch_job_stub():
    result = rest_api.destroy_batch_job("bj-0001")
    assert result["status"] == "CANCELLED"


def test_retrieve_batch_job_logs():
    result = rest_api.retrieve_batch_job_logs("bj-0001", lines=10)
    assert "content" in result
    assert result["lines"] == 10


def test_retry_batch_job_shards():
    failed_jobs = rest_api.list_batch_jobs(status="FAILED")["results"]
    assert failed_jobs
    result = rest_api.retry_batch_job_shards(failed_jobs[0]["job_id"])
    assert "new_job_id" in result


def test_list_models_envelope():
    result = rest_api.list_models()
    assert "count" in result and "results" in result


def test_retrieve_model():
    models = rest_api.list_models()["results"]
    assert models
    mid = models[0]["model_id"]
    assert rest_api.retrieve_model(mid)["model_id"] == mid


def test_list_datasets_envelope():
    result = rest_api.list_datasets()
    assert "count" in result and "results" in result


def test_list_endpoints_envelope():
    result = rest_api.list_endpoints()
    assert "count" in result and "results" in result


def test_list_endpoints_filter_status():
    result = rest_api.list_endpoints(status="ACTIVE")
    for r in result["results"]:
        assert r["status"] == "ACTIVE"


def test_list_endpoint_metrics_envelope():
    ep_id = rest_api.list_endpoints()["results"][0]["endpoint_id"]
    result = rest_api.list_endpoint_metrics(ep_id, days=7)
    assert "count" in result and "results" in result


def test_update_endpoint_traffic():
    result = rest_api.update_endpoint_traffic("ep-prod-chat", {"v1": 80, "v2": 20})
    assert result["status"] == "OK"


def test_list_alerts_envelope():
    result = rest_api.list_alerts()
    assert "count" in result and "results" in result


def test_list_alerts_filter_severity():
    result = rest_api.list_alerts(severity="HIGH")
    for r in result["results"]:
        assert r["severity"] == "HIGH"


def test_retrieve_alert():
    alerts = rest_api.list_alerts()["results"]
    assert alerts
    aid = alerts[0]["alert_id"]
    assert rest_api.retrieve_alert(aid)["alert_id"] == aid
