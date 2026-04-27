from __future__ import annotations


def agent_response_block(response: str) -> list[str]:
    fence = safe_fence(response)
    lines = ["  Agent response:", f"  {fence}markdown"]
    lines.extend(f"  {line}" if line else "  " for line in response.strip().splitlines())
    lines.append(f"  {fence}")
    return lines


def safe_fence(text: str) -> str:
    fence = "````"
    while fence in text:
        fence += "`"
    return fence
