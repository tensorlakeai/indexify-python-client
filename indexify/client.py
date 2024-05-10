import yaml
import httpx
import uuid
import hashlib
import json
from collections import namedtuple
from .settings import DEFAULT_SERVICE_URL
from .extractor import Extractor
from .extraction_policy import ExtractionPolicy, ExtractionGraph
from .index import Index
from .utils import json_set_default
from .data_containers import TextChunk
from indexify.exceptions import ApiException
from dataclasses import dataclass

from typing import List, Optional, Union, Dict

Document = namedtuple("Document", ["text", "labels", "id"])

SQLQueryRow = namedtuple("SQLQueryRow", ["content_id", "data"])


@dataclass
class SqlQueryResult:
    result: List[Dict]


class IndexifyClient:
    """
    IndexifyClient is the main entry point for the SDK.
    For the full list of client features, see the
    [httpx Client documentation](https://www.python-httpx.org/api/#client).

    :param service_url: The URL of the Indexify service to connect to.
    :param args: Arguments to pass to the httpx.Client constructor
    :param kwargs: Keyword arguments to pass to the httpx.Client constructor

    Example usage:
    ```
    from indexify import IndexifyClient

    client = IndexifyClient()
    assert client.heartbeat() == True
    ```
    """

    def __init__(
        self,
        service_url: str = DEFAULT_SERVICE_URL,  # switch this to DEFAULT_SERVICE_URL_HTTPS for TLS
        namespace: str = "default",
        config_path: Optional[str] = None,
        *args,
        **kwargs,
    ):
        if config_path:
            with open(config_path, "r") as file:
                config = yaml.safe_load(file)

            if config.get("use_tls", False):
                tls_config = config["tls_config"]
                self._client = httpx.Client(
                    http2=True,
                    cert=(tls_config["cert_path"], tls_config["key_path"]),
                    verify=tls_config.get("ca_bundle_path", True),
                )
            else:
                self._client = httpx.Client(*args, **kwargs)
        else:
            self._client = httpx.Client(*args, **kwargs)

        self.namespace: str = namespace
        self.extraction_graphs: List[ExtractionGraph] = []
        self.labels: dict = {}
        self._service_url = service_url
        self._timeout = kwargs.get("timeout")

        # get namespace data
        response = self.get(f"namespaces/{self.namespace}")
        response.raise_for_status()
        resp_json = response.json()
        # initialize extraction_policies
        for eb in resp_json["namespace"]["extraction_graphs"]:
            self.extraction_graphs.append(ExtractionGraph.from_dict(eb))

    @classmethod
    def with_mtls(
        cls,
        cert_path: str,
        key_path: str,
        ca_bundle_path: Optional[str] = None,
        service_url: str = DEFAULT_SERVICE_URL,
        *args,
        **kwargs,
    ) -> "IndexifyClient":
        """
        Create a client with mutual TLS authentication. Also enables HTTP/2,
        which is required for mTLS.
        NOTE: mTLS must be enabled on the Indexify service for this to work.

        :param cert_path: Path to the client certificate. Resolution handled by httpx.
        :param key_path: Path to the client key. Resolution handled by httpx.
        :param args: Arguments to pass to the httpx.Client constructor
        :param kwargs: Keyword arguments to pass to the httpx.Client constructor
        :return: A client with mTLS authentication

        Example usage:
        ```
        from indexify import IndexifyClient

        client = IndexifyClient.with_mtls(
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
        )
        assert client.heartbeat() == True
        ```
        """
        if not (cert_path and key_path):
            raise ValueError("Both cert and key must be provided for mTLS")

        client_certs = (cert_path, key_path)
        verify_option = ca_bundle_path if ca_bundle_path else True
        client = IndexifyClient(
            *args,
            **kwargs,
            service_url=service_url,
            http2=True,
            cert=client_certs,
            verify=verify_option,
        )
        return client

    def _request(self, method: str, **kwargs) -> httpx.Response:
        response = self._client.request(method, timeout=self._timeout, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"exception: {exc}, response text: {response.text}")
            raise exc
        return response

    def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make a GET request to the Indexify service.

        :param endpoint: The endpoint to make the request to.

        Example usage:
        ```
        from indexify import IndexifyClient

        client = IndexifyClient()
        response = client.get("namespaces")
        print(response.json())
        ```
        """
        return self._request("GET", url=f"{self._service_url}/{endpoint}", **kwargs)

    def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make a POST request to the Indexify service.

        :param endpoint: The endpoint to make the request to.

        Example usage:

        ```
        from indexify import IndexifyClient

        client = IndexifyClient()
        response = client.post("namespaces", json={"name": "my-repo"})
        print(response.json())
        ```
        """
        return self._request("POST", url=f"{self._service_url}/{endpoint}", **kwargs)

    def put(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make a PUT request to the Indexify service.

        :param endpoint: The endpoint to make the request to.

        Example usage:

        ```
        from indexify import IndexifyClient

        client = IndexifyClient()
        response = client.put("namespaces", json={"name": "my-repo"})
        print(response.json())
        ```
        """
        return self._request("PUT", url=f"{self._service_url}/{endpoint}", **kwargs)

    def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make a DELETE request to the Indexify service.

        :param endpoint: The endpoint to make the request to.

        Example usage:

        ```
        from indexify import IndexifyClient

        client = IndexifyClient()
        response = client.delete("namespaces")
        print(response.json())
        ```
        """
        return self._request("DELETE", url=f"{self._service_url}/{endpoint}", **kwargs)

    def close(self):
        """
        Close the underlying httpx.Client.
        """
        self._client.close()

    # __enter__ and __exit__ allow the client to be used as a context manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def heartbeat(self, heartbeat_response="Indexify Server") -> bool:
        """
        Check if the Indexify service is alive.
        """
        response = self.get(f"")
        # Server responds with text: "Indexify Server"
        return response.text == heartbeat_response

    def namespaces(self) -> list[str]:
        """
        Get a list of all namespaces.
        """
        response = self.get(f"namespaces")
        namespaces_dict = response.json()["namespaces"]
        namespaces = []
        for item in namespaces_dict:
            namespaces.append(item["name"])
        return namespaces

    @classmethod
    def create_namespace(
        self,
        namespace: str,
        extraction_graphs: list = [],
        labels: dict = {},
        service_url: str = DEFAULT_SERVICE_URL,
    ) -> "IndexifyClient":
        """
        Create a new namespace.

        Returns:
            IndexifyClient: a new client with the given namespace
        """
        extraction_graphs = []
        for bd in extraction_graphs:
            if isinstance(bd, extraction_graphs):
                extraction_graphs.append(bd.to_dict())
            else:
                extraction_graphs.append(bd)

        req = {
            "name": namespace,
            "extraction_graphs": extraction_graphs,
            "labels": labels,
        }

        with httpx.Client() as client:
            client.post(f"{service_url}/namespaces", json=req)

        client = IndexifyClient(namespace=namespace, service_url=service_url)
        return client

    def _add_content_url(self, content):
        """
        Add download content_url url property
        """
        return {
            **content,
            "content_url": f"{self._service_url}/namespaces/{self.namespace}/content/{content['id']}/download",
        }

    def indexes(self) -> List[Index]:
        """
        Get the indexes of the current namespace.

        Returns:
            List[Index]: list of indexes in the current namespace
        """
        response = self.get(f"namespaces/{self.namespace}/indexes")
        response.raise_for_status()
        return response.json()["indexes"]

    def extractors(self) -> List[Extractor]:
        """
        Get a list of all extractors.

        Returns:
            List[Extractor]: list of extractors
        """
        response = self.get(f"extractors")
        extractors_dict = response.json()["extractors"]
        extractors = []
        for ed in extractors_dict:
            extractors.append(Extractor.from_dict(ed))
        return extractors

    def get_extraction_policies(self):
        """
        Retrieve and update the list of extraction policies for the current namespace.
        """
        response = self.get(f"namespaces/{self.namespace}")
        response.raise_for_status()

        self.extraction_policies = []
        for eb in response.json()["namespace"]["extraction_policies"]:
            self.extraction_policies.append(ExtractionPolicy.from_dict(eb))
        return self.extraction_policies

    def create_extraction_graph(self, extraction_graph: ExtractionGraph):
        """
        Create a new extraction graph.

        Args:
            - extraction_graph (ExtractionGraph): the extraction graph to create
        """
        req = extraction_graph.to_dict()
        req["namespace"] = self.namespace
        request_body = json.dumps(req, default=json_set_default)
        response = self.post(
            f"namespaces/{self.namespace}/extraction_graphs",
            data=request_body,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return

    def get_content_metadata(self, content_id: str) -> dict:
        """
        Get metadata for a specific content ID in a given index.

        Args:
            - content_id (str): content id to query
        """
        response = self.get(f"namespaces/{self.namespace}/content/{content_id}")
        response.raise_for_status()
        return response.json()

    def get_extracted_content(
        self,
        content_id: str = None,
    ):
        """
        Get list of content from current namespace.

        Args:
            - parent_id (str): Optional filter for parent id
            - labels_eq (str): Optional filter for labels
        """
        params = {"parent_id": content_id}

        response = self.get(f"namespaces/{self.namespace}/content", params=params)
        response.raise_for_status()
        return [
            self._add_content_url(content)
            for content in response.json()["content_list"]
        ]

    def download_content(self, id: str) -> bytes:
        """
        Download content from id. Return bytes

        Args:
            - id (str): id of content to download
        """
        response = self.get(f"namespaces/{self.namespace}/content/{id}/download")
        try:
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as exc:
            raise ApiException(exc.response.text)

    def add_documents(
        self,
        extraction_graphs: Union[str, List[str]],
        documents: Union[Document, str, List[Union[Document, str]]],
        doc_id=None,
    ) -> None:
        """
        Add documents to current namespace.

        Args:
            - documents (Union[Document, str, List[Union[Document, str]]]): this can be a list of strings, list of Documents or a mix of both
        """
        if isinstance(extraction_graphs, str):
            extraction_graphs = [extraction_graphs]
        if isinstance(documents, Document):
            documents = [documents]
        elif isinstance(documents, str):
            documents = [Document(documents, {}, id=doc_id)]
        elif isinstance(documents, list):
            new_documents = []
            for item in documents:
                if isinstance(item, Document):
                    new_documents.append(item)
                elif isinstance(item, str):
                    new_documents.append(
                        Document(item, {}, id=None)
                    )  # don't pass in id for a string content because doesn't make sense to have same content id for all strings
                else:
                    raise ValueError(
                        "List items must be either Document instances or strings."
                    )
            documents = new_documents
        else:
            raise TypeError(
                "Invalid type for documents. Expected Document, str, or list of these."
            )

        req = {
            "documents": [doc._asdict() for doc in documents],
            "extraction_graph_names": extraction_graphs,
        }
        response = self.post(
            f"namespaces/{self.namespace}/add_texts",
            json=req,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    def delete_documents(self, document_ids: List[str]) -> None:
        """
        Delete documents from current namespace.

        Args:
            - document_ids (List[str]): list of document ids to delete
        """
        req = {"content_ids": document_ids}
        response = self.delete(
            f"namespaces/{self.namespace}/content",
            json=req,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    def update_content(self, document_id: str, path: str) -> None:
        """
        Update a piece of content with a new file

        Args:
            - path (str): relative path to the file to be uploaded
        """
        with open(path, "rb") as f:
            response = self.put(
                f"namespaces/{self.namespace}/content/{document_id}", files={"file": f}
            )
            response.raise_for_status()

    def get_structured_data(self, content_id: str) -> dict:
        """
        Query metadata for a specific content ID in a given index.

        Args:
            - content_id (str): content id to query
        """
        response = self.get(
            f"namespaces/{self.namespace}/content/{content_id}/metadata"
        )
        response.raise_for_status()
        return response.json().get("metadata", [])

    def search_index(
        self, name: str, query: str, top_k: int, filters: List[str] = []
    ) -> list[TextChunk]:
        """
        Search index in the current namespace.

        Args:
            - name (str): name of index to search
            - query (str): query string
            - top_k (int): top k nearest neighbors to be returned
            - filters (List[str]): list of filters to apply
        """
        req = {"index": name, "query": query, "k": top_k, "filters": filters}
        response = self.post(
            f"namespaces/{self.namespace}/search",
            json=req,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()["results"]

    def upload_file(self, extraction_graphs: Union[str, List[str]], path: str, id=None, labels: dict = {}) -> str:
        """
        Upload a file.

        Args:
            - path (str): relative path to the file to be uploaded
            - labels (dict): labels to be associated with the file
        """
        if isinstance(extraction_graphs, str):
            extraction_graphs = [extraction_graphs]
        params = {"extraction_graph_names": extraction_graphs}
        if id is not None:
            params["id"] = id
        with open(path, "rb") as f:
            response = self.post(
                f"namespaces/{self.namespace}/upload_file",
                files={"file": f},
                data=labels,
                params=params,
            )
            response.raise_for_status()
            response_json = response.json()
            return response_json["content_id"]

    def list_schemas(self) -> List[str]:
        """
        List all schemas in the current namespace.
        """
        response = self.get(f"namespaces/{self.namespace}/schemas")
        response.raise_for_status()
        return response.json()

    def get_content_tree(self, content_id: str):
        """
        Get content tree for a given content id

        Args:
            - content_id (str): id of content
        """
        response = self.get(
            f"namespaces/{self.namespace}/content/{content_id}/content-tree"
        )
        response.raise_for_status()
        return response.json()

    def sql_query(self, query: str):
        """
        Execute a SQL query.

        Args:
            - query (str): SQL query to be executed
        """
        req = {"query": query}
        response = self.post(
            f"namespaces/{self.namespace}/sql_query",
            json=req,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()
        rows = []
        for row in result["rows"]:
            data = row["data"]
            rows.append(data)
        return SqlQueryResult(result=rows)

    def ingest_remote_file(
        self, extraction_graphs: Union[str, List[str]], url: str, mime_type: str, labels: Dict[str, str], id=None
    ):
        if isinstance(extraction_graphs, str):
            extraction_graphs = [extraction_graphs]
        req = {"url": url, "mime_type": mime_type, "labels": labels, "id": id, "extraction_graph_names": extraction_graphs}
        response = self.post(
            f"namespaces/{self.namespace}/ingest_remote_file",
            json=req,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def generate_unique_hex_id(self):
        """
        Generate a unique hexadecimal identifier

        Returns:
            str: a unique hexadecimal string
        """
        return uuid.uuid4().hex[:16]

    def generate_hash_from_string(self, input_string: str):
        """
        Generate a hash for the given string and return it as a hexadecimal string.

        Args:
            input_string (str): The input string to hash.

        Returns:
            str: The hexadecimal hash of the input string.
        """
        hash_object = hashlib.sha256(input_string.encode())
        return hash_object.hexdigest()[:16]
