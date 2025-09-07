import os
import json
import numpy as np

# Directory to store logs
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "ParsedData")
os.makedirs(DATA_DIR, exist_ok=True)

def write_old_mockup_log(
    old_mockup_chunks, 
    old_mockup_embeddings,
    ps_chunks,
    chunk_map,
    out_filename="old_mockup_chunks_log.txt"
):
    """
    Logs all chunks of Old Mockup, their embeddings, and mapping with Old PS.

    Args:
        old_mockup_chunks (list): List of dicts, each chunk from Old Mockup
        old_mockup_embeddings (list): List of vectors (np.ndarray or list), each embedding for old mockup chunk
        ps_chunks (list): List of dicts, each chunk from Old PS
        chunk_map (dict): Mapping {old_mockup_chunk_index: ps_chunk_index}
        out_filename (str): Output log filename

    Returns: str (output path)
    """
    out_path = os.path.join(DATA_DIR, out_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("=== Old Mockup Chunks, Embeddings, and Mapping to Old PS ===\n")
        for idx, chunk in enumerate(old_mockup_chunks):
            emb = old_mockup_embeddings[idx] if idx < len(old_mockup_embeddings) else None
            f.write(f"\n--- Old Mockup Chunk {idx+1} ---\n")
            # Texts
            f.write(f"Text from old mock up: {chunk['text']}\n")
            ps_idx = chunk_map.get(idx)
            if ps_idx is not None and ps_idx < len(ps_chunks):
                f.write(f"Text from old ps: {ps_chunks[ps_idx]['text']}\n")
            else:
                f.write("Text from old ps:\n")

            # --- New: print all old_mockup_chunks and ps_chunks with indices for debugging ---
            f.write("Old mock up chunks and their indices:\n")
            for omi, omc in enumerate(old_mockup_chunks):
                f.write(f"  [{omi}] {repr(omc.get('text', ''))}\n")
            f.write("PS Chunks and their indices:\n")
            for psi, psc in enumerate(ps_chunks):
                f.write(f"  [{psi}] {repr(psc.get('text', ''))}\n")
            # -------------------------------------------------------------------------------

            # Chunk size
            f.write(f"chunk size considered: {len(chunk['text'])}\n")
            # Embedding
            f.write(f"Embedding: {np.array2string(np.array(emb), precision=4, separator=', ') if emb is not None else 'N/A'}\n")
            # Mapping info
            if ps_idx is not None and ps_idx < len(ps_chunks):
                f.write(f"Mapped to Old PS Paragraph {ps_idx+1}\n")
            else:
                f.write("No mapping to Old PS found.\n")
        f.write("\n=== End of Old Mockup Log ===\n")
    return out_path

def write_new_mockup_log(
    new_mockup_chunks,
    new_mockup_embeddings,
    out_filename="new_mockup_chunks_log.txt"
):
    """
    Logs all chunks of New Mockup and their embeddings.

    Args:
        new_mockup_chunks (list): List of dicts, each chunk from New Mockup
        new_mockup_embeddings (list): List of vectors (np.ndarray or list), each embedding for new mockup chunk
        out_filename (str): Output log filename

    Returns: str (output path)
    """
    out_path = os.path.join(DATA_DIR, out_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("=== New Mockup Chunks and Embeddings ===\n")
        for idx, chunk in enumerate(new_mockup_chunks):
            emb = new_mockup_embeddings[idx] if idx < len(new_mockup_embeddings) else None
            f.write(f"\n--- New Mockup Chunk {idx+1} ---\n")
            f.write(f"Text: {chunk['text']}\n")
            f.write(f"Embedding: {np.array2string(np.array(emb), precision=4, separator=', ') if emb is not None else 'N/A'}\n")
        f.write("\n=== End of New Mockup Log ===\n")
    return out_path

# Example usage for demonstration (not called unless run directly)
if __name__ == "__main__":
    '''
    # Sample dummy data for demo/testing
    ps_chunks = [
        {"text": "Thank you for being a valued client."},
        {"text": "As we continue to build a lasting relationship"},
        {"text": " Important information about CIBC Service Commitment "},
    ]
    old_mockup_chunks = [
        {"text": "Thank you for being a valued client."},
        {"text": "As we continue to build a lasting relationship"},
        {"text": " Important information about CIBC Service Commitment "},
    ]
    old_mockup_embeddings = [
        [1234.0, 0.0], [5678.0, 0.0], [9101112.0, 0.0]
    ]
    chunk_map = {
        0: 0,
        1: 1,
        2: 2,
    }
    new_mockup_chunks = [
        {"text": "We strive to develop a lasting relationship"},
        {"text": "Thank you so much Amit fro being a CIBC customer."},
        {"text": " Pay attention to this information about CIBC Service Commitment "},
    ]
    new_mockup_embeddings = [
        [5678.0, 0.0], [1235.0, 0.0], [9101112.0, 0.0]
    ]
    '''
    write_old_mockup_log(old_mockup_chunks, old_mockup_embeddings, ps_chunks, chunk_map)
    write_new_mockup_log(new_mockup_chunks, new_mockup_embeddings)