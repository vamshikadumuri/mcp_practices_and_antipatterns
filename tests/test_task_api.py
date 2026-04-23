from mlops_backend import task_api


def test_triage_failed_batch_jobs_structure():
    result = task_api.triage_failed_batch_jobs(since_hours=9999)
    assert "total_failed" in result
    assert "by_failure_reason" in result
    assert "most_common_reason" in result
    assert "most_affected_model_id" in result


def test_triage_failed_batch_jobs_groups_by_reason():
    result = task_api.triage_failed_batch_jobs(since_hours=9999)
    total = sum(item["count"] for item in result["by_failure_reason"])
    assert total == result["total_failed"]


def test_triage_failed_batch_jobs_most_common_is_ranked_first():
    result = task_api.triage_failed_batch_jobs(since_hours=9999)
    if result["by_failure_reason"]:
        top_reason = result["by_failure_reason"][0]["reason"]
        assert top_reason == result["most_common_reason"]


def test_triage_failed_batch_jobs_model_filter():
    result = task_api.triage_failed_batch_jobs(since_hours=9999, model_id="m-llama3-8b-ft")
    for item in result["by_failure_reason"]:
        for model in item["models_affected"]:
            assert model == "m-llama3-8b-ft"


def test_endpoint_latency_trends_structure():
    result = task_api.endpoint_latency_trends(top_n=3, days=7)
    assert "endpoints" in result
    assert len(result["endpoints"]) <= 3
    for ep in result["endpoints"]:
        assert "endpoint_id" in ep
        assert "avg_qps" in ep
        assert "p99_trend_ms" in ep
        assert "p99_doubled" in ep


def test_endpoint_latency_trends_top_n():
    result = task_api.endpoint_latency_trends(top_n=2, days=7)
    assert len(result["endpoints"]) <= 2


def test_model_cost_report_structure():
    result = task_api.model_cost_report()
    assert "models" in result
    for m in result["models"]:
        assert "model_id" in m
        assert "total_cost_usd" in m
        assert "avg_cost_per_job_usd" in m
        assert "exceeds_threshold" in m


def test_model_cost_report_ranked_descending():
    result = task_api.model_cost_report()
    costs = [m["total_cost_usd"] for m in result["models"]]
    assert costs == sorted(costs, reverse=True)


def test_model_cost_report_threshold_flag():
    result = task_api.model_cost_report(threshold_per_job_usd=0.0)
    for m in result["models"]:
        assert m["exceeds_threshold"] is True


def test_correlate_alerts_with_metrics_structure():
    result = task_api.correlate_alerts_with_metrics(severity="HIGH", since_days=9999)
    assert isinstance(result, list)
    for item in result:
        assert "alert" in item
        assert "endpoint_id" in item
        assert "metric_on_fired_date" in item


def test_correlate_alerts_with_metrics_severity_filter():
    result = task_api.correlate_alerts_with_metrics(severity="HIGH", since_days=9999)
    for item in result:
        assert item["alert"]["severity"] == "HIGH"


def test_compare_recent_failed_jobs_structure():
    result = task_api.compare_recent_failed_jobs("m-llama3-8b-ft", n=2)
    assert "model_id" in result
    assert "jobs" in result
    assert "recommendation" in result


def test_compare_recent_failed_jobs_recommendation_values():
    result = task_api.compare_recent_failed_jobs("m-llama3-8b-ft", n=2)
    assert result["recommendation"] in ("retry_shards", "resubmit_full_job", "insufficient_data")


def test_apply_traffic_split():
    result = task_api.apply_traffic_split("ep-prod-chat", {"v1": 70, "v2": 30})
    assert result["status"] == "OK"
    assert result["applied"] == {"v1": 70, "v2": 30}
