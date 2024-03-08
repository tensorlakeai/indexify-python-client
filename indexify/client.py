import httpx
import json
from collections import namedtuple
from .settings import DEFAULT_SERVICE_URL
from .extractor import Extractor
from .extraction_policy import ExtractionPolicy
from .index import Index
from .utils import json_set_default
from .data_containers import TextChunk
from indexify.exceptions import ApiException

from typing import List, Optional, Union

Document = namedtuple("Document", ["text", "labels"])


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
        service_url: str = DEFAULT_SERVICE_URL,
        namespace: str = "default",
        *args,
        **kwargs,
    ):
        self.namespace: str = namespace
        self.extraction_policies: List[ExtractionPolicy] = []
        self.labels: dict = {}
        self._service_url = service_url
        self._client = httpx.Client(*args, **kwargs)

        # get namespace data
        response = self.get(f"namespaces/{self.namespace}")
        response.raise_for_status()
        resp_json = response.json()
        # initialize extraction_policies
        for eb in resp_json["namespace"]["extraction_policies"]:
            self.extraction_policies.append(ExtractionPolicy.from_dict(eb))

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
        response = self._client.request(method, **kwargs)
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
        # Not Implemented
        raise NotImplementedError

    def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        # Not Implemented
        raise NotImplementedError

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
        extraction_policies: list = [],
        labels: dict = {},
    ) -> "IndexifyClient":
        """
        Create a new namespace.

        Returns:
            IndexifyClient: a new client with the given namespace
        """
        extraction_policies = []
        for bd in extraction_policies:
            if isinstance(bd, ExtractionPolicy):
                extraction_policies.append(bd.to_dict())
            else:
                extraction_policies.append(bd)
        req = {
            "name": namespace,
            "extraction_policies": extraction_policies,
            "labels": labels,
        }

        client = IndexifyClient(namespace=namespace)
        client.post(f"namespaces", json=req)
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

    def add_extraction_policy(
        self,
        extractor: str,
        name: str,
        input_params: dict = {},
        labels_eq: str = None,
        content_source="ingestion",
    ) -> dict:
        """Add a new extraction policy.

        Args:
            - extractor (str): Name of the extractor
            - name (str): Name for this instance
            - input_params (dict): Dictionary containing extractor input params
            - filter (Filter): Optional filter for this extractor

        Returns:
            dict: response payload

        Examples:
            >>> repo.add_extraction_policy("EfficientNet", "efficientnet")

            >>> repo.add_extraction_policy("MiniLML6", "minilm")

        """
        req = {
            "extractor": extractor,
            "name": name,
            "input_params": input_params,
            "filters_eq": labels_eq,
            "content_source": content_source,
        }
        if req["filters_eq"] == None:
            del req["filters_eq"]

        request_body = json.dumps(req, default=json_set_default)
        response = self.post(
            f"namespaces/{self.namespace}/extraction_policies",
            data=request_body,
            headers={"Content-Type": "application/json"},
        )

        # update self.extractor_bindings
        self.get_extraction_policies()

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ApiException(exc.response.text)
        return

    def get_content(
        self,
        parent_id: str = None,
        labels_eq: str = None,
    ):
        """
        Get list of content from current namespace.

        Args:
            - parent_id (str): Optional filter for parent id
            - labels_eq (str): Optional filter for labels
        """
        params = {}
        if parent_id:
            params.update({"parent_id": parent_id})
        if labels_eq:
            params.update({"labels_eq": labels_eq})

        response = self.get(f"namespaces/{self.namespace}/content", params=params)
        response.raise_for_status()
        return [
            self._add_content_url(content)
            for content in response.json()["content_list"]
        ]
    
    def download_content(self, id:str) -> bytes:
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
        self, documents: Union[Document, str, List[Union[Document, str]]]
    ) -> None:
        """
        Add documents to current namespace.

        Args:
            - documents (Union[Document, str, List[Union[Document, str]]]): this can be a list of strings, list of Documents or a mix of both
        """
        if isinstance(documents, Document):
            documents = [documents]
        elif isinstance(documents, str):
            documents = [Document(documents, {})]
        elif isinstance(documents, list):
            new_documents = []
            for item in documents:
                if isinstance(item, Document):
                    new_documents.append(item)
                elif isinstance(item, str):
                    new_documents.append(Document(item, {}))
                else:
                    raise ValueError(
                        "List items must be either Document instances or strings."
                    )
            documents = new_documents
        else:
            raise TypeError(
                "Invalid type for documents. Expected Document, str, or list of these."
            )

        req = {"documents": documents}
        response = self.post(
            f"namespaces/{self.namespace}/add_texts",
            json=req,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    def query_metadata(self, index_name: str, content_id: str) -> dict:
        """
        Query metadata for a specific content ID in a given index.

        Args:
            - index_name (str): index to query
            - content_id (str): content id to query
        """
        params = {"index": index_name, "content_id": content_id}
        response = self.get(f"namespaces/{self.namespace}/metadata", params=params)
        response.raise_for_status()
        return response.json()["attributes"]

    def search_index(self, name: str, query: str, top_k: int) -> list[TextChunk]:
        """
        Search index in the current namespace.

        Args:
            - name (str): name of index to search
            - query (str): query string
            - top_k (int): top k nearest neighbors to be returned
        """
        req = {"index": name, "query": query, "k": top_k}
        response = self.post(
            f"namespaces/{self.namespace}/search",
            json=req,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()["results"]

    def upload_file(self, path: str):
        """
        Upload a file.

        Args:
            - path (str): relative path to the file to be uploaded
        """
        with open(path, "rb") as f:
            response = self.post(
                f"namespaces/{self.namespace}/upload_file",
                files={"file": f},
                timeout=None,
            )
            response.raise_for_status()
