"""
CustomDocxParser.py

Unified DOCX parser that extracts paragraphs, runs, tables, embedded objects, and detailed run/paragraph/cell formatting.
Composes functionality from:
 - DocParser.py: Paragraphs/headings/tables with rich formatting
 - TableNew.py: All tables (including nested), with run properties
 - ExtractRunPropertiesFromDOCxXML.py: Raw DOCX XML run/text properties
 - DocParserAI_Main.py: Orchestrates parsing and merging

Outputs a comprehensive JSON representation of all document elements, saved in 'ParsedJSON' folder.
"""

import os
import json
from datetime import datetime

from DocParser import parse_docx
from TableNew import extract_all_tables_with_run_properties
from ExtractRunPropertiesFromDOCxXML import rename_docx_to_zip, extract_text_properties

PARSED_JSON_DIR = os.path.join(os.path.dirname(__file__), "ParsedJSON")
os.makedirs(PARSED_JSON_DIR, exist_ok=True)

def annotate_section_path_and_idx(parsed_list):
    current_section = []
    para_counter = {}
    section_initialized = False
    for entry in parsed_list:
        style = entry.get('style', '')
        if style.replace(" ", "").lower().startswith("heading"):
            try:
                level = int(''.join(filter(str.isdigit, style)))
            except Exception:
                level = 1
            heading_text = entry.get('text', '').strip()
            current_section = current_section[:level-1] + [heading_text]
            section_initialized = True
        if not section_initialized:
            current_section = ["ROOT"]
        section_path = " > ".join([s for s in current_section if s])
        if entry['type'] in ('paragraph', 'heading'):
            if section_path not in para_counter:
                para_counter[section_path] = 0
            entry['section_path'] = section_path
            entry['para_idx'] = para_counter[section_path]
            para_counter[section_path] += 1
        else:
            entry['section_path'] = section_path
            entry['para_idx'] = None
    return parsed_list

def parse_docx_comprehensively(docx_path):
    """
    Parses a DOCX file using multiple strategies and merges results into a rich JSON structure.

    Args:
        docx_path (str): Path to .docx file.

    Returns:
        dict: Merged JSON structure with keys:
            - paragraphs_and_tables: Output from parse_docx (headings, paragraphs, tables, embedded files, with formatting)
            - tables_runs: Output from extract_all_tables_with_run_properties (all tables, nested, with run properties)
            - text_runs_properties: Output from extract_text_properties (raw XML, run/text properties)
            - parsed_at: ISO timestamp
            - source_file: Original input path
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"File not found: {docx_path}")

    print("[CustomDocxParser] Running DocParser.py logic...")
    paragraphs_and_tables = parse_docx(docx_path)
    paragraphs_and_tables = annotate_section_path_and_idx(paragraphs_and_tables)

    print("[CustomDocxParser] Running TableNew.py logic...")
    tables_runs = extract_all_tables_with_run_properties(docx_path)

    print("[CustomDocxParser] Running ExtractRunPropertiesFromDOCxXML.py logic...")
    zip_path = rename_docx_to_zip(docx_path)
    text_runs_properties = extract_text_properties(zip_path)

    parsed_json = {
        "parsed_at": datetime.utcnow().isoformat(),
        "source_file": docx_path,
        "paragraphs_and_tables": paragraphs_and_tables,
        "tables_runs": tables_runs,
        "text_runs_properties": text_runs_properties
    }

    base = os.path.splitext(os.path.basename(docx_path))[0]
    out_path = os.path.join(PARSED_JSON_DIR, f"{base}_PARSED.json")
    with open(out_path, "w", encoding="utf-8") as jf:
        json.dump(parsed_json, jf, ensure_ascii=False, indent=2)
    print(f"[CustomDocxParser] ✅ Parsed JSON saved to: {out_path}")

    return parsed_json

if __name__ == "__main__":
    pass