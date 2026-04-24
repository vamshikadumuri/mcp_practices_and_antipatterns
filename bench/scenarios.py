SCENARIOS = [
    {
        "id": "failed_jobs_triage",
        "prompt": (
            "Look at batch inference jobs from the last 48 hours. "
            "Group the FAILED ones by failure_reason, show counts, and "
            "tell me the single most common failure mode and which model_id is most affected."
        ),
    },
    {
        "id": "top_endpoints_latency",
        "prompt": (
            "For the 3 online endpoints with the highest average QPS over the past 7 days, "
            "report their p99 latency trend day-over-day and flag any whose p99 doubled."
        ),
    },
    {
        "id": "model_cost_audit",
        "prompt": (
            "For every model_id, compute total GPU-hours and total cost across all its batch jobs. "
            "Rank models by cost descending and note any model whose average cost-per-job exceeds $50."
        ),
    },
    {
        "id": "alert_correlation",
        "prompt": (
            "Cross-reference HIGH-severity alerts from the last 14 days with endpoint metrics: "
            "for each alerted endpoint, show the metric row from the day the alert fired."
        ),
    },
    {
        "id": "compare_reruns",
        "prompt": (
            "Find the two most recent FAILED batch jobs on model m-llama3-8b-ft, "
            "compare their GPU hours and cost, and recommend whether to retry failed shards "
            "or resubmit the full job."
        ),
    },
    {
        "id": "model_failure_by_dataset",
        "prompt": (
            "For each dataset, count how many batch jobs on that dataset failed in the "
            "last 7 days. Show datasets with at least one failure, sorted by failure count "
            "descending. For the dataset with the most failures, also show the breakdown "
            "by failure_reason."
        ),
    },
]
