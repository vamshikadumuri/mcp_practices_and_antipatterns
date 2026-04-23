"""
Task-oriented MCP server — one tool per ML-ops user workflow.

Each tool answers a complete scenario in a single call. Tools are named
after the action the user wants to take, not the resource being touched.
Docstrings are concise because each tool does one coherent thing.
"""
from fastmcp import FastMCP
from mlops_backend import task_api

mcp = FastMCP("mlops-task-oriented")


@mcp.tool
def triage_failed_batch_jobs(since_hours: int = 48, model_id: str | None = None) -> dict:
    """Group failed batch jobs by failure reason; return counts, most common failure, and most affected model."""
    return task_api.triage_failed_batch_jobs(since_hours, model_id)


@mcp.tool
def endpoint_latency_trends(top_n: int = 3, days: int = 7) -> dict:
    """Return the top-N endpoints by avg QPS with their daily p99 trend and a flag if p99 doubled."""
    return task_api.endpoint_latency_trends(top_n, days)


@mcp.tool
def model_cost_report(threshold_per_job_usd: float = 50.0) -> dict:
    """Rank all models by total GPU-hours and cost across batch jobs; flag models whose avg cost-per-job exceeds the threshold."""
    return task_api.model_cost_report(threshold_per_job_usd)


@mcp.tool
def correlate_alerts_with_metrics(severity: str = "HIGH", since_days: int = 14) -> list:
    """For each alert of the given severity in the last N days, return the endpoint metric row from the day it fired."""
    return task_api.correlate_alerts_with_metrics(severity, since_days)


@mcp.tool
def compare_recent_failed_jobs(model_id: str, n: int = 2) -> dict:
    """Compare the N most recent failed jobs for a model on GPU hours and cost; recommend retry-shards vs full resubmit."""
    return task_api.compare_recent_failed_jobs(model_id, n)


@mcp.tool
def apply_traffic_split(endpoint_id: str, splits: dict) -> dict:
    """Apply a traffic split across model versions for an endpoint."""
    return task_api.apply_traffic_split(endpoint_id, splits)


if __name__ == "__main__":
    mcp.run()
