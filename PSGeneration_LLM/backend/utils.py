import os
import uuid
import json

# Base project directory (parent of this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DocParser folder (guaranteed correct regardless of import location)
DOCPARSER_DIR = os.path.join(BASE_DIR, "DocParser")

# Key folders
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
UPDATED_DIR = os.path.join(DATA_DIR, "updated")
VECTOR_DIR = os.path.join(DATA_DIR, "vectorstores")
PARSED_JSON_DIR = os.path.join(DOCPARSER_DIR, "ParsedJSON")
LATEST_IDS_PATH = os.path.join(DOCPARSER_DIR, "latest_ids.json")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(UPDATED_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)
os.makedirs(PARSED_JSON_DIR, exist_ok=True)

def new_id(prefix="doc"):
    """
    Generate a unique ID for uploaded documents.
    Example: ps_fa8d2e1c3b47
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def update_latest_ids(**kwargs):
    """
    Update the global latest_ids.json in the DocParser directory.
    """
    ids_file = LATEST_IDS_PATH
    if os.path.exists(ids_file):
        with open(ids_file, "r", encoding="utf-8") as f:
            try:
                ids = json.load(f)
                if not isinstance(ids, dict):
                    ids = {}
            except Exception:
                ids = {}
    else:
        ids = {}
    ids.update(kwargs)
    with open(ids_file, "w", encoding="utf-8") as f:
        json.dump(ids, f, indent=2)