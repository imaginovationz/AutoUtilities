from flask import Flask, request, jsonify, send_from_directory
import requests
import re
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return send_from_directory(os.getcwd(), "index.html")


@app.route("/api/git-structure", methods=["POST"])
def find_git_structure():
    git_url = request.json.get("git_url")

    pattern = r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(/(.*))?"
    match = re.match(pattern, git_url)

    owner, repo, branch, path = match.group(1), match.group(2), match.group(3), match.group(5) or ""

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    response = requests.get(api_url)

    folder_count = sum(1 for item in response.json() if item["type"] == "dir")

    return jsonify({"folder_count": folder_count})


if __name__ == "__main__":
    app.run(debug=True)
