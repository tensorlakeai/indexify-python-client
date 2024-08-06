from indexify import Content, Feature, extractor
from indexify.extractor import Extractor

from collections import defaultdict
from typing import Any, Callable, Dict, List
from pydantic import BaseModel, Field

class ChunkOptions(BaseModel):
    chunk_size: int = 100

class ProfanityOptions(BaseModel):
    words: List[str] = Field(default_factory=lambda: [])


@extractor(description="Extracts text from PDFs")
def pdf_extraction(content: Content) -> List[Content]:
    return [Content.from_text("this is stupid"), Content.from_text("fuck why"), Content.from_text("this isn't stupid")]

@extractor(description="Profanity filter")
def filter_for_profanity(content: Content, params: ProfanityOptions) -> List[Content]:
    for profane_word in params['words']:
        if profane_word in content.data.decode('utf-8'):
            return []

    return [content]

@extractor(description="Object detector in the images")
def object_detector(content: Content) -> List[Content]:
    # TODO This should call a model or whatever
    return [Content.from_text("detected r12c201"), Content.from_text("detected r1c1")]

@extractor(description="Chunks text into paragraphs")
def text_chunks(content: Content, params: ChunkOptions) -> List[Content]:
    text = content.data.decode('utf-8')
    return [Content.from_text(i + "--" + j) for i, j in zip(text.split()[:-1], text.split()[1:])]

@extractor(description="Embeds text chunks")
def chunk_embeddings(content: Content) -> List[Feature]:
    return [content]

@extractor(description="id function")
def _id(content: Content) -> List[Content]:
    return [content]


class Graph:
    def __init__(self, name: str):
        # TODO name check, name collision on insert, cycles
        self.name = name

        self.nodes: Dict[str, Callable] = {}
        self.params: Dict[str, Any] = {}

        self.edges: Dict[str, List[(str, str)]] = defaultdict(list)

        self.results: Dict[str, Any] = defaultdict(list) # TODO should the Any be Content?

        self.nodes["start"] = _id
        self.nodes["end"] = _id

    def node(self, name: str, closure: Extractor, params: Any = None) -> None:
        self.nodes[name] = closure
        self.params[name] = params

    def edge(self, from_node: str, to_node: str, prefilter_predicates: str = "") -> None:
        self.edges[from_node].append((to_node, prefilter_predicates))


class LocalRunner:
    def __init__(self):
        self.results: Dict[str, Any] = defaultdict(list) # TODO should the Any be Content?

    def run(self, g, content: Content):
        return self._run(g, content=content, node_name="start")

    def _run(self, g, content: Content, node_name: str):
        extractor_construct: Callable = g.nodes[node_name]
        params = g.params.get(node_name, None)

        res = extractor_construct().extract(content=content, params=params)

        self.results[node_name].extend(res)

        for out_edge, pre_filter_predicate in g.edges[node_name]:
            # TODO there are no reductions yet, each recursion finishes it's path and returns
            for r in res:
                if self._prefilter_content(content=r, prefilter_predicate=pre_filter_predicate):
                    continue

                self._run(g, content=r, node_name=out_edge)

    def _prefilter_content(self, content: Content, prefilter_predicate: str) -> bool:
        # TODO impl
        return False

    def get_result(self, node_name: str) -> Content:
        return self.results[node_name]


if __name__ == "__main__":
    g = Graph("FilterGraph")

    a = g.node(name="pdf-extraction", closure=pdf_extraction)
    g.node(name="filter-for-profanity", closure=filter_for_profanity, params={"words": ["fuck"]})
    g.node(name="object-detector", closure=object_detector)
    g.node(name="text-chunker", closure=text_chunks, params={"chunk_size": 500})
    g.node(name="chunk-embedding", closure=chunk_embeddings)

    # add a pre-filter="tag1=10 and tag2=20"

    # change this to not need start or end
    g.edge("start", "pdf-extraction")

    g.edge("pdf-extraction", "filter-for-profanity")
    g.edge("pdf-extraction", "object-detector")

    g.edge("filter-for-profanity", "text-chunker")
    g.edge("object-detector", "text-chunker")

    g.edge("text-chunker", "chunk-embedding")

    g.edge("chunk-embedding", "end")

    # TODO will come back to this
    #content = Content.from_file("sample.pdf")
    local_runner = LocalRunner()
    local_runner.run(g, Content.from_text(""))

    print([i.data.decode('utf-8') for i in local_runner.get_result(node_name="end")])
