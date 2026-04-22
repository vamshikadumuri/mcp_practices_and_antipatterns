from fastmcp import FastMCP
from mlops_backend import api

mcp = FastMCP("mlops-classic")

@mcp.tool
def list_batch_jobs(status: str | None = None, model_id: str | None = None,
                    since_hours: int | None = None) -> list[dict]:
    """List batch inference jobs, optionally filtered by status / model / recency."""
    return api.list_batch_jobs(status, model_id, since_hours)

@mcp.tool
def get_batch_job(job_id: str) -> dict:
    """Fetch a single batch job by id."""
    return api.get_batch_job(job_id)

@mcp.tool
def get_batch_job_logs(job_id: str, lines: int = 50) -> str:
    """Return the last N log lines for a batch job."""
    return api.get_batch_job_logs(job_id, lines)

@mcp.tool
def retry_failed_shards(job_id: str) -> dict:
    """Retry only the failed shards of a batch job."""
    return api.retry_failed_shards(job_id)

@mcp.tool
def list_models() -> list[dict]:
    """List all registered models."""
    return api.list_models()

@mcp.tool
def get_model(model_id: str) -> dict:
    """Fetch a model by id."""
    return api.get_model(model_id)

@mcp.tool
def list_datasets() -> list[dict]:
    """List all datasets."""
    return api.list_datasets()

@mcp.tool
def get_dataset(dataset_id: str) -> dict:
    """Fetch a dataset by id."""
    return api.get_dataset(dataset_id)

@mcp.tool
def list_endpoints(status: str | None = None) -> list[dict]:
    """List online serving endpoints."""
    return api.list_endpoints(status)

@mcp.tool
def get_endpoint(endpoint_id: str) -> dict:
    """Fetch a single endpoint."""
    return api.get_endpoint(endpoint_id)

@mcp.tool
def get_endpoint_metrics(endpoint_id: str, days: int = 7) -> list[dict]:
    """Daily QPS / p50 / p99 / error-rate rollups for an endpoint."""
    return api.get_endpoint_metrics(endpoint_id, days)

@mcp.tool
def update_traffic_split(endpoint_id: str, splits: dict) -> dict:
    """Apply a new traffic split across model versions for an endpoint."""
    return api.update_traffic_split(endpoint_id, splits)

@mcp.tool
def tail_endpoint_logs(endpoint_id: str, lines: int = 50) -> str:
    """Tail recent request logs for an endpoint."""
    return api.tail_endpoint_logs(endpoint_id, lines)

@mcp.tool
def list_alerts(severity: str | None = None) -> list[dict]:
    """List firing alerts, optionally filtered by severity."""
    return api.list_alerts(severity)

@mcp.tool
def compare_runs(job_ids: list[str]) -> dict:
    """Compare GPU hours, cost, and status across N batch jobs."""
    return api.compare_runs(job_ids)

if __name__ == "__main__":
    mcp.run()
