import os
import uuid
from utils import update_latest_ids
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from utils import UPLOAD_DIR, UPDATED_DIR, new_id
from docparser_langchain import (
    create_vectorstore,
    find_best_old_mockup_for_new_mockup,
    find_best_ps_for_old_mockup,
)
from updater import update_ps_document_closest
import traceback
from docparser_langchain import log_chunk_embeddings_and_mappings

app = Flask(__name__)
CORS(app)

# In-memory dict (for demo; use Redis or DB for prod)
progress_dict = {}

def set_progress(job_id, value, status):
    progress_dict[job_id] = {'progress': value, 'status': status}

@app.route("/upload_ps", methods=["POST"])
def upload_ps():
    status_updates = []
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        f = request.files["file"]
        doc_id = new_id("ps")
        filename = f"{doc_id}.docx"
        path = os.path.join(UPLOAD_DIR, filename)
        f.save(path)
        status_updates.append(f"File saved for PS upload: {path}")
        update_latest_ids(ps_doc_id=doc_id)
        
        # Parse and vectorize - will auto-save parsed JSON to proper folder
        result = create_vectorstore(doc_id, path, status_updates)
        status_updates.extend(result.get("status_updates", []))

        parsed_json_folder = os.path.join(os.path.dirname(__file__), "DocParser", "ParsedJSON")
        parsed_json_file = os.path.join(parsed_json_folder, f"{doc_id}_PARSED.json")

        return jsonify({
            "doc_id": doc_id,
            "filename": filename,
            "parsed_json_path": parsed_json_file,
            "status_updates": status_updates
        })
    except Exception as e:
        error_msg = f"Error in upload_ps: {str(e)}"
        tb = traceback.format_exc()
        status_updates.append(error_msg)
        status_updates.append("Traceback:")
        for line in tb.splitlines():
            status_updates.append(line)
        print(error_msg)
        print(tb)
        return jsonify({"error": error_msg, "status_updates": status_updates}), 500

@app.route("/upload_old_mock", methods=["POST"])
def upload_old_mock():
    status_updates = []
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        f = request.files["file"]
        doc_id = new_id("mock_old")
        filename = f"{doc_id}.docx"
        path = os.path.join(UPLOAD_DIR, filename)
        f.save(path)
        status_updates.append("File saved for old mockup upload.")
       
        update_latest_ids(old_mockup_id=doc_id)
       
        result = create_vectorstore(doc_id, path, status_updates)
        status_updates.extend(result.get("status_updates", []))
        return jsonify({"doc_id": doc_id, "filename": filename, "status_updates": status_updates})
    except Exception as e:
        error_msg = f"Error in upload_old_mock: {str(e)}"
        tb = traceback.format_exc()
        status_updates.append(error_msg)
        status_updates.append("Traceback:")
        for line in tb.splitlines():
            status_updates.append(line)
        print(error_msg)
        print(tb)
        return jsonify({"error": error_msg, "status_updates": status_updates}), 500

@app.route("/upload_new_mock", methods=["POST"])
def upload_new_mock():
    status_updates = []
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        f = request.files["file"]
        doc_id = new_id("mock_new")
        filename = f"{doc_id}.docx"
        path = os.path.join(UPLOAD_DIR, filename)
        f.save(path)
        update_latest_ids(new_mockup_id=doc_id)
        
        status_updates.append("File saved for new mockup upload.")
        result = create_vectorstore(doc_id, path, status_updates)
        status_updates.extend(result.get("status_updates", []))
        return jsonify({"doc_id": doc_id, "filename": filename, "status_updates": status_updates})
    except Exception as e:
        error_msg = f"Error in upload_new_mock: {str(e)}"
        tb = traceback.format_exc()
        status_updates.append(error_msg)
        status_updates.append("Traceback:")
        for line in tb.splitlines():
            status_updates.append(line)
        print(error_msg)
        print(tb)
        return jsonify({"error": error_msg, "status_updates": status_updates}), 500

@app.route("/generate_new_ps", methods=["POST"])
@app.route("/generate_new_ps", methods=["POST"])
def generate_new_ps():
    status_updates = []
    job_id = str(uuid.uuid4())
    try:
        set_progress(job_id, 0, "Starting...")
        data = request.get_json()
        ps_doc_id = data.get("ps_doc_id")
        old_mock_id = data.get("old_mock_id")
        new_mock_id = data.get("new_mock_id")
        similarity_threshold = data.get("similarity_threshold", 0.0)

        if not ps_doc_id or not old_mock_id or not new_mock_id:
            set_progress(job_id, 100, "Failed: Missing IDs")
            return jsonify({"error": "ps_doc_id, old_mock_id, new_mock_id required", "status_updates": status_updates, "job_id": job_id}), 400

        set_progress(job_id, 10, "Finding best matches: new mockup to old mockup...")
        status_updates.append("Finding best matches: new mockup to old mockup.")
        new2old_mockup_matches, log1 = find_best_old_mockup_for_new_mockup(new_mock_id, old_mock_id)
        status_updates.extend(log1)
        set_progress(job_id, 30, "Finding best matches: old mockup to PS...")
        status_updates.append("Finding best matches: old mockup to PS.")
        oldmock2ps_matches, log2 = find_best_ps_for_old_mockup(old_mock_id, ps_doc_id)
        status_updates.extend(log2)

        # === INSERT LOGGING HERE ===
        log_chunk_embeddings_and_mappings(old_mock_id, new_mock_id, ps_doc_id)
        # ===========================

        ps_filename = f"{ps_doc_id}.docx"
        ps_path = os.path.join(UPLOAD_DIR, ps_filename)

        status_updates.append(f"Generating new PS document using new mockup and mapping via old mockup.")
        updated_path, update_status = update_ps_document_closest(
            ps_path,
            new2old_mockup_matches,
            oldmock2ps_matches,
            similarity_threshold=similarity_threshold,
            job_id=job_id,
            set_progress=set_progress
        )
        status_updates.extend(update_status)

        out_filename = os.path.basename(updated_path)
        set_progress(job_id, 100, "Generation complete. Ready for download.")
        status_updates.append("Generation complete. Ready for download.")
        return jsonify({"updated_file": out_filename, "status_updates": status_updates, "job_id": job_id})
    except Exception as e:
        error_msg = f"Error in generate_new_ps: {str(e)}"
        tb = traceback.format_exc()
        status_updates.append(error_msg)
        status_updates.append("Traceback:")
        for line in tb.splitlines():
            status_updates.append(line)
        set_progress(job_id, 100, "Error: " + error_msg)
        print(error_msg)
        print(tb)
        return jsonify({"error": error_msg, "status_updates": status_updates, "job_id": job_id}), 500

@app.route("/progress/<job_id>")
def get_progress(job_id):
    return jsonify(progress_dict.get(job_id, {'progress': 0, 'status': "Not started"}))

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(UPDATED_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False)