# backend/vector_store.py
import os
import json
import numpy as np
from utils import EMBED_DIR
from numpy.linalg import norm
import logging

logger = logging.getLogger(__name__)

def load_manifest(doc_id):
    meta_path = os.path.join(EMBED_DIR, f"{doc_id}.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Manifest for {doc_id} not found")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_embeddings(doc_id):
    manifest = load_manifest(doc_id)
    emb_path = manifest["emb_path"]
    arr = np.load(emb_path)
    chunks = manifest["chunks"]
    return chunks, arr

def cosine_similarity_matrix(A, B):
    """
    A: (n, d)
    B: (m, d)
    returns (n, m) matrix of cosine similarities
    """
    # normalize
    a_norm = A / np.linalg.norm(A, axis=1, keepdims=True)
    b_norm = B / np.linalg.norm(B, axis=1, keepdims=True)
    return np.dot(a_norm, b_norm.T)

def find_best_matches(src_id, tgt_id, top_k=1):
    """
    For all chunks in src, find best matches in tgt.
    returns list of matches [(src_index, tgt_index, sim), ...] for top_k=1 per src
    """
    src_chunks, src_emb = load_embeddings(src_id)
    tgt_chunks, tgt_emb = load_embeddings(tgt_id)

    sims = cosine_similarity_matrix(src_emb, tgt_emb)  # (n_src, n_tgt)
    matches = []
    for i in range(sims.shape[0]):
        # top_k best target indices
        idxs = np.argsort(-sims[i])[:top_k]
        for j in idxs:
            matches.append({
                "src_index": src_chunks[i]["index"],
                "src_text": src_chunks[i]["text"],
                "tgt_index": tgt_chunks[j]["index"],
                "tgt_text": tgt_chunks[j]["text"],
                "similarity": float(sims[i, j])
            })
    return matches
