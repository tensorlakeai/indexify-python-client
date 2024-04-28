from dataclasses import dataclass
from typing import List

from indexify.extraction_policy import ExtractionPolicyRequest


@dataclass
class ExtractionGraphRequest:
  name: str
  namespace: str
  policies: List[ExtractionPolicyRequest]