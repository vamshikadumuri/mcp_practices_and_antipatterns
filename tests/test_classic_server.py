import pytest
from fastmcp import Client
from servers.classic_server import mcp

@pytest.mark.asyncio
async def test_classic_exposes_expected_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert {"list_batch_jobs", "get_batch_job", "list_endpoints",
                "get_endpoint_metrics", "compare_runs"} <= names

@pytest.mark.asyncio
async def test_classic_list_batch_jobs_failed():
    async with Client(mcp) as client:
        res = await client.call_tool("list_batch_jobs", {"status": "FAILED"})
        # FastMCP 3.x returns a list of content items; extract the data
        data = res.data if hasattr(res, "data") else res
        assert data  # non-empty
        assert all(j["status"] == "FAILED" for j in data)
