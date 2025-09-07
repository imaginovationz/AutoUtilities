import os

PARSED_OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "ParsedOut")
os.makedirs(PARSED_OUT_DIR, exist_ok=True)

def save_chunks_info(doc_id, matches, status_updates):
    """
    Saves chunk information and status updates to a TXT file in data/ParsedOut.
    Now logs, for each chunk:
      - requirement_chunk (new mockup)
      - matched_old_mockup_chunk (bridge)
      - matched_ps_chunk (anchor in PS)
      - mockup_similarity (new→old)
      - ps_similarity (old→ps)
      - anchor_section_path, anchor_para_idx, anchor_docx_idx
      - action_taken
    Args:
        doc_id (str): Document identifier (used for file naming).
        matches (List[dict]): List of dicts with chunk merge info.
        status_updates (List[str]): Status log strings for the process.
    Returns:
        out_path (str): Path to saved TXT file.
    """
    out_name = f"{doc_id}_parsedout.txt"
    out_path = os.path.join(PARSED_OUT_DIR, out_name)

    high_score_chunks = []

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("=== Status Log ===\n")
        for status in status_updates:
            f.write(status + "\n")
        f.write("\n=== Chunks Information ===\n")
        for idx, m in enumerate(matches):
            req = m.get("requirement_chunk", "").strip()
            old_mock = m.get("matched_old_mockup_chunk", "").strip()
            ps = m.get("matched_ps_chunk", "").strip()
            mockup_sim = m.get("mockup_similarity", None)
            ps_sim = m.get("ps_similarity", None)
            anchor_section_path = m.get("anchor_section_path", "")
            anchor_para_idx = m.get("anchor_para_idx", "")
            anchor_docx_idx = m.get("anchor_docx_idx", "")
            action_taken = m.get("action_taken", "")
            mockup_sim_s = f"{(mockup_sim if mockup_sim is not None else 0.0):.4f}"
            ps_sim_s = f"{(ps_sim if ps_sim is not None else 0.0):.4f}"
            chunk_info = (
                f"\n---- Chunk {idx+1} ----\n"
                f"Requirement Chunk:\n{req}\n\n"
                f"Matched Old Mockup Chunk:\n{old_mock}\n\n"
                f"Matched PS Chunk:\n{ps}\n\n"
                f"Similarity (New→Old): {mockup_sim_s}\n"
                f"Similarity (Old→PS): {ps_sim_s}\n"
                f"Anchor Location: section_path='{anchor_section_path}', para_idx={anchor_para_idx}, docx_idx={anchor_docx_idx}\n"
                f"Action Taken: {action_taken}\n"
            )
            f.write(chunk_info)
            try:
                score = float(ps_sim) if ps_sim is not None else 0.0
            except Exception:
                score = 0.0
            percentage = score * 100
            if percentage > 70.0:
                high_score_chunks.append(f"Chunk {idx+1} - Similarity: {percentage:.1f}%")

        f.write("\n=== Chunks with Similarity Score > 70% (Old→PS) ===\n")
        if high_score_chunks:
            for line in high_score_chunks:
                f.write(line + "\n")
        else:
            f.write("None\n")

    return out_path