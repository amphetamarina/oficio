from __future__ import annotations

from typing import Any, Callable

JsonDict = dict[str, Any]


class ToolSpec:
    def __init__(self, name: str, schema: JsonDict, handler: Callable[..., str]) -> None:
        self.name = name
        self.schema = schema
        self.handler = handler


class ToolSchema:
    PATH = {
        "type": "string",
        "description": "Vault-relative source path. Defaults to today's daily note.",
    }
    LINE = {
        "type": "integer",
        "description": "Line number of the request from scan output. Required for auto-generated IDs.",
    }
    SESSION = {
        "type": "string",
        "description": "Current Hermes session ID from --pass-session-id.",
    }

    @classmethod
    def build(
        cls,
        name: str,
        description: str,
        properties: JsonDict,
        required: list[str] | None = None,
    ) -> JsonDict:
        parameters: JsonDict = {"type": "object", "properties": properties}
        if required:
            parameters["required"] = required
        return {"name": name, "description": description, "parameters": parameters}


CONFIG_SCHEMA = ToolSchema.build("oficio_config_show", "Show the active ofício configuration paths.", {})
SCAN_SCHEMA = ToolSchema.build(
    "oficio_scan",
    "Scan the daily note for pending '- [ ] @hermes ...' requests.",
    {"path": {"type": "string", "description": "Vault-relative daily note path. Defaults to today's daily note."}},
)
READ_SCHEMA = ToolSchema.build(
    "oficio_read",
    "Read a vault note through obsidian-cli, using a vault-relative path.",
    {"path": {"type": "string"}},
    ["path"],
)
START_SCHEMA = ToolSchema.build(
    "oficio_start",
    "Mark an ofício request as 'in progress' with inline Status in the daily note.",
    {"id": {"type": "string"}, "path": ToolSchema.PATH, "session_id": ToolSchema.SESSION, "line": ToolSchema.LINE},
    ["id"],
)
COMPLETE_SCHEMA = ToolSchema.build(
    "oficio_complete",
    "Mark an ofício request complete with inline Status in the daily note.",
    {
        "id": {"type": "string"},
        "path": ToolSchema.PATH,
        "note": {"type": "string"},
        "response": {
            "type": "string",
            "description": "Full response to write under the request as an Agent response block.",
        },
        "session_id": ToolSchema.SESSION,
        "line": ToolSchema.LINE,
    },
    ["id", "note"],
)
FAIL_SCHEMA = ToolSchema.build(
    "oficio_fail",
    "Mark an ofício request failed with inline Status in the daily note.",
    {
        "id": {"type": "string"},
        "path": ToolSchema.PATH,
        "error": {"type": "string"},
        "session_id": ToolSchema.SESSION,
        "line": ToolSchema.LINE,
    },
    ["id", "error"],
)
REPLACE_SCHEMA = ToolSchema.build(
    "oficio_replace",
    "Safely replace one exact string in a vault note.",
    {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
    ["path", "old", "new"],
)
TODAY_SCHEMA = ToolSchema.build("oficio_today", "Show today's resolved ofício daily note path.", {})
