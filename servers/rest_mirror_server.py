"""
REST-mirror MCP server — one tool per REST primitive.

Tool names use OpenAPI operationId conventions (DRF-spectacular style).
Docstrings are deliberately verbose to simulate what an auto-generated
OpenAPI→MCP gateway (e.g. IBM mcp-context-forge) produces from a
Django + DRF-spectacular Swagger JSON. Every tool schema is large, every
list response is a pagination envelope, and stub write tools exist purely
because the OpenAPI spec defines them — even though no agentic scenario
calls them. That full schema ships as part of the tools context on every
API turn, regardless of which tools the agent actually uses.
"""
from fastmcp import FastMCP
from mlops_backend import api

mcp = FastMCP("mlops-rest-mirror")


# ---------------------------------------------------------------------------
# Batch jobs
# ---------------------------------------------------------------------------

@mcp.tool
def mlops_batch_jobs_list(
    status: str | None = None,
    model_id: str | None = None,
    submitted_after: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    mlops_batch_jobs_list — List batch inference jobs.

    Returns a paginated list of BatchJob objects, optionally filtered.

    Parameters:
        status (string, optional): Filter by job status.
            Enum: PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED.
        model_id (string, optional): Filter by model identifier.
            Example: "m-llama3-8b-ft"
        submitted_after (string[$date-time], optional): Return only jobs
            submitted after this ISO 8601 datetime.
            Example: "2026-04-20T00:00:00Z"
        page (integer, optional): Page number within the paginated result set.
            Default: 1.
        page_size (integer, optional): Number of results per page.
            Default: 20. Maximum: 100.

    Response (200 OK):
        {
          "count": <integer> — total number of matching items,
          "next": <string|null> — URL of next page, or null,
          "previous": <string|null> — URL of previous page, or null,
          "results": [<BatchJob>, ...]
        }

    BatchJob schema:
        job_id (string), model_id (string), dataset_id (string),
        status (string), submitted_at (string[$date-time]),
        finished_at (string[$date-time]|null), shards_total (integer),
        shards_failed (integer), gpu_hours (number|null),
        cost_usd (number|null), failure_reason (string|null)

    Example response:
        {"count": 42, "next": "http://api.local/batch_jobs/?page=2", "previous": null,
         "results": [{"job_id": "bj-0001", "status": "FAILED", ...}]}
    """
    return api.list_batch_jobs(status, model_id, submitted_after, page, page_size)


@mcp.tool
def mlops_batch_jobs_retrieve(job_id: str) -> dict:
    """
    mlops_batch_jobs_retrieve — Retrieve a single batch inference job.

    Parameters:
        job_id (string, required): Unique identifier for the BatchJob.
            Example: "bj-0001"

    Response (200 OK): BatchJob object.
        job_id (string), model_id (string), dataset_id (string),
        status (string), submitted_at (string[$date-time]),
        finished_at (string[$date-time]|null), shards_total (integer),
        shards_failed (integer), gpu_hours (number|null),
        cost_usd (number|null), failure_reason (string|null)

    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retrieve_batch_job(job_id)


@mcp.tool
def mlops_batch_jobs_create(model_id: str, dataset_id: str, shards_total: int = 16) -> dict:
    """
    mlops_batch_jobs_create — Submit a new batch inference job.

    Parameters:
        model_id (string, required): Model to run inference with.
        dataset_id (string, required): Dataset to run inference over.
        shards_total (integer, optional): Number of shards to split the job into.
            Default: 16.

    Response (201 Created): BatchJob object with status PENDING.

    Response (400 Bad Request): {"model_id": ["This field is required."]}
    """
    return api.create_batch_job(model_id, dataset_id, shards_total)


@mcp.tool
def mlops_batch_jobs_destroy(job_id: str) -> dict:
    """
    mlops_batch_jobs_destroy — Cancel and delete a batch job.

    Parameters:
        job_id (string, required): Unique identifier for the BatchJob.

    Response (200 OK): {"job_id": "...", "status": "CANCELLED"}
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.destroy_batch_job(job_id)


@mcp.tool
def mlops_batch_jobs_logs_retrieve(job_id: str, lines: int = 50) -> dict:
    """
    mlops_batch_jobs_logs_retrieve — Retrieve recent log lines for a batch job.

    Parameters:
        job_id (string, required): Unique identifier for the BatchJob.
        lines (integer, optional): Number of log tail lines to return.
            Default: 50. Maximum: 500.

    Response (200 OK):
        {
          "job_id": <string>,
          "lines": <integer>,
          "content": <string> — newline-separated log text
        }

    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retrieve_batch_job_logs(job_id, lines)


@mcp.tool
def mlops_batch_jobs_retry_shards_create(job_id: str) -> dict:
    """
    mlops_batch_jobs_retry_shards_create — Retry only the failed shards of a batch job.

    This is a custom @action endpoint. A new child job is created containing
    only the shards that failed in the original job.

    Parameters:
        job_id (string, required): Unique identifier of the parent BatchJob.

    Response (201 Created):
        {
          "job_id": <string> — original job id,
          "retried_shards": <integer> — number of shards retried,
          "new_job_id": <string> — id of the newly created retry job
        }

    Response (400 Bad Request): {"detail": "Job has no failed shards."}
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retry_batch_job_shards(job_id)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@mcp.tool
def mlops_models_list(page: int = 1, page_size: int = 20) -> dict:
    """
    mlops_models_list — List all registered ML models.

    Parameters:
        page (integer, optional): Page number. Default: 1.
        page_size (integer, optional): Results per page. Default: 20.

    Response (200 OK): Paginated list of Model objects.
        {count, next, previous, results: [Model, ...]}

    Model schema:
        model_id (string), name (string), version (string),
        framework (string|null), status (string), created_at (string[$date-time])
    """
    return api.list_models(page, page_size)


@mcp.tool
def mlops_models_retrieve(model_id: str) -> dict:
    """
    mlops_models_retrieve — Retrieve a single ML model by id.

    Parameters:
        model_id (string, required): Unique model identifier.
            Example: "m-llama3-8b-ft"

    Response (200 OK): Model object.
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retrieve_model(model_id)


@mcp.tool
def mlops_models_create(name: str, version: str) -> dict:
    """
    mlops_models_create — Register a new ML model.

    Parameters:
        name (string, required): Human-readable model name.
        version (string, required): Semantic version string. Example: "1.0.0"

    Response (201 Created): Model object with status "registered".
    Response (400 Bad Request): Validation errors.
    """
    return api.create_model(name, version)


@mcp.tool
def mlops_models_partial_update(model_id: str, status: str | None = None, name: str | None = None) -> dict:
    """
    mlops_models_partial_update — Partially update a model record (PATCH).

    Parameters:
        model_id (string, required): Unique model identifier.
        status (string, optional): New model status. Enum: active, deprecated, archived.
        name (string, optional): New human-readable name.

    Response (200 OK): {"model_id": "...", "updated_fields": [...], "status": "ok"}
    Response (404 Not Found): {"detail": "Not found."}
    """
    fields = {k: v for k, v in {"status": status, "name": name}.items() if v is not None}
    return api.partial_update_model(model_id, **fields)


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

@mcp.tool
def mlops_datasets_list(page: int = 1, page_size: int = 20) -> dict:
    """
    mlops_datasets_list — List all registered datasets.

    Parameters:
        page (integer, optional): Page number. Default: 1.
        page_size (integer, optional): Results per page. Default: 20.

    Response (200 OK): Paginated list of Dataset objects.
        {count, next, previous, results: [Dataset, ...]}

    Dataset schema:
        dataset_id (string), name (string), row_count (integer|null),
        format (string|null), created_at (string[$date-time])
    """
    return api.list_datasets(page, page_size)


@mcp.tool
def mlops_datasets_retrieve(dataset_id: str) -> dict:
    """
    mlops_datasets_retrieve — Retrieve a single dataset by id.

    Parameters:
        dataset_id (string, required): Unique dataset identifier.
            Example: "ds-support-tickets"

    Response (200 OK): Dataset object.
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retrieve_dataset(dataset_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@mcp.tool
def mlops_endpoints_list(status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    """
    mlops_endpoints_list — List online serving endpoints.

    Parameters:
        status (string, optional): Filter by endpoint status.
            Enum: ACTIVE, DEGRADED, INACTIVE, PENDING.
        page (integer, optional): Page number. Default: 1.
        page_size (integer, optional): Results per page. Default: 20.

    Response (200 OK): Paginated list of Endpoint objects.
        {count, next, previous, results: [Endpoint, ...]}

    Endpoint schema:
        endpoint_id (string), name (string), model_id (string),
        status (string), environment (string), traffic_splits (object|null),
        created_at (string[$date-time])
    """
    return api.list_endpoints(status, page, page_size)


@mcp.tool
def mlops_endpoints_retrieve(endpoint_id: str) -> dict:
    """
    mlops_endpoints_retrieve — Retrieve a single endpoint by id.

    Parameters:
        endpoint_id (string, required): Unique endpoint identifier.
            Example: "ep-prod-chat"

    Response (200 OK): Endpoint object.
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retrieve_endpoint(endpoint_id)


@mcp.tool
def mlops_endpoints_create(name: str, model_id: str) -> dict:
    """
    mlops_endpoints_create — Deploy a new serving endpoint.

    Parameters:
        name (string, required): Human-readable endpoint name.
        model_id (string, required): Model to serve at this endpoint.

    Response (201 Created): Endpoint object with status PENDING.
    Response (400 Bad Request): Validation errors.
    """
    return api.create_endpoint(name, model_id)


@mcp.tool
def mlops_endpoints_destroy(endpoint_id: str) -> dict:
    """
    mlops_endpoints_destroy — Decommission a serving endpoint.

    Parameters:
        endpoint_id (string, required): Unique endpoint identifier.

    Response (200 OK): {"endpoint_id": "...", "status": "DECOMMISSIONED"}
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.destroy_endpoint(endpoint_id)


@mcp.tool
def mlops_endpoints_partial_update(
    endpoint_id: str,
    name: str | None = None,
    model_id: str | None = None,
) -> dict:
    """
    mlops_endpoints_partial_update — Partially update an endpoint record (PATCH).

    Parameters:
        endpoint_id (string, required): Unique endpoint identifier.
        name (string, optional): New human-readable name.
        model_id (string, optional): Swap the model served at this endpoint.

    Response (200 OK): {"endpoint_id": "...", "updated_fields": [...], "status": "ok"}
    Response (404 Not Found): {"detail": "Not found."}
    """
    fields = {k: v for k, v in {"name": name, "model_id": model_id}.items() if v is not None}
    return api.partial_update_endpoint(endpoint_id, **fields)


@mcp.tool
def mlops_endpoints_metrics_list(
    endpoint_id: str, days: int = 7, page: int = 1, page_size: int = 20
) -> dict:
    """
    mlops_endpoints_metrics_list — List daily metric rollups for an endpoint.

    Parameters:
        endpoint_id (string, required): Unique endpoint identifier.
        days (integer, optional): Number of most-recent days to include.
            Default: 7.
        page (integer, optional): Page number. Default: 1.
        page_size (integer, optional): Results per page. Default: 20.

    Response (200 OK): Paginated list of EndpointMetric objects.
        {count, next, previous, results: [EndpointMetric, ...]}

    EndpointMetric schema:
        endpoint_id (string), date (string[$date]), qps (number),
        p50_ms (integer), p99_ms (integer), error_rate (number),
        tokens_out (integer)

    Example response:
        {"count": 7, "next": null, "previous": null,
         "results": [{"endpoint_id": "ep-prod-chat", "date": "2026-04-22",
                      "qps": 188.7, "p50_ms": 388, "p99_ms": 2100, ...}]}
    """
    return api.list_endpoint_metrics(endpoint_id, days, page, page_size)


@mcp.tool
def mlops_endpoints_logs_retrieve(endpoint_id: str, lines: int = 50) -> dict:
    """
    mlops_endpoints_logs_retrieve — Tail recent request logs for an endpoint.

    Parameters:
        endpoint_id (string, required): Unique endpoint identifier.
        lines (integer, optional): Number of log tail lines. Default: 50.

    Response (200 OK):
        {
          "endpoint_id": <string>,
          "lines": <integer>,
          "content": <string>
        }

    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retrieve_endpoint_logs(endpoint_id, lines)


@mcp.tool
def mlops_endpoints_traffic_partial_update(endpoint_id: str, splits: dict) -> dict:
    """
    mlops_endpoints_traffic_partial_update — Apply a traffic split across model versions.

    This is a custom @action endpoint (PATCH /endpoints/{id}/traffic/).
    The splits dict maps model version identifiers to traffic percentages.
    Percentages must sum to 100.

    Parameters:
        endpoint_id (string, required): Unique endpoint identifier.
        splits (object, required): Map of model_version_id → traffic_percentage.
            Example: {"v1": 80, "v2": 20}

    Response (200 OK): {"endpoint_id": "...", "applied": {...}, "status": "OK"}
    Response (400 Bad Request): {"detail": "Percentages must sum to 100."}
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.update_endpoint_traffic(endpoint_id, splits)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@mcp.tool
def mlops_alerts_list(
    severity: str | None = None,
    fired_after: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    mlops_alerts_list — List firing alerts.

    Parameters:
        severity (string, optional): Filter by severity level.
            Enum: LOW, MEDIUM, HIGH, CRITICAL.
        fired_after (string[$date-time], optional): Return only alerts fired
            after this ISO 8601 datetime.
            Example: "2026-04-09T00:00:00Z"
        page (integer, optional): Page number. Default: 1.
        page_size (integer, optional): Results per page. Default: 20.

    Response (200 OK): Paginated list of Alert objects.
        {count, next, previous, results: [Alert, ...]}

    Alert schema:
        alert_id (string), endpoint_id (string), severity (string),
        fired_at (string[$date-time]), message (string)

    Example response:
        {"count": 5, "next": null, "previous": null,
         "results": [{"alert_id": "alert-001", "severity": "HIGH", ...}]}
    """
    return api.list_alerts(severity, fired_after, page, page_size)


@mcp.tool
def mlops_alerts_retrieve(alert_id: str) -> dict:
    """
    mlops_alerts_retrieve — Retrieve a single alert by id.

    Parameters:
        alert_id (string, required): Unique alert identifier.
            Example: "alert-001"

    Response (200 OK): Alert object.
    Response (404 Not Found): {"detail": "Not found."}
    """
    return api.retrieve_alert(alert_id)


if __name__ == "__main__":
    mcp.run()
