"""Project-scoped MCP adapter for Epic's built-in Python remote execution."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import threading
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = Path(os.environ.get("UNREAL_ENGINE_ROOT", r"C:\Program Files\Epic Games\UE_5.8"))
REMOTE_MODULE = ENGINE_ROOT / "Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python/remote_execution.py"
spec = importlib.util.spec_from_file_location("unreal_remote_execution", REMOTE_MODULE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load Epic Python remote execution: {REMOTE_MODULE}")
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)


class CommandConnection(remote._RemoteExecutionCommandConnection):
    """Handle fragmented TCP responses, including replies above 8 KB."""

    def _receive_message(self, expected_type):
        self._command_channel_socket.settimeout(60)
        payload = bytearray()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            chunk = self._command_channel_socket.recv(65536)
            if not chunk:
                raise ConnectionError("Unreal Editor closed the command connection")
            payload.extend(chunk)
            if len(payload) > 16 * 1024 * 1024:
                raise RuntimeError("Unreal response exceeds 16 MB; paginate the query")
            try:
                json.loads(payload)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            message = remote._RemoteExecutionMessage(None, None)
            if (message.from_json_bytes(bytes(payload))
                    and message.passes_receive_filter(self._node_id)
                    and message.type_ == expected_type):
                return message
            raise RuntimeError("Unexpected Unreal remote execution response")
        raise TimeoutError("Unreal response timed out")


# Epic's client creates this connection class in open_command_connection().
remote._RemoteExecutionCommandConnection = CommandConnection
command_lock = threading.Lock()
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
mcp = FastMCP(
    "Unreal Fruit Example",
    instructions=(
        "Operate only on Fruit_Example through the open Unreal Editor. Start with "
        "editor_status. Use list_assets/list_level_actors for inspection and "
        "execute_python for Unreal Python operations. Use print() for results. "
        "Paginate large queries. Save intentional changes with save_all. "
        "Do not retry a timed-out mutation automatically: it may have executed."
    ),
)


def _run(code: str) -> dict[str, Any]:
    with command_lock:
        config = remote.RemoteExecutionConfig()
        # Each short-lived session needs a distinct loopback command port.
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            config.command_endpoint = probe.getsockname()
        session = remote.RemoteExecution(config)
        try:
            session.start()
            deadline = time.monotonic() + 8
            matches = []
            while time.monotonic() < deadline:
                matches = [
                    node for node in session.remote_nodes
                    if node.get("project_root")
                    and Path(node["project_root"]).resolve() == PROJECT_ROOT
                ]
                if matches:
                    break
                time.sleep(0.1)
            if not matches:
                raise RuntimeError(
                    f"Editor for {PROJECT_ROOT} is not available. Open "
                    "Fruit_Example.uproject in Unreal Editor and wait for startup. "
                    "PythonScriptPlugin and Python Remote Execution must be enabled."
                )
            if len(matches) != 1:
                raise RuntimeError("Multiple editors opened this project; keep one instance open")
            session.open_command_connection(matches[0]["node_id"])
            result = session.run_command(code, unattended=True, exec_mode=remote.MODE_EXEC_FILE)
            if not result.get("success"):
                raise RuntimeError(json.dumps(result, ensure_ascii=False))
            return result
        except (OSError, TimeoutError) as exc:
            raise RuntimeError(
                "Unreal connection failed. If a command was sent, it may have executed; "
                "inspect editor state before retrying a mutation. " + str(exc)
            ) from exc
        finally:
            session.stop()


def _query(body: str) -> dict[str, Any]:
    result = _run("import unreal, json\n" + body)
    for entry in reversed(result.get("output", [])):
        output = entry.get("output", "")
        if output.startswith("MCP_JSON:"):
            return json.loads(output[len("MCP_JSON:"):])
    raise RuntimeError("Unreal did not return structured query output")


@mcp.tool(annotations=READ_ONLY)
def editor_status() -> dict[str, Any]:
    """Verify the project connection and return engine, project and current level."""
    return _query(
        "world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()\n"
        "print('MCP_JSON:' + json.dumps({"
        "'connected': True, 'project_file': unreal.Paths.get_project_file_path(), "
        "'engine_version': unreal.SystemLibrary.get_engine_version(), "
        "'level': world.get_path_name() if world else None}))"
    )


@mcp.tool(annotations=READ_ONLY)
def list_assets(path: str = "/Game", offset: int = 0, limit: int = 100) -> dict[str, Any]:
    """List project assets recursively, with pagination. path must be /Game or below."""
    if path != "/Game" and not path.startswith("/Game/"):
        raise ValueError("Asset path must be /Game or a subfolder")
    if offset < 0 or not 1 <= limit <= 500:
        raise ValueError("offset must be >= 0; limit must be 1..500")
    return _query(
        f"assets = sorted(unreal.EditorAssetLibrary.list_assets({path!r}, recursive=True, include_folder=False))\n"
        f"print('MCP_JSON:' + json.dumps({{'total': len(assets), 'offset': {offset}, "
        f"'assets': assets[{offset}:{offset + limit}]}}))"
    )


@mcp.tool(annotations=READ_ONLY)
def list_level_actors(offset: int = 0, limit: int = 100) -> dict[str, Any]:
    """List actors in the current editor level, with labels, classes and locations."""
    if offset < 0 or not 1 <= limit <= 500:
        raise ValueError("offset must be >= 0; limit must be 1..500")
    return _query(
        "actors = sorted(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors(), key=lambda a: a.get_path_name())\n"
        "rows = []\n"
        f"for actor in actors[{offset}:{offset + limit}]:\n"
        "    location = actor.get_actor_location()\n"
        "    rows.append({'label': actor.get_actor_label(), 'path': actor.get_path_name(), "
        "'class': actor.get_class().get_path_name(), 'location': [location.x, location.y, location.z]})\n"
        f"print('MCP_JSON:' + json.dumps({{'total': len(actors), 'offset': {offset}, 'actors': rows}}))"
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def execute_python(code: str) -> dict[str, Any]:
    """Execute Python in this project's Unreal Editor. import unreal to access the API.

    Can inspect or modify assets, actors, materials and exposed Blueprint properties.
    Use print() for output. Changes are not automatically saved. Do not automatically
    retry failed/timed-out mutations, because part of the script may have run.
    """
    return _run(code)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
def save_all(save_maps: bool = True, save_content: bool = True) -> dict[str, Any]:
    """Save all dirty maps/content packages in this project after intentional edits."""
    return _query(
        f"saved = unreal.EditorLoadingAndSavingUtils.save_dirty_packages({save_maps!r}, {save_content!r})\n"
        "print('MCP_JSON:' + json.dumps({'saved': saved}))"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
