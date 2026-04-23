import asyncio, json, sys
import pytest
from mcp import ClientSession, StdioServerParameters, stdio_client


@pytest.fixture
def server_params():
    return StdioServerParameters(command=sys.executable, args=["-m", "servers.task_oriented_server"])


@pytest.mark.asyncio
async def test_lists_small_tool_count(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            # Task-oriented server should stay lean
            assert len(tools) <= 10, f"Expected <=10 tools, got {len(tools)}"


@pytest.mark.asyncio
async def test_tool_names_are_action_oriented(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert "triage_failed_batch_jobs" in names
            assert "endpoint_latency_trends" in names
            assert "model_cost_report" in names
            assert "correlate_alerts_with_metrics" in names
            assert "compare_recent_failed_jobs" in names


@pytest.mark.asyncio
async def test_triage_single_call_returns_complete_answer(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("triage_failed_batch_jobs", {"since_hours": 9999})
            data = json.loads(result.content[0].text)
            assert "total_failed" in data
            assert "most_common_reason" in data
            assert "most_affected_model_id" in data


@pytest.mark.asyncio
async def test_model_cost_report_single_call(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("model_cost_report", {})
            data = json.loads(result.content[0].text)
            assert "models" in data
            assert len(data["models"]) > 0
