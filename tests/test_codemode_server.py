import pytest
from fastmcp import Client
from servers.codemode_server import mcp

@pytest.mark.asyncio
async def test_codemode_exposes_two_tools():
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
        assert names == {"list_api", "execute_python"}

@pytest.mark.asyncio
async def test_list_api_returns_compact_signatures():
    async with Client(mcp) as client:
        res = await client.call_tool("list_api", {})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "list_batch_jobs(" in text and "compare_runs(" in text

@pytest.mark.asyncio
async def test_list_api_filter():
    async with Client(mcp) as client:
        res = await client.call_tool("list_api", {"filter": "endpoint"})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert "list_endpoints" in text and "list_batch_jobs" not in text

@pytest.mark.asyncio
async def test_execute_python_uses_sandbox():
    async with Client(mcp) as client:
        code = ("failed = mlops.list_batch_jobs(status='FAILED')\n"
                "print(f'{len(failed)} failed jobs')\n")
        res = await client.call_tool("execute_python", {"code": code})
        assert "failed jobs" in (res.data if isinstance(res.data, str) else str(res.data))

@pytest.mark.asyncio
async def test_execute_python_blocks_import():
    async with Client(mcp) as client:
        res = await client.call_tool("execute_python", {"code": "import os"})
        text = res.data if isinstance(res.data, str) else str(res.data)
        assert text.startswith("ERROR:")
