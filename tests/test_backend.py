from mlops_backend import api

def test_list_batch_jobs_filters_by_status():
    failed = api.list_batch_jobs(status="FAILED")
    assert all(j["status"] == "FAILED" for j in failed)
    assert len(failed) > 0

def test_list_batch_jobs_filters_by_model():
    jobs = api.list_batch_jobs(model_id="m-llama3-8b-ft")
    assert all(j["model_id"] == "m-llama3-8b-ft" for j in jobs)

def test_get_batch_job_returns_single_record():
    j = api.get_batch_job("bj-0001")
    assert j["job_id"] == "bj-0001"

def test_get_endpoint_metrics_window():
    rows = api.get_endpoint_metrics("ep-prod-chat", days=7)
    assert len(rows) == 7
    assert all("p99_ms" in r for r in rows)

def test_compare_runs_returns_diff():
    diff = api.compare_runs(["bj-0001", "bj-0002"])
    assert "gpu_hours" in diff and "cost_usd" in diff
