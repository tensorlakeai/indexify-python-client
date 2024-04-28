from dataclasses import dataclass, asdict, field
from typing import Optional, Dict


@dataclass
class ExtractionPolicyRequest:
    extractor: str
    name: str
    content_source: str
    input_params: Dict = field(default_factory=dict)
    labels_eq: Optional[str] = None

@dataclass
class ExtractionPolicy:
    extractor: str
    name: str
    content_source: str
    input_params: dict
    graph_name: str
    id: Optional[str] = None
    labels_eq: Optional[str] = None

    def __repr__(self) -> str:
        return f"ExtractionPolicy(name={self.name} extractor={self.extractor})"

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self) -> dict:
        filtered_dict = {k: v for k, v in asdict(self).items() if v is not None}
        return filtered_dict

    @classmethod
    def from_dict(cls, json: dict):
        if "filters_eq" in json:
            json["labels_eq"] = json.pop("filters_eq")
        return ExtractionPolicy(**json)
