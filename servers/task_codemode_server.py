"""
Task-oriented + Code Mode MCP server.

Six pre-designed task tools cover the common ML-ops scenarios. For anything
those tools don't cover, list_api + execute_python let the model write its
own Python against the mlops helper library.
"""
import inspect
from fastmcp import FastMCP
from servers import mlops
from servers.sandbox import run_sandboxed

mcp = FastMCP("mlops-task-codemode")


# ---------------------------------------------------------------------------
# Pre-designed task tools (same 6 as task_oriented_server)
# ---------------------------------------------------------------------------

@mcp.tool
def triage_failed_batch_jobs(since_hours: int = 48, model_id: str | None = None) -> dict:
    """Group failed batch jobs by failure reason; return counts, most common failure, and most affected model."""
    return mlops.triage_failed_batch_jobs(since_hours, model_id)


@mcp.tool
def endpoint_latency_trends(top_n: int = 3, days: int = 7) -> dict:
    """Return the top-N endpoints by avg QPS with their daily p99 trend and a flag if p99 doubled."""
    return mlops.endpoint_latency_trends(top_n, days)


@mcp.tool
def model_cost_report(threshold_per_job_usd: float = 50.0) -> dict:
    """Rank all models by total GPU-hours and cost across batch jobs; flag models whose avg cost-per-job exceeds the threshold."""
    return mlops.model_cost_report(threshold_per_job_usd)


@mcp.tool
def correlate_alerts_with_metrics(severity: str = "HIGH", since_days: int = 14) -> list:
    """For each alert of the given severity in the last N days, return the endpoint metric row from the day it fired."""
    return mlops.correlate_alerts_with_metrics(severity, since_days)


@mcp.tool
def compare_recent_failed_jobs(model_id: str, n: int = 2) -> dict:
    """Compare the N most recent failed jobs for a model on GPU hours and cost; recommend retry-shards vs full resubmit."""
    return mlops.compare_recent_failed_jobs(model_id, n)


@mcp.tool
def apply_traffic_split(endpoint_id: str, splits: dict) -> dict:
    """Apply a traffic split across model versions for an endpoint."""
    return mlops.apply_traffic_split(endpoint_id, splits)


# ---------------------------------------------------------------------------
# Code Mode escape hatch
# ---------------------------------------------------------------------------

_CODEMODE_API = [
    "list_batch_jobs", "get_batch_job", "get_batch_job_logs", "retry_failed_shards",
    "list_models", "get_model", "list_datasets", "get_dataset",
    "list_endpoints", "get_endpoint", "get_endpoint_metrics",
    "update_traffic_split", "tail_endpoint_logs", "list_alerts", "compare_runs",
    "triage_failed_batch_jobs", "endpoint_latency_trends", "model_cost_report",
    "correlate_alerts_with_metrics", "compare_recent_failed_jobs", "apply_traffic_split",
]


def _signatures(filter_substr=None):
    lines = []
    for name in _CODEMODE_API:
        if filter_substr and filter_substr not in name:
            continue
        fn = getattr(mlops, name)
        sig = inspect.signature(fn)
        first = (inspect.getdoc(fn) or "").splitlines()
        doc = first[0] if first else ""
        lines.append(f"mlops.{name}{sig}  # {doc}".rstrip())
    return "\n".join(lines)


@mcp.tool
def list_api(filter: str | None = None) -> str:
    """Python functions available inside execute_python. Use this ONLY when no
    pre-designed tool above (triage_failed_batch_jobs, endpoint_latency_trends,
    model_cost_report, correlate_alerts_with_metrics, compare_recent_failed_jobs,
    apply_traffic_split) answers the user's question."""
    return _signatures(filter)


@mcp.tool
def execute_python(code: str) -> str:
    """Run Python in a sandboxed subprocess. `mlops` is pre-imported with the
    functions listed by list_api. Returns stdout, else repr(result). Prefer
    a pre-designed task tool when one fits the user's intent."""
    return run_sandboxed(code)


if __name__ == "__main__":
    mcp.run()
