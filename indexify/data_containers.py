from enum import Enum
from typing import List
from dataclasses import dataclass, field

@dataclass
class Content:
    id: str
    parent_id: str
    labels: dict[str, any]
    extraction_graph_names: List[str]
    extraction_policy: str
    mime_type: str

    @classmethod
    def from_dict(cls, json: dict):
        return Content(
            id=json["id"],
            parent_id=json["parent_id"],
            labels=json["labels"],
            extraction_graph_names=json["extraction_graph_names"],
            extraction_policy=json["source"],
            mime_type=json["mime_type"],
        )

@dataclass
class TextChunk:
    text: str
    metadata: dict[str, any] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self):
        return {"text": self.text, "metadata": self.metadata}


@dataclass
class SearchResult:
    results: List[TextChunk]
