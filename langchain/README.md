# Indexify Langchain

[![PyPI version](https://badge.fury.io/py/indexify-langchain.svg)](https://badge.fury.io/py/indexify-langchain)

This package contains our LangChain Retriever component, which leverages LLMs to fetch data with langchain. In order to use this retriever you must have Indexify, to read more about getting started with indexify you can read our [getting started documentation](https://getindexify.ai/getting_started/).

### Requirements
- [Indexify](https://getindexify.ai/getting_started/)
- [Indexify Python Client](https://pypi.org/project/indexify/)

### Indexify Retriever RAG Example
Below is an example on how you can use our indexify client and langchain retriever with OpenAI in a basic RAG example.

```python
from indexify_langchain import IndexifyRetriever

# Initialize Indexify client
client = IndexifyClient.create_namespace("test-langchain")
client.bind_extractor(
    "tensorlake/minilm-l6",
    "minilml6",
)

# Add Documents
client.add_documents("Lucas is from Atlanta Georgia")

# Initialize retriever
params = {"name": "minilml6.embedding", "top_k": 9}
retriever = IndexifyRetriever(client=client, params=params)

# Setup Chat Prompt Template
from langchain.prompts import ChatPromptTemplate

template = """You are an assistant for question-answering tasks. 
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, just say that you don't know. 
Use three sentences maximum and keep the answer concise.
Question: {question} 
Context: {context} 
Answer:
"""
prompt = ChatPromptTemplate.from_template(template)

# Ask llm question with retriever context
from langchain_openai import ChatOpenAI
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# Ask LLM Question
query = "Where is Lucas from?"
print(rag_chain.invoke(query))
```