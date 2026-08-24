"""Discover remote MCP v2 tools and adapt them to LangChain."""
import asyncio
import json
import time
from typing import Any
from langchain_core.tools import StructuredTool
from pydantic import create_model

_DISCOVERY_CACHE: dict[str, tuple[float, list]] = {}
DISCOVERY_TTL_SECONDS = 300  # 5 minutes
from mcp import Client


def _field_type(schema: dict[str, Any]):
    kind = (schema or {}).get("type")
    return {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}.get(kind, Any)


def _args_model(tool_name: str, schema: dict[str, Any]):
    properties = (schema or {}).get("properties", {})
    required = set((schema or {}).get("required", []))
    fields = {}
    for name, prop in properties.items():
        annotation = _field_type(prop)
        fields[name] = (annotation, ... if name in required else None)
    safe_name = "MCPArgs_" + re_safe(tool_name)
    return create_model(safe_name, **fields)


def re_safe(value: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in value)


async def _discover(url: str):
    async with Client(url) as client:
        listed = await client.list_tools()
        return list(listed.tools)


async def _call(url: str, name: str, arguments: dict[str, Any]):
    async with Client(url) as client:
        return await client.call_tool(name, arguments)


def _sync_call(url: str, name: str, arguments: dict[str, Any]) -> str:
    result = asyncio.run(_call(url, name, arguments))
    if getattr(result, "is_error", False):
        return json.dumps({"error": True, "content": [str(x) for x in getattr(result, "content", [])]})
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, default=str)
    return json.dumps({"content": [str(x) for x in getattr(result, "content", [])]}, ensure_ascii=False)


def load_remote_mcp_tools(url: str) -> list[StructuredTool]:
    if not url:
        return []
    now = time.time()
    cached = _DISCOVERY_CACHE.get(url)
    if cached and now - cached[0] < DISCOVERY_TTL_SECONDS:
        remote_tools = cached[1]
    else:
        remote_tools = asyncio.run(_discover(url))
        _DISCOVERY_CACHE[url] = (now, remote_tools)
    tools = []
    for remote in remote_tools:
        args_schema = _args_model(remote.name, getattr(remote, "inputSchema", {}) or {})
        def make_fn(name):
            def invoke(**kwargs):
                return _sync_call(url, name, kwargs)
            invoke.__name__ = f"mcp_{re_safe(name)}"
            return invoke
        fn = make_fn(remote.name)
        tools.append(
            StructuredTool.from_function(
                func=fn,
                name=f"mcp_{re_safe(remote.name)}",
                description=(getattr(remote, "description", None) or f"MCP tool: {remote.name}") + " Use this MCP capability when it directly matches the user's request.",
                args_schema=args_schema,
            )
        )
    return tools
