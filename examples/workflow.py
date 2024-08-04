from indexify import Content, Feature, extractor
from typing import List
from pydantic import BaseModel, Field

class ChunkOptions(BaseModel):
    chunk_size: int = 100

class ProfanityOptions(BaseModel):
    slangs: List[str] = Field(default_factory=lambda: [])


@extractor(description="Extracts text from PDFs")
def pdf_extraction(content: Content) -> List[Content]:
    pass

def filter_for_profanity(content: Content, params: ProfanityOptions) -> List[Content]:
    if "fuck" in content.data.decode('utf-8'):
        return []
    return [content]


def object_detector(content: Content) -> List[Content]:
    pass

@extractor(description="Chunks text into paragraphs")
def text_chunks(content: Content, params: ChunkOptions) -> List[Content]:
    pass

@extractor(description="Embeds text chunks")
def chunk_embeddings(content: Content) -> List[Feature]:
    pass

pipeline = pdf_extraction | (filter_for_profanity, object_detector) | text_chunks(params={"chunk_size": 500}) | chunk_embeddings


if __name__ == "__main__":
    content = Content.from_file("sample.pdf")
    pipeline(content)