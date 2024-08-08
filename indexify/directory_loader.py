from .data_loader import DataLoader
from .data import Content, ContentMetadata
from typing import List, Optional
import os

class SimpleDirectoryLoader(DataLoader):
    def __init__(self, directory: str, file_extensions: Optional[List[str]] = None):
        self.directory = directory
        self.file_extensions = file_extensions
        self.processed_files = set()

    def load(self, limit: int) -> List[ContentMetadata]:
        contents_metadata = []
        for root, _, files in os.walk(self.directory):
            for file in files:
                if len(contents_metadata) >= limit:
                    break
                if self.file_extensions is None or any(file.endswith(ext) for ext in self.file_extensions):
                    file_path = os.path.join(root, file)
                    if file_path not in self.processed_files:
                        contents_metadata.append(ContentMetadata.load_from_file(file_path))
                        self.processed_files.add(file_path)
                        
        return contents_metadata

    def state(self) -> dict:
        return {
            "processed_files": list(self.processed_files)
        }
