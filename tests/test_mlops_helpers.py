"""Tests for servers.mlops — MCP-side pagination helpers and workflow aggregates."""
from servers import mlops


def test_list_batch_jobs_returns_flat_list():
    result = mlops.list_batch_jobs()
    assert isinstance(result, list)
    assert len(result) > 0
    assert "job_id" in result[0]


def test_list_batch_jobs_filter_by_status():
    failed = mlops.list_batch_jobs(status="FAILED")
    assert all(j["status"] == "FAILED" for j in failed)


def test_get_batch_job_returns_single_record():
    j = mlops.get_batch_job("bj-0001")
    assert j["job_id"] == "bj-0001"


def test_get_batch_job_logs_returns_string():
    logs = mlops.get_batch_job_logs("bj-0001")
    assert isinstance(logs, str)
    assert "bj-0001" in logs


def test_list_models_returns_flat_list():
    models = mlops.list_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "model_id" in models[0]


def test_list_datasets_returns_flat_list():
    datasets = mlops.list_datasets()
    assert isinstance(datasets, list)
    assert len(datasets) > 0


def test_list_endpoints_returns_flat_list():
    endpoints = mlops.list_endpoints()
    assert isinstance(endpoints, list)
    assert len(endpoints) > 0


def test_get_endpoint_metrics_returns_flat_list():
    metrics = mlops.get_endpoint_metrics("ep-prod-chat", days=7)
    assert isinstance(metrics, list)
    assert len(metrics) == 7
    assert "p99_ms" in metrics[0]


def test_list_alerts_returns_flat_list():
    alerts = mlops.list_alerts()
    assert isinstance(alerts, list)


def test_compare_runs_returns_expected_shape():
    diff = mlops.compare_runs(["bj-0001", "bj-0002"])
    assert "gpu_hours" in diff and "cost_usd" in diff and "status" in diff


def test_triage_failed_batch_jobs_shape():
    result = mlops.triage_failed_batch_jobs(since_hours=9999)
    assert "total_failed" in result
    assert "most_common_reason" in result
    assert "most_affected_model_id" in result
    assert "by_failure_reason" in result


def test_model_cost_report_shape():
    result = mlops.model_cost_report()
    assert "models" in result
    assert len(result["models"]) > 0
    assert "total_cost_usd" in result["models"][0]


def test_correlate_alerts_with_metrics_shape():
    result = mlops.correlate_alerts_with_metrics(severity="HIGH", since_days=9999)
    assert isinstance(result, list)
    if result:
        assert "alert" in result[0]
        assert "endpoint_id" in result[0]


def test_compare_recent_failed_jobs_shape():
    result = mlops.compare_recent_failed_jobs("m-llama3-8b-ft")
    assert "model_id" in result
    assert "recommendation" in result
