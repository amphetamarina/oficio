from __future__ import annotations


def agent_response_block(response: str) -> list[str]:
    lines = ["  Agent response:"]
    lines.extend(f"  {line}" if line else "  " for line in response.strip().splitlines())
    return lines
