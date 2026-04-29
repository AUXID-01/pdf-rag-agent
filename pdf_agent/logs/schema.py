"""
schema.py
Responsibility: Shared dataclass definitions used across all modules.
All inter-module data must use these types — no raw dicts passed between layers.
Inputs: N/A (definitions only)
Outputs: N/A (definitions only)
Dependencies: None
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ParsedPage:
    page_number: int
    text: str
    blocks: List[dict] = field(default_factory=list)
    section_title: Optional[str] = None

@dataclass
class ParsedDocument:
    source_path: str
    filename: str
    total_pages: int
    pages: List[ParsedPage]

@dataclass
class Chunk:
    chunk_id: str
    page_start: int
    page_end: int
    section_title: str
    source_doc: str
    text: str
    char_count: int = 0

@dataclass
class LogEvent:
    level: str
    event_type: str
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "event_type": self.event_type,
            **self.payload
        }

@dataclass
class RetrievalHit:
    chunk_id: str
    score: float
    text: str
    page: int
    section: str

@dataclass
class AnswerObject:
    answer_text: str
    citations: List[RetrievalHit] = field(default_factory=list)
    turn_id: Optional[str] = None

@dataclass
class RefusalObject:
    reason: str
    query: str
    nearest_topic: Optional[str] = None
    nearest_page: Optional[int] = None

@dataclass
class ParsedResponse:
    status: str
    answer: str
    has_citations: bool = False
    citations: List[dict] = field(default_factory=list)
