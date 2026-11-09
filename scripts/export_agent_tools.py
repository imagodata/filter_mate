#!/usr/bin/env python3
"""Regenerate ``core/agent/tool_catalog.json`` from the declarations of the stdio MCP server.

Run it after changing a tool in ``filtermate_api/mcp/server.py``; ``pip install -r requirements-mcp.txt`` first.
References are inlined and schema titles dropped: fewer tokens, and no ``$ref`` for a local model to trip on.

    python scripts/export_agent_tools.py
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "core" / "agent" / "tool_catalog.json"


def clean_schema(schema: Any, definitions: Dict[str, Any]) -> Any:
    """``schema`` with its ``$ref`` replaced by what they point at and the ``title`` keywords removed."""
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        target = definitions[schema["$ref"].rsplit("/", 1)[-1]]
        merged = {**target, **{key: value for key, value in schema.items() if key != "$ref"}}
        return clean_schema(merged, definitions)
    cleaned: Dict[str, Any] = {}
    for key, value in schema.items():
        if key in ("title", "$defs"):
            continue
        if key == "properties":  # names of arguments here, not keywords
            cleaned[key] = {name: clean_schema(item, definitions) for name, item in value.items()}
        elif key in ("items", "additionalProperties") and isinstance(value, dict):
            cleaned[key] = clean_schema(value, definitions)
        elif key == "anyOf":
            cleaned[key] = [clean_schema(item, definitions) for item in value]
        else:
            cleaned[key] = value
    return cleaned


def catalog_entries():
    """The tools as the MCP server declares them, cleaned."""
    sys.path.insert(0, str(ROOT))
    from filtermate_api.mcp.server import build_server

    listed = asyncio.run(build_server(None).list_tools())  # the client is only used when a tool runs
    entries = []
    for tool in listed:
        schema = tool.input_schema if hasattr(tool, "input_schema") else tool.inputSchema
        annotations = tool.annotations
        read_only = annotations.read_only_hint if hasattr(annotations, "read_only_hint") else annotations.readOnlyHint
        destructive = (annotations.destructive_hint if hasattr(annotations, "destructive_hint")
                       else annotations.destructiveHint)
        idempotent = (annotations.idempotent_hint if hasattr(annotations, "idempotent_hint")
                      else annotations.idempotentHint)
        entries.append({
            "name": tool.name,
            "title": annotations.title or "",
            "description": " ".join(line.strip() for line in (tool.description or "").splitlines() if line.strip()),
            "read_only": bool(read_only),
            "destructive": bool(destructive),
            "idempotent": bool(idempotent),
            "input_schema": clean_schema(schema, schema.get("$defs", {})),
        })
    return entries


def main() -> int:
    payload = {"generated_by": "scripts/export_agent_tools.py", "tools": catalog_entries()}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUTPUT}: {len(payload['tools'])} tools")
    return 0


if __name__ == "__main__":
    sys.exit(main())
