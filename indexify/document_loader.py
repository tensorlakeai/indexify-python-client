import os
import requests
from typing import List, Optional
from indexify import IndexifyClient

def simple_directory_loader(
    client: IndexifyClient,
    extraction_graph: str,
    directory: str,
    file_extensions: Optional[List[str]] = None,
    download_urls: Optional[List[str]] = None,
    wait_for_extraction: bool = True
) -> List[str]:
    """
    Load and process documents from a directory or download from URLs.

    Args:
        client (IndexifyClient): An instance of IndexifyClient.
        extraction_graph (str): The name of the extraction graph to use.
        directory (str): The directory to load files from or save downloaded files to.
        file_extensions (Optional[List[str]]): List of file extensions to process. If None, process all files.
        download_urls (Optional[List[str]]): List of URLs to download files from.
        wait_for_extraction (bool): Whether to wait for extraction to complete before returning.

    Returns:
        List[str]: A list of content IDs for the processed documents.
    """
    os.makedirs(directory, exist_ok=True)
    content_ids = []

    if download_urls:
        for url in download_urls:
            file_name = f"{url.split('/')[-1]}"
            file_path = os.path.join(directory, file_name)
            download_file(url, file_path)
            print(f"Downloaded: {file_path}")

    for root, _, files in os.walk(directory):
        for file in files:
            if file_extensions is None or any(file.endswith(ext) for ext in file_extensions):
                file_path = os.path.join(root, file)
                content_id = client.upload_file(extraction_graph, file_path)
                if wait_for_extraction:
                    client.wait_for_extraction(content_id)
                content_ids.append(content_id)
                print(f"Processed: {file_path}")

    return content_ids

def download_file(url: str, save_path: str):
    """
    Download a file from a given URL and save it to the specified path.

    Args:
        url (str): The URL of the file to download.
        save_path (str): The path where the downloaded file will be saved.
    """
    response = requests.get(url)
    with open(save_path, 'wb') as f:
        f.write(response.content)
