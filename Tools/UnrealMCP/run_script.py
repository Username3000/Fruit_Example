"""Run a local UTF-8 Python script inside Unreal Editor via MCP."""

import asyncio
from pathlib import Path
import sys

from client import call

if __name__ == "__main__":
    script = Path(sys.argv[1]).resolve()
    asyncio.run(call("execute_python", {"code": script.read_text(encoding="utf-8-sig")}))
