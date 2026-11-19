"""Call the project MCP server over stdio, including before Codex reloads its tools."""

import argparse
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call(tool: str, arguments: dict):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("server.py"))],
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=120)) as session:
            await session.initialize()
            if tool == "tools":
                result = await session.list_tools()
            else:
                result = await session.call_tool(tool, arguments)
            print(result.model_dump_json(indent=2))
            if getattr(result, "isError", False):
                raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", nargs="?", default="editor_status")
    parser.add_argument("--arguments-file", type=Path, help="UTF-8 JSON tool arguments")
    options = parser.parse_args()
    arguments = json.loads(options.arguments_file.read_text(encoding="utf-8-sig")) if options.arguments_file else {}
    asyncio.run(call(options.tool, arguments))
