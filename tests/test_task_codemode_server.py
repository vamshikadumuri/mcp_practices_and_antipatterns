import json
import pytest
from fastmcp import Client
from servers.task_codemode_server import mcp


@pytest.mark.asyncio
async def test_exposes_eight_tools():
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
        assert len(names) == 8
        assert "list_api" in names
        assert "execute_python" in names
        assert "triage_failed_batch_jobs" in names


@pytest.mark.asyncio
async def test_task_tools_present():
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
        expected = {
            "triage_failed_batch_jobs", "endpoint_latency_trends", "model_cost_report",
            "correlate_alerts_with_metrics", "compare_recent_failed_jobs", "apply_traffic_split",
        }
        assert expected.issubset(names)


@pytest.mark.asyncio
async def test_list_api_shows_mlops_functions():
    async with Client(mcp) as client:
        res = await client.call_tool("list_api", {})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "list_batch_jobs(" in text
        assert "triage_failed_batch_jobs(" in text
        assert "compare_runs(" in text


@pytest.mark.asyncio
async def test_list_api_filter():
    async with Client(mcp) as client:
        res = await client.call_tool("list_api", {"filter": "endpoint"})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "list_endpoints" in text
        assert "list_batch_jobs" not in text


@pytest.mark.asyncio
async def test_list_api_no_rest_names():
    async with Client(mcp) as client:
        res = await client.call_tool("list_api", {})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "mlops_batch_jobs_list" not in text
        assert "rest_api" not in text


@pytest.mark.asyncio
async def test_execute_python_uses_sandbox():
    async with Client(mcp) as client:
        code = "failed = mlops.list_batch_jobs(status='FAILED')\nprint(f'{len(failed)} failed jobs')\n"
        res = await client.call_tool("execute_python", {"code": code})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "failed jobs" in text


@pytest.mark.asyncio
async def test_execute_python_blocks_import():
    async with Client(mcp) as client:
        res = await client.call_tool("execute_python", {"code": "import os"})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert text.startswith("ERROR:")


@pytest.mark.asyncio
async def test_triage_tool_returns_complete_answer():
    async with Client(mcp) as client:
        result = await client.call_tool("triage_failed_batch_jobs", {"since_hours": 9999})
        data = json.loads(result.content[0].text)
        assert "total_failed" in data
        assert "most_common_reason" in data
