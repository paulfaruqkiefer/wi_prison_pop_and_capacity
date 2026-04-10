import os
import zipfile
import pandas as pd

# Paths based on previous script
WEEKLY_DIR = "doc_reports/weekly"
ARCHIVE_DIR = "doc_reports/archives"
EXTRACT_DIR = "doc_reports/extracted_pdfs"
os.makedirs(EXTRACT_DIR, exist_ok=True)

def unpack_archives():
    print("Unpacking ZIP archives...")
    for item in os.listdir(ARCHIVE_DIR):
        if item.endswith(".zip"):
            with zipfile.ZipFile(os.path.join(ARCHIVE_DIR, item), 'r') as zip_ref:
                # Extract to a flattened folder to make processing easier
                zip_ref.extractall(EXTRACT_DIR)

# Execution
unpack_archives()

