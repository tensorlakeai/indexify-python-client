# Langhchain Integration for Indexify

Indexify complements LangChain by providing a robust platform for indexing large volume of multi-modal content such as PDFs, raw text, audio and video. It provides a retriever API to retrieve context for LLMs.

You can use our LangChain retriever from our repo located in `indexify_langchain/retriever.py` to begin retrieving your data.

Below is an example

```python
# setup your indexify client
from indexify.client import IndexifyClient
client = IndexifyClient()


# add docs
from indexify.client import Document

client.bind_extractor(
    "openai-embedding-ada-002-extractor",
    "openai-embedding",
)

client.add_documents(
    [
        Document(
            text="Indexify is amazing!",
            labels={"source": "indexify-example"},
        ),
        Document(
            text="Indexify is also a retrieval service for LLM agents!",
            labels={"source": "indexify-example"},
        )
    ]
)


# implement retriever from indexify repo
from retriever import IndexifyRetriever

params = {"name": "minilm-embedding", "top_k": 3}
retriever = IndexifyRetriever(client=client, params=params)

docs = retriever.get_relevant_documents("indexify")
```