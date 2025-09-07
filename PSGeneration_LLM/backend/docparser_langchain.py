import os
import json
import numpy as np
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from utils import UPLOAD_DIR, PARSED_JSON_DIR, LATEST_IDS_PATH
import sys



sys.path.append(os.path.join(os.path.dirname(__file__), "DocParser"))
from CustomDocxParser import parse_docx_comprehensively

# Import the logging functions for chunk/embedding/mapping logs
from log_chunk_embeddings_and_mappings import write_old_mockup_log, write_new_mockup_log

VECTOR_DIR = os.path.join(os.path.dirname(__file__), "data", "vectorstores")
os.makedirs(VECTOR_DIR, exist_ok=True)

def normalize(text):
    """Normalize text for matching—strip, collapse spaces, lower-case."""
    return ' '.join(text.strip().split()).lower()

def load_and_chunk_docx(path, chunk_size=100, chunk_overlap=50, status_updates=None):
    """
    Parses a .docx document and extracts paragraph and table cell level chunks for embedding.

    Returns:
        List[dict]: Each dict contains 'text', 'type', and various metadata fields.
    """
    if status_updates is not None:
        status_updates.append("Parsing document: " + os.path.basename(path))

    parsed_json = parse_docx_comprehensively(path)
    base = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(PARSED_JSON_DIR, f"{base}_PARSED.json")
    with open(out_path, "w", encoding="utf-8") as jf:
        json.dump(parsed_json, jf, ensure_ascii=False, indent=2)
    if status_updates is not None:
        status_updates.append(f"Saved full parsed JSON to {out_path}")

    chunks = []
    # Extract only paragraph/table-level chunks
    for item in parsed_json.get("paragraphs_and_tables", []):
        text = item.get("text", "").strip()
        if text:
            metadata = {}
            for k in item.keys():
                if k != "text":
                    metadata[k] = item[k]
            metadata["section_path"] = item.get("section_path", "")
            metadata["para_idx"] = item.get("para_idx", 0)
            chunk = {
                "text": text,
                "type": item.get("type"),
                "style": item.get("style"),
                "alignment": item.get("alignment"),
                "runs": item.get("runs"),
                "source": "paragraph",
                "metadata": metadata
            }
            chunks.append(chunk)
    for item in parsed_json.get("paragraphs_and_tables", []):
        if item.get("type") == "table":
            for row in item.get("data", []):
                for cell_text in row:
                    if cell_text:
                        chunk = {
                            "text": cell_text,
                            "type": "table_cell",
                            "table_index": item.get("table_index"),
                            "source": "table_cell",
                            "metadata": {
                                "table_index": item.get("table_index"),
                                "section_path": item.get("section_path", ""),
                                "para_idx": item.get("para_idx", 0)
                            }
                        }
                        chunks.append(chunk)

    if status_updates is not None:
        status_updates.append(f"Extracted {len(chunks)} chunks for embedding.")

    return chunks

def create_vectorstore(doc_id, path, status_updates=None, chunk_size=100, chunk_overlap=50):
    """
    Creates FAISS vectorstore for a docx document, stores chunk metadata in LangChain format.

    Returns:
        Dict: Contains 'status_updates'.
    """
    if status_updates is None:
        status_updates = []
    status_updates.append("Starting vectorstore creation for doc_id: " + doc_id)
    chunks = load_and_chunk_docx(path, chunk_size=chunk_size, chunk_overlap=chunk_overlap, status_updates=status_updates)

    docs = []
    for i, chunk in enumerate(chunks):
        chunk['index'] = i
        from langchain.docstore.document import Document as LC_Document
        doc = LC_Document(page_content=chunk["text"], metadata=chunk.get("metadata", {}))
        docs.append(doc)
    status_updates.append("Creating OpenAI embeddings.")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    status_updates.append("Generating FAISS vectorstore.")
    vectorstore = FAISS.from_documents(docs, embeddings)
    out_path = os.path.join(VECTOR_DIR, f"{doc_id}.faiss")
    vectorstore.save_local(out_path)
    status_updates.append(f"Vectorstore persisted at {out_path}.")
    return {"status_updates": status_updates}

def load_vectorstore(doc_id, status_updates=None):
    """
    Loads an existing FAISS vectorstore for a doc_id.

    Returns:
        FAISS vectorstore object.
    """
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    if status_updates is not None:
        status_updates.append(f"Loading vectorstore for doc_id: {doc_id}.")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    path = os.path.join(VECTOR_DIR, f"{doc_id}.faiss")
    vs = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    if status_updates is not None:
        status_updates.append(f"Loaded vectorstore for {doc_id}.")
    return vs

def build_mo_to_ps_exact_mapping(mockup_chunks, ps_chunks):
    """
    Map each chunk in mockup_original to its exact text match in psdocx_original.

    Returns:
        Dict: {MO_chunk_index: PS_chunk_index, ...}
    """
    chunk_map = {}
    normalized_ps = [normalize(c['text']) for c in ps_chunks]
    print("Normalized Old PS Chunks:")
    for idx, nps in enumerate(normalized_ps):
        print(f"{idx}: {repr(nps)}")
    for i, mo in enumerate(mockup_chunks):
        mo_norm = normalize(mo['text'])
        print(f"\nMockup chunk {i}: {repr(mo_norm)}")
        found = False
        for j, ps_norm in enumerate(normalized_ps):
            if mo_norm == ps_norm:
                print(f" --> MATCHES PS chunk {j}")
                chunk_map[i] = j
                found = True
                break
        if not found:
            print(" --> No match in PS")
    return chunk_map
def get_all_chunks(doc_id):
    """
    Loads all chunks from parsed JSON for a doc.

    Returns:
        List[dict]: Each dict represents a chunk.
    """
    base = os.path.join(PARSED_JSON_DIR, f"{doc_id}_PARSED.json")
    with open(base, "r", encoding="utf-8") as f:
        parsed = json.load(f)
    return [item for item in parsed.get("paragraphs_and_tables", []) if item.get("text", "").strip()]

def get_all_embeddings(doc_id):
    """
    Loads all embeddings for a doc_id from the FAISS vectorstore.

    Returns:
        List[np.ndarray]: Embeddings for each chunk in order.
    """
    embeddings = []
    vs = load_vectorstore(doc_id)
    # For newer langchain/faiss: index_to_docstore_id is a dict: {index: docstore_id}
    # For older: index_to_docstore_id may be a list; handle both for robustness
    index_to_docstore_id = vs.index_to_docstore_id

    # If it's a dict, sort by index (key)
    if isinstance(index_to_docstore_id, dict):
        for idx in sorted(index_to_docstore_id.keys()):
            emb = vs.index.reconstruct(idx)
            embeddings.append(emb)
    else:  # fallback for old style list
        for idx, key in enumerate(index_to_docstore_id):
            emb = vs.index.reconstruct(idx)
            embeddings.append(emb)
    return embeddings

def log_chunk_embeddings_and_mappings(
    old_mockup_id, new_mockup_id, ps_doc_id
):
    """
    Main integration function to perform logging after all chunking/embedding/mapping.

    Writes:
        - Old Mockup chunk/embedding/mapping log
        - New Mockup chunk/embedding log
    """
    # 1. Get chunks
    old_mockup_chunks = get_all_chunks(old_mockup_id)
    new_mockup_chunks = get_all_chunks(new_mockup_id)
    ps_chunks = get_all_chunks(ps_doc_id)
    # 2. Get embeddings
    old_mockup_embeddings = get_all_embeddings(old_mockup_id)
    new_mockup_embeddings = get_all_embeddings(new_mockup_id)
    # 3. Build mapping
    chunk_map = build_mo_to_ps_exact_mapping(old_mockup_chunks, ps_chunks)
    # 4. Write logs
    write_old_mockup_log(old_mockup_chunks, old_mockup_embeddings, ps_chunks, chunk_map)
    write_new_mockup_log(new_mockup_chunks, new_mockup_embeddings)

########################
# BEST MATCHING UTILS  #
########################

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two numpy arrays."""
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

def find_best_old_mockup_for_new_mockup(new_mock_id, old_mock_id, similarity_threshold=0.0):
    """
    For each chunk in new mockup, find the best matching chunk (by embedding similarity) in old mockup.

    Returns:
        matches: List[dict] -- Each dict: {"new_idx": int, "old_idx": int, "similarity": float}
        logs: List[str]
    """
    logs = []
    new_chunks = get_all_chunks(new_mock_id)
    old_chunks = get_all_chunks(old_mock_id)
    new_embs = get_all_embeddings(new_mock_id)
    old_embs = get_all_embeddings(old_mock_id)

    matches = []
    for i, (nchunk, nemb) in enumerate(zip(new_chunks, new_embs)):
        best_sim = -1
        best_j = None
        for j, oemb in enumerate(old_embs):
            sim = cosine_similarity(nemb, oemb)
            if sim > best_sim:
                best_sim = sim
                best_j = j
        if best_sim >= similarity_threshold:
            matches.append({"new_idx": i, "old_idx": best_j, "similarity": best_sim})
            logs.append(f"New chunk {i} best matches old chunk {best_j} (sim={best_sim:.4f})")
        else:
            matches.append({"new_idx": i, "old_idx": None, "similarity": best_sim})
            logs.append(f"New chunk {i} has no match above threshold, best sim={best_sim:.4f}")
    return matches, logs

def find_best_ps_for_old_mockup(old_mock_id, ps_doc_id, similarity_threshold=0.0):
    """
    For each chunk in old mockup, find the best matching chunk (by embedding similarity) in PS.

    Returns:
        matches: List[dict] -- Each dict: {"old_idx": int, "ps_idx": int, "similarity": float}
        logs: List[str]
    """
    logs = []
    old_chunks = get_all_chunks(old_mock_id)
    ps_chunks = get_all_chunks(ps_doc_id)
    old_embs = get_all_embeddings(old_mock_id)
    ps_embs = get_all_embeddings(ps_doc_id)

    matches = []
    for i, (ochunk, oemb) in enumerate(zip(old_chunks, old_embs)):
        best_sim = -1
        best_j = None
        for j, pemb in enumerate(ps_embs):
            sim = cosine_similarity(oemb, pemb)
            if sim > best_sim:
                best_sim = sim
                best_j = j
        if best_sim >= similarity_threshold:
            matches.append({"old_idx": i, "ps_idx": best_j, "similarity": best_sim})
            logs.append(f"Old chunk {i} best matches PS chunk {best_j} (sim={best_sim:.4f})")
        else:
            matches.append({"old_idx": i, "ps_idx": None, "similarity": best_sim})
            logs.append(f"Old chunk {i} has no match above threshold, best sim={best_sim:.4f}")
    return matches, logs

# The function update_ps_document_closest is expected in updater.py, not here.
# But for completeness, you can re-export it if you want easy imports in app.py:
try:
    from updater import update_ps_document_closest
except ImportError:
    def update_ps_document_closest(*args, **kwargs):
        raise ImportError("update_ps_document_closest is not implemented or not in updater.py")

if __name__ == "__main__":
    ids_path = LATEST_IDS_PATH
    if not os.path.exists(ids_path):
        raise FileNotFoundError(
            f"Could not find latest_ids.json at {ids_path}. "
            f"Please upload your documents via the API first."
        )
    with open(ids_path, "r", encoding="utf-8") as f:
        ids = json.load(f)
    old_mockup_id = ids.get("old_mockup_id")
    new_mockup_id = ids.get("new_mockup_id")
    ps_doc_id = ids.get("ps_doc_id")
    if not all([old_mockup_id, new_mockup_id, ps_doc_id]):
        raise ValueError(
            f"Missing IDs in latest_ids.json. Found: {ids}. "
            f"Please upload all required documents via the API."
        )
    print(f"Using IDs: old_mockup_id={old_mockup_id}, new_mockup_id={new_mockup_id}, ps_doc_id={ps_doc_id}")
    log_chunk_embeddings_and_mappings(old_mockup_id, new_mockup_id, ps_doc_id)