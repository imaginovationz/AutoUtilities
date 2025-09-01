'''
Created on Aug 8, 2025

@author: ernig
'''
import json
import os
#from DocParser_Table import extract_all_tables_with_formatting
from DocParser import parse_docx
from ExtractRunPropertiesFromDOCxXML import rename_docx_to_zip, extract_text_properties
from TableNew import extract_all_tables_with_run_properties

# Path to your DOCX file
DOCX_FILE = '..//DocParser_AI//Files//PS00082.docx'

def main():
    if not os.path.exists(DOCX_FILE):
        print(f"File not found: {DOCX_FILE}")
        return

    final_output = {}

    # table extraction login in TableNew file
    
    print("Running table extraction from DocParser_Table.py...")
    #tables_json = extract_all_tables_with_formatting(DOCX_FILE)
    tables_json = extract_all_tables_with_run_properties(DOCX_FILE)
    
    final_output["tables"] = tables_json


    #  Run DocParser.py logic from doc x directly
    print("Running paragraph and table parsing from DocParser.py...")
    docparser_json = parse_docx(DOCX_FILE)
    final_output["docparser"] = docparser_json


    # 3️ -  Run ExtractRunPropertiesFromDOCxXML.py logic , ro extract from XML file of DOCX.
    # this can additionally extract data
         
    print("Running text properties extraction from ExtractRunPropertiesFromDOCxXML.py...")
    zip_file = rename_docx_to_zip(DOCX_FILE)
    text_props_json = extract_text_properties(zip_file)
    final_output["text_properties"] = text_props_json



    # 4️⃣ Merge and save final output
    output_file = os.path.splitext(DOCX_FILE)[0] + "_FINAL_OUTPUT.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Final merged JSON saved to: {output_file}")
    print(json.dumps(final_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
