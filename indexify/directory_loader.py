from indexify_extractor_sdk import Content
from abc import ABC, abstractmethod
from typing import List, Optional, Type, Union
import os
import json
import requests

class DataLoader(ABC):
    @abstractmethod
    def load(self, limit: int) -> List[Content]:
        pass

    @abstractmethod
    def state(self) -> dict:
        pass

class SimpleDirectoryLoader(DataLoader):
    def __init__(self, directory: str, file_extensions: Optional[List[str]] = None):
        self.directory = directory
        self.file_extensions = file_extensions
        self.processed_files = set()

    def load(self, limit: int) -> List[Content]:
        contents = []
        for root, _, files in os.walk(self.directory):
            for file in files:
                if len(contents) >= limit:
                    break
                if self.file_extensions is None or any(file.endswith(ext) for ext in self.file_extensions):
                    file_path = os.path.join(root, file)
                    if file_path not in self.processed_files:
                        f = open(file_path, "rb")
                        contents.append(Content(data=f.read()))
                        self.processed_files.add(file_path)
        return contents

    def state(self) -> dict:
        return {
            "processed_files": list(self.processed_files)
        }