'''
Created on Aug 4, 2025

@author: ernig
'''
import os
import zipfile
import xml.etree.ElementTree as ET
import json

def rename_docx_to_zip(docx_path):
    """
    Renames a .docx file to .zip and places it in the same directory.
    Returns the new zip file path.
    """
    base, ext = os.path.splitext(docx_path)
    if ext.lower() != ".docx":
        raise ValueError("Input file must be a .docx file")
    zip_path = base + ".zip"
    with open(docx_path, 'rb') as f_in, open(zip_path, 'wb') as f_out:
        f_out.write(f_in.read())
    return zip_path

def extract_text_properties(zip_path):
    """
    Reads document.xml from the zip, and for each <w:t> (text) tag,
    extracts its properties from the preceding <w:rPr> (run properties) tag.
    Returns a list of dictionaries for JSON output.
    """
    ns = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    }
    text_info_list = []

    with zipfile.ZipFile(zip_path) as zf:
        with zf.open('word/document.xml') as doc_xml:
            tree = ET.parse(doc_xml)
            root = tree.getroot()
            # Iterate through all runs <w:r>
            for run in root.iterfind('.//w:r', ns):
                rpr = run.find('w:rPr', ns)
                t = run.find('w:t', ns)
                if t is not None:
                    text = t.text
                    properties = []
                    if rpr is not None:
                        for elem in rpr:
                            tag = elem.tag
                            tag_clean = tag.split('}')[-1]
                            attrib = elem.attrib
                            if tag_clean == "b":
                                properties.append("Bold")
                            elif tag_clean == "bCs":
                                properties.append("Bold (Complex Script)")
                            elif tag_clean == "i":
                                properties.append("Italic")
                            elif tag_clean == "iCs":
                                properties.append("Italic (Complex Script)")
                            elif tag_clean == "highlight":
                                color = attrib.get('{%s}val' % ns['w'], attrib.get('val', ''))
                                properties.append(f"Highlight: {color}")
                            elif tag_clean == "u":
                                underline = attrib.get('{%s}val' % ns['w'], attrib.get('val', ''))
                                properties.append(f"Underline: {underline}")
                            elif tag_clean == "sz":
                                sz = attrib.get('{%s}val' % ns['w'], attrib.get('val', ''))
                                if sz:
                                    properties.append(f"Font Size: {int(sz)//2}pt")
                            elif tag_clean == "szCs":
                                szcs = attrib.get('{%s}val' % ns['w'], attrib.get('val', ''))
                                if szcs:
                                    properties.append(f"Font Size (Complex Script): {int(szcs)//2}pt")
                            else:
                                properties.append(f"{tag_clean}: {attrib}")
                    text_info_list.append({
                        "text": text,
                        "properties": properties if properties else None
                    })
    return text_info_list

if __name__ == "__main__":
    # Step 1: Rename .docx to .zip
    docx_file = '..//DocParser_AI//Files//PS00082.docx'
    #docx_file = "Timetable.docx"  # <-- Change this to your docx filename
    zip_file = rename_docx_to_zip(docx_file)
    print(f"Renamed {docx_file} to {zip_file}")

    # Step 2 and 3: Extract and store properties for each text
    text_properties = extract_text_properties(zip_file)

    # Output in JSON format
    json_filename = os.path.splitext(docx_file)[0] + "_text_properties.json"
    with open(json_filename, "w", encoding="utf-8") as jf:
        json.dump(text_properties, jf, ensure_ascii=False, indent=2)

    print(f"JSON output written to {json_filename}")