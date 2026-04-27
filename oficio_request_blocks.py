from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

STATUS_LINE_PATTERN = re.compile(r"^\s+Status:\s*")
AGENT_RESPONSE_PATTERN = re.compile(r"^\s*Agent response:\s*$")
CHECKBOX_PATTERN = re.compile(r"^\s*-\s*\[\s*[ x]\]")
OPEN_CHECKBOX_PATTERN = re.compile(r"^\s*-\s*\[\s*\]")


class PendingRequest(TypedDict, total=False):
    id: str
    path: str
    line: int
    lines: list[int]
    text: str
    has_explicit_id: bool


@dataclass(frozen=True, slots=True)
class RequestBlock:
    marker_index: int
    checkbox_index: int
    end_index: int
    marker_line: str
    has_explicit_id: bool

    @property
    def line_number(self) -> int:
        return self.marker_index + 1

    @property
    def checkbox_line_number(self) -> int:
        return self.checkbox_index + 1

    @property
    def is_split_line(self) -> bool:
        return self.marker_index != self.checkbox_index
