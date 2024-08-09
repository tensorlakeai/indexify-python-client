from indexify import Content, extractor
from indexify.extractor import Extractor

from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional


@extractor(description="id function")
def _id(content: Content) -> List[Content]:
    return [content]

class Graph:
    def __init__(self, name: str):
        # TODO check for cycles
        self.name = name

        self.nodes: Dict[str, Callable] = {}
        self.params: Dict[str, Any] = {}

        self.edges: Dict[str, List[(str, str)]] = defaultdict(list)

        self.results: Dict[str, Any] = defaultdict(list) # TODO should the Any be Content?

        self.nodes["start"] = _id
        self.nodes["end"] = _id

        self._topo_counter = defaultdict(int)

        self._start_node = None

    def node(self, extractor: Extractor, params: Any = None) -> None:
        name = extractor._extractor_name
        if name in self.nodes:
            raise Exception(f"Cannot insert node, node with name: `{name}` already exists")

        self.nodes[name] = extractor
        self.params[name] = params

        # assign each node a rank of 1 to init the graph
        self._topo_counter[name] = 1

    def edge(self, from_node: extractor, to_node: extractor, prefilter_predicates: Optional[str] = None) -> None:
        from_node_name = from_node._extractor_name
        to_node_name = to_node._extractor_name

        self.edges[from_node_name].append((to_node_name, prefilter_predicates))

        self._topo_counter[to_node_name] += 1

    def _assign_start_node(self):
        # this method should be called before a graph can be run
        nodes = sorted(self._topo_counter.items(), key=lambda x: x[1])
        self._start_node = nodes[0][0]