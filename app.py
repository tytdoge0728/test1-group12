# app.py

from flask import Flask, render_template, request, redirect, url_for
from github_classroom_client import GitHubClassroomClient  # (make sure this file is in the same folder)
import os


# app.py
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env.py")  # This will parse your .env file and load variables into os.environ

token = os.getenv("GITHUB_ACCESS_TOKEN", "")
print(token)

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello! <a href='/classrooms'>View Classrooms</a>"

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

if __name__ == '__main__':
    app.run(debug=True)
