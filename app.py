# app.py
# try handling for loading .env file
from flask import Flask, render_template, request, redirect, url_for, jsonify
from github_classroom_client import GitHubClassroomClient  # (make sure this file is in the same folder)
import os

#test for git command
# app.py
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")  # This will parse your .env file and load variables into os.environ

token = os.getenv("GITHUB_ACCESS_TOKEN", "")
print(token)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/classrooms')
def list_classrooms():
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)
    classrooms = client.list_classrooms()
    return render_template("classrooms.html", classrooms=classrooms)

@app.route('/classroom/<int:classroom_id>/assignments')
def list_assignments(classroom_id):
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)
    assignments = client.list_assignments(classroom_id)
    return render_template("assignments.html", classroom_id=classroom_id, assignments=assignments)

@app.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/repos')
def list_assignment_repos(classroom_id, assignment_id):
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)
    repos = client.list_assignment_repos(classroom_id, assignment_id)
    return render_template("repos.html", repos=repos)

@app.route('/repo/<owner>/<repo>/contributors')
def show_contributors(owner, repo):
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)

    contributors = client.save_contributors_to_db(owner, repo)
    commit_data = client.get_commit_history(owner, repo)

    return render_template(
        "contributors.html",
        contributors=contributors,
        repo=f"{owner}/{repo}",
        timeline=commit_data["timeline"],
        commit_details=commit_data["details"]
    )

# @app.route("/api/contributions")
# def get_contributions():
#     data = {
#         "labels": ["2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28", "2025-03-29", "2025-03-30", "2025-03-31"],
#         "members": {
#             "Anson": [2, 1, 3, 5, 4, 1, 9],
#             "Yu Sang": [3, 2, 0, 6, 7, 9, 3],
#             "Tsz To": [1, 0, 2, 1, 0, 2, 3],
#             "Yuk Yu": [0, 1, 1, 0, 2, 1, 2]
#         }
#     }
#     return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
