"""Tests for mlops_backend.api — the pure REST client (1:1 with Flask)."""
from mlops_backend import api


def test_list_batch_jobs_returns_pagination_envelope():
    result = api.list_batch_jobs()
    assert "count" in result
    assert "next" in result
    assert "previous" in result
    assert "results" in result
    assert isinstance(result["results"], list)


def test_list_batch_jobs_filter_by_status():
    result = api.list_batch_jobs(status="FAILED")
    assert all(j["status"] == "FAILED" for j in result["results"])
    assert len(result["results"]) > 0


def test_list_batch_jobs_filter_by_model():
    result = api.list_batch_jobs(model_id="m-llama3-8b-ft")
    assert all(j["model_id"] == "m-llama3-8b-ft" for j in result["results"])


def test_retrieve_batch_job_returns_raw_dict():
    j = api.retrieve_batch_job("bj-0001")
    assert j["job_id"] == "bj-0001"
    assert "count" not in j


def test_retrieve_batch_job_logs_returns_content_dict():
    result = api.retrieve_batch_job_logs("bj-0001")
    assert "content" in result
    assert "job_id" in result


def test_list_models_returns_pagination_envelope():
    result = api.list_models()
    assert "count" in result and "results" in result


def test_retrieve_model_returns_raw_dict():
    m = api.retrieve_model("m-llama3-8b-ft")
    assert m["model_id"] == "m-llama3-8b-ft"
    assert "count" not in m


def test_list_datasets_returns_pagination_envelope():
    result = api.list_datasets()
    assert "count" in result and "results" in result


def test_list_endpoints_returns_pagination_envelope():
    result = api.list_endpoints()
    assert "count" in result and "results" in result


def test_list_endpoint_metrics_returns_pagination_envelope():
    result = api.list_endpoint_metrics("ep-prod-chat", days=7)
    assert "count" in result and "results" in result
    assert len(result["results"]) > 0


def test_retrieve_endpoint_logs_returns_content_dict():
    result = api.retrieve_endpoint_logs("ep-prod-chat")
    assert "content" in result


def test_list_alerts_returns_pagination_envelope():
    result = api.list_alerts()
    assert "count" in result and "results" in result
