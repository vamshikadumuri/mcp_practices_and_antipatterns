import asyncio, sys
import pytest
from mcp import ClientSession, StdioServerParameters, stdio_client


@pytest.fixture
def server_params():
    return StdioServerParameters(command=sys.executable, args=["-m", "servers.rest_mirror_server"])


@pytest.mark.asyncio
async def test_lists_expected_tool_count(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            # Rest mirror should expose many more tools than task-oriented
            assert len(tools) >= 20, f"Expected >=20 tools, got {len(tools)}"


@pytest.mark.asyncio
async def test_tool_names_use_operationid_convention(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert "mlops_batch_jobs_list" in names
            assert "mlops_batch_jobs_retrieve" in names
            assert "mlops_alerts_list" in names
            assert "mlops_endpoints_metrics_list" in names


@pytest.mark.asyncio
async def test_list_returns_pagination_envelope(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("mlops_batch_jobs_list", {})
            import json
            data = json.loads(result.content[0].text)
            assert "count" in data
            assert "next" in data
            assert "previous" in data
            assert "results" in data


@pytest.mark.asyncio
async def test_stub_write_tools_exist(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            # Stub tools exist in the schema and inflate every tool list
            assert "mlops_batch_jobs_create" in names
            assert "mlops_batch_jobs_destroy" in names
            assert "mlops_endpoints_create" in names
            assert "mlops_models_create" in names
