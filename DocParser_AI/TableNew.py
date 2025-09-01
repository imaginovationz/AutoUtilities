"""
docx_table_runs.py

Extracts ALL tables (including nested tables) from a .docx and captures
every run inside every paragraph of every cell, along with run properties
(bold/italic/underline/font/size/color/highlight/strike/style, etc.)
by parsing word/document.xml.

Dependencies:
 - None beyond Python stdlib (zipfile, xml.etree.ElementTree, json)
 - 'python-docx' is NOT required for XML parsing but can be used elsewhere.
"""

import zipfile
import xml.etree.ElementTree as ET
import json
import os

# Word ML namespace used throughout
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def _qname(tag):
    """Qualified name for comparing element.tag (e.g. 'tbl','tr','tc','p')"""
    return f"{{{NS['w']}}}{tag}"

def _get_attr(elem, attr_name):
    """Get attribute checking both namespaced and non-namespaced keys."""
    if elem is None:
        return None
    # namespaced attribute key like '{namespace}val'
    ns_key = f"{{{NS['w']}}}{attr_name}"
    return elem.attrib.get(ns_key) if ns_key in elem.attrib else elem.attrib.get(attr_name)

def _flag_from_elem(elem):
    """
    Interpret presence/value of an element (like <w:b w:val="true"/> or <w:b/>) as boolean.
    Returns True/False or None if elem is None.
    """
    if elem is None:
        return None
    val = _get_attr(elem, 'val')
    if val is None:
        # just presence means enabled
        return True
    v = str(val).strip().lower()
    if v in ('0', 'false', 'off', 'no', 'none'):
        return False
    return True

def _parse_rpr(rpr):
    """Parse <w:rPr> element and extract commonly used run properties."""
    if rpr is None:
        return {
            "bold": None,
            "italic": None,
            "underline": None,
            "strike": None,
            "font_name": None,
            "font_size_pt": None,
            "color": None,
            "highlight": None,
            "rStyle": None
        }

    # Bold / Italic / Strike
    bold = _flag_from_elem(rpr.find('w:b', NS))
    italic = _flag_from_elem(rpr.find('w:i', NS))
    strike = _flag_from_elem(rpr.find('w:strike', NS))

    # Underline - special: w:u val="none" => off
    u_elem = rpr.find('w:u', NS)
    if u_elem is None:
        underline = None
    else:
        uval = _get_attr(u_elem, 'val')
        underline = False if (uval and str(uval).strip().lower() == 'none') else True

    # Font size - <w:sz w:val="22"/> value is in half-points (so 22 => 11pt)
    sz_elem = rpr.find('w:sz', NS)
    font_size_pt = None
    if sz_elem is not None:
        sz_val = _get_attr(sz_elem, 'val')
        if sz_val:
            try:
                font_size_pt = int(sz_val) / 2.0
            except Exception:
                font_size_pt = None

    # Font name - <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
    rfonts = rpr.find('w:rFonts', NS)
    font_name = None
    if rfonts is not None:
        font_name = _get_attr(rfonts, 'ascii') or _get_attr(rfonts, 'hAnsi') or _get_attr(rfonts, 'cs')

    # Color - <w:color w:val="FF0000"/>
    color_elem = rpr.find('w:color', NS)
    color = _get_attr(color_elem, 'val') if color_elem is not None else None

    # Highlight - <w:highlight w:val="yellow"/>
    highlight_elem = rpr.find('w:highlight', NS)
    highlight = _get_attr(highlight_elem, 'val') if highlight_elem is not None else None

    # run style
    rstyle_elem = rpr.find('w:rStyle', NS)
    rstyle = _get_attr(rstyle_elem, 'val') if rstyle_elem is not None else None

    return {
        "bold": bold,
        "italic": italic,
        "underline": underline,
        "strike": strike,
        "font_name": font_name,
        "font_size_pt": font_size_pt,
        "color": color,
        "highlight": highlight,
        "rStyle": rstyle
    }

def _get_text_from_run(r_elem):
    """Concatenate all <w:t> children text for a run (handles xml:space)."""
    parts = []
    for t in r_elem.findall('w:t', NS):
        if t.text:
            parts.append(t.text)
    # also consider <w:instrText> (fields) if needed:
    for instr in r_elem.findall('w:instrText', NS):
        if instr.text:
            parts.append(instr.text)
    return ''.join(parts)

def parse_paragraph(p_elem):
    """Return paragraph dictionary with runs and paragraph-level properties (alignment)."""
    # paragraph alignment: <w:pPr><w:jc w:val="center"/>
    ppr = p_elem.find('w:pPr', NS)
    alignment = None
    if ppr is not None:
        jc = ppr.find('w:jc', NS)
        if jc is not None:
            alignment = _get_attr(jc, 'val')

    runs = []
    for r in p_elem.findall('w:r', NS):
        text = _get_text_from_run(r)
        rpr = r.find('w:rPr', NS)
        props = _parse_rpr(rpr)
        run_info = {
            "text": text,
            **props
        }
        runs.append(run_info)

    # If there are no <w:r> (sometimes in strange docs), try to capture direct text
    if not runs:
        # fallback: capture any text nodes under paragraph via w:t
        fallback_text = ''.join([t.text for t in p_elem.findall('.//w:t', NS) if t.text])
        if fallback_text:
            runs.append({"text": fallback_text})

    return {"paragraph_text": ''.join([r.get('text','') for r in runs]), "runs": runs, "alignment": alignment}

def parse_table(tbl_elem, table_counter):
    """
    Parse a <w:tbl> element into a nested structure (rows -> cells -> paragraphs -> runs).
    table_counter is a mutable list used to maintain sequential table indices across recursive calls.
    """
    table_counter[0] += 1
    tbl_index = table_counter[0]

    rows = []
    for tr in tbl_elem.findall('w:tr', NS):
        cells = []
        for tc in tr.findall('w:tc', NS):
            # iterate direct children of <w:tc> so nested tables are handled separately
            cell_paragraphs = []
            nested_tables = []
            for child in list(tc):
                if child.tag == _qname('p'):   # paragraph element
                    cell_paragraphs.append(parse_paragraph(child))
                elif child.tag == _qname('tbl'):  # nested table
                    nested_tables.append(parse_table(child, table_counter))
                else:
                    # ignore other tags (e.g., w:tcPr) or handle if needed
                    pass

            # If no direct paragraph children found, there may still be paragraphs nested deeper,
            # so as a fallback collect paragraphs under this tc (but avoid paragraphs inside nested tables)
            if not cell_paragraphs:
                # gather paragraphs that are descendants but make sure they are not inside nested tables
                for p in tc.findall('.//w:p', NS):
                    # determine if p is inside a nested table by scanning parents - skip if inside nested table
                    inside_nested_tbl = False
                    # walk up tree; ElementTree lacks parent pointer, so just check if any ancestor between tc and p is a tbl
                    # fallback: if p has an ancestor 'tbl' which is not the top-level tbl element - skip
                    # Simpler fallback: include it — many docs will have paragraphs directly
                    cell_paragraphs.append(parse_paragraph(p))

            cells.append({
                "paragraphs": cell_paragraphs,
                "nested_tables": nested_tables
            })
        rows.append(cells)

    return {"table_index": tbl_index, "rows": rows}

def extract_all_tables_with_run_properties(docx_path):
    """
    Main entrypoint. Returns list of tables (in document order),
    each table as dictionary produced by parse_table.
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"File not found: {docx_path}")

    with zipfile.ZipFile(docx_path, 'r') as zf:
        try:
            document_xml = zf.read('word/document.xml')
        except KeyError:
            raise ValueError("The .docx file does not contain word/document.xml")

    root = ET.fromstring(document_xml)
    body = root.find('w:body', NS)
    if body is None:
        return []

    tables = []
    table_counter = [0]

    # iterate direct children of body to preserve document order (only top-level tables here)
    for child in list(body):
        if child.tag == _qname('tbl'):
            tables.append(parse_table(child, table_counter))
        else:
            # skip paragraphs and other nodes; top-level tables only — nested tables handled inside parse_table
            pass

    return tables

# Example usage and write JSON
if __name__ == "__main__":
    # adjust path to your .docx
    DOCX_FILE = '..//DocParser_AI//Files//PS00082.docx'  # example path; change as needed

    try:
        result = extract_all_tables_with_run_properties(DOCX_FILE)
        out_file = os.path.splitext(DOCX_FILE)[0] + '_tables_runs.json'
        with open(out_file, 'w', encoding='utf-8') as jf:
            json.dump(result, jf, ensure_ascii=False, indent=2)
        print(f"Extracted {len(result)} top-level tables (nested tables included).")
        print(f"Output written to: {out_file}")
    except Exception as e:
        print("Error:", e)
