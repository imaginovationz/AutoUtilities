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

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def _qname(tag):
    return f"{{{NS['w']}}}{tag}"

def _get_attr(elem, attr_name):
    if elem is None:
        return None
    ns_key = f"{{{NS['w']}}}{attr_name}"
    return elem.attrib.get(ns_key) if ns_key in elem.attrib else elem.attrib.get(attr_name)

def _flag_from_elem(elem):
    if elem is None:
        return None
    val = _get_attr(elem, 'val')
    if val is None:
        return True
    v = str(val).strip().lower()
    if v in ('0', 'false', 'off', 'no', 'none'):
        return False
    return True

def _parse_rpr(rpr):
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
    bold = _flag_from_elem(rpr.find('w:b', NS))
    italic = _flag_from_elem(rpr.find('w:i', NS))
    strike = _flag_from_elem(rpr.find('w:strike', NS))
    u_elem = rpr.find('w:u', NS)
    if u_elem is None:
        underline = None
    else:
        uval = _get_attr(u_elem, 'val')
        underline = False if (uval and str(uval).strip().lower() == 'none') else True
    sz_elem = rpr.find('w:sz', NS)
    font_size_pt = None
    if sz_elem is not None:
        sz_val = _get_attr(sz_elem, 'val')
        if sz_val:
            try:
                font_size_pt = int(sz_val) / 2.0
            except Exception:
                font_size_pt = None
    rfonts = rpr.find('w:rFonts', NS)
    font_name = None
    if rfonts is not None:
        font_name = _get_attr(rfonts, 'ascii') or _get_attr(rfonts, 'hAnsi') or _get_attr(rfonts, 'cs')
    color_elem = rpr.find('w:color', NS)
    color = _get_attr(color_elem, 'val') if color_elem is not None else None
    highlight_elem = rpr.find('w:highlight', NS)
    highlight = _get_attr(highlight_elem, 'val') if highlight_elem is not None else None
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
    parts = []
    for t in r_elem.findall('w:t', NS):
        if t.text:
            parts.append(t.text)
    for instr in r_elem.findall('w:instrText', NS):
        if instr.text:
            parts.append(instr.text)
    return ''.join(parts)

def parse_paragraph(p_elem):
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
    if not runs:
        fallback_text = ''.join([t.text for t in p_elem.findall('.//w:t', NS) if t.text])
        if fallback_text:
            runs.append({"text": fallback_text})
    return {"paragraph_text": ''.join([r.get('text','') for r in runs]), "runs": runs, "alignment": alignment}

def parse_table(tbl_elem, table_counter):
    table_counter[0] += 1
    tbl_index = table_counter[0]
    rows = []
    for tr in tbl_elem.findall('w:tr', NS):
        cells = []
        for tc in tr.findall('w:tc', NS):
            cell_paragraphs = []
            nested_tables = []
            for child in list(tc):
                if child.tag == _qname('p'):
                    cell_paragraphs.append(parse_paragraph(child))
                elif child.tag == _qname('tbl'):
                    nested_tables.append(parse_table(child, table_counter))
            if not cell_paragraphs:
                for p in tc.findall('.//w:p', NS):
                    cell_paragraphs.append(parse_paragraph(p))
            cells.append({
                "paragraphs": cell_paragraphs,
                "nested_tables": nested_tables
            })
        rows.append(cells)
    return {"table_index": tbl_index, "rows": rows}

def extract_all_tables_with_run_properties(docx_path):
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
    for child in list(body):
        if child.tag == _qname('tbl'):
            tables.append(parse_table(child, table_counter))
    return tables

# Example usage and write JSON
if __name__ == "__main__":
    DOCX_FILE = '..//DocParser_AI//Files//PS00082.docx'
    try:
        result = extract_all_tables_with_run_properties(DOCX_FILE)
        out_file = os.path.splitext(DOCX_FILE)[0] + '_tables_runs.json'
        with open(out_file, 'w', encoding='utf-8') as jf:
            json.dump(result, jf, ensure_ascii=False, indent=2)
        print(f"Extracted {len(result)} top-level tables (nested tables included).")
        print(f"Output written to: {out_file}")
    except Exception as e:
        print("Error:", e)