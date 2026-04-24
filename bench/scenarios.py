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
    {
        "id": "team_cost_attribution",
        "prompt": (
            "For each team (the owner field on a model), compute the total GPU-hours and "
            "total cost_usd across all batch jobs run on models they own. Rank teams by "
            "total cost descending and call out the single highest-spending team."
        ),
    },
    {
        "id": "alert_fatigue_analysis",
        "prompt": (
            "Over the last 14 days, count how often each distinct alert message fires and "
            "which endpoint generates the most alerts. Identify the top 3 noisiest "
            "(message, endpoint_id) pairs by fire count."
        ),
    },
    {
        "id": "gpu_efficiency_per_model",
        "prompt": (
            "For each model, compute GPU-hours per successfully-completed shard: "
            "sum gpu_hours over SUCCEEDED jobs divided by sum of (shards_total - shards_failed). "
            "Rank models from most to least efficient and flag any whose value exceeds 0.5 "
            "GPU-hours per shard."
        ),
    },
    {
        "id": "shard_stability_audit",
        "prompt": (
            "For every model, compute the average shards_failed / shards_total ratio "
            "across its FAILED batch jobs. Flag any model whose average exceeds 20% and "
            "show the count of FAILED jobs contributing to that average."
        ),
    },
    {
        "id": "canary_traffic_split_audit",
        "prompt": (
            "List every endpoint currently serving traffic across more than one model "
            "version (traffic_split has more than one key). For each, show the split "
            "percentages and the p99 latency trend over the last 7 days. Flag any "
            "endpoint whose p99 trended upward day-over-day."
        ),
    },
    {
        "id": "llm_token_economics",
        "prompt": (
            "For each endpoint, compute total tokens_out over the last 7 days and the "
            "average daily growth rate. Rank endpoints by total output tokens and flag "
            "any whose daily tokens_out grew by more than 20% over the window."
        ),
    },
    {
        "id": "post_deploy_alert_correlation",
        "prompt": (
            "For every HIGH-severity alert fired in the last 14 days, check whether a "
            "deploy to that same endpoint occurred within the 2 hours immediately before "
            "the alert. List each alert with its suspected triggering deploy (if any) and "
            "summarise what fraction of HIGH alerts appear deploy-related."
        ),
    },
]
