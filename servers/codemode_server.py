import inspect
from fastmcp import FastMCP
from mlops_backend import api as mlops
from servers.sandbox import run_sandboxed

mcp = FastMCP("mlops-codemode")

_EXPORTED = [
    "list_batch_jobs", "get_batch_job", "get_batch_job_logs", "retry_failed_shards",
    "list_models", "get_model", "list_datasets", "get_dataset",
    "list_endpoints", "get_endpoint", "get_endpoint_metrics",
    "update_traffic_split", "tail_endpoint_logs", "list_alerts", "compare_runs",
]

def _signatures(filter: str | None = None) -> str:
    lines = []
    for name in _EXPORTED:
        if filter and filter not in name:
            continue
        fn = getattr(mlops, name)
        sig = inspect.signature(fn)
        lines_doc = (inspect.getdoc(fn) or "").splitlines()
        doc = lines_doc[0] if lines_doc else ""
        lines.append(f"mlops.{name}{sig}  # {doc}".rstrip())
    return "\n".join(lines)

@mcp.tool
def list_api(filter: str | None = None) -> str:
    """Return one-line signatures for every callable in the `mlops` module.

    Call this first to discover the API, then call `execute_python` with code
    that uses the signatures. Optionally filter by substring on the name.
    """
    return _signatures(filter)

@mcp.tool
def execute_python(code: str) -> str:
    """Run Python in a sandboxed subprocess. `mlops` is pre-imported; no other
    imports are available. Returns captured stdout, else repr(`result`).
    Intermediate variables stay inside the sandbox and are discarded after
    each call — there is no cross-call state."""
    return run_sandboxed(code)

if __name__ == "__main__":
    mcp.run()
