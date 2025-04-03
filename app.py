# app.py
# try handling for loading .env file
from flask import Flask, render_template, request, redirect, url_for, jsonify
from github_classroom_client import GitHubClassroomClient  # (make sure this file is in the same folder)
import os
import openai
import requests

#test for git command
# app.py
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")  # This will parse your .env file and load variables into os.environ

token = os.getenv("GITHUB_ACCESS_TOKEN", "")
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN", "")

# Getting GitHub access tokens (for contributor data) and AI model tokens
AI_MODEL_TOKEN = os.getenv("AI_MODEL_TOKEN", "")
# AI Model Setup
AI_ENDPOINT = "https://models.inference.ai.azure.com"
AI_MODEL_NAME = "gpt-4o"
print(token)

app = Flask(__name__)

@app.route('/')
def index():
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)
    org_name = "tytdoge0728"  # <--- 替換為你的 GitHub org 名稱

    all_data = []
    all_users_set = set()
    total_commit_count = 0

    try:
        classrooms = client.list_classrooms()
        all_repos = client.list_all_org_repos(org_name)

        for classroom in classrooms:
            class_dict = {
                "id": classroom["id"],
                "name": classroom["name"],
                "assignments": []
            }

            assignments = client.list_assignments(classroom["id"])
            for assignment in assignments:
                assignment_title = assignment["title"].lower().replace(" ", "")
                matching_repos = [
                    r for r in all_repos if assignment_title in r["name"].lower()
                ]

                for repo in matching_repos:
                    # ⬇️ 呼叫 get_commit_history，並計算 user + commit 數
                    try:
                        history = client.get_commit_history(repo["owner"]["login"], repo["name"])
                        contributors = history.get("details", {})
                        for user, commits in contributors.items():
                            all_users_set.add(user)
                            total_commit_count += len(commits)
                    except Exception as e:
                        print(f"[WARN] Cannot fetch commits for {repo['name']}: {e}")

                class_dict["assignments"].append({
                    "id": assignment["id"],
                    "title": assignment["title"],
                    "repos": matching_repos
                })

            all_data.append(class_dict)

    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] {e}")

    return render_template("index.html",
        total_repos=sum(len(a["repos"]) for c in all_data for a in c["assignments"]),
        total_users=len(all_users_set),
        total_commits=total_commit_count,
        all_data=all_data)



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

@app.route('/repo/<owner>/<repo>/contributors')
def show_contributors(owner, repo):
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)
    contributors = client.save_contributors_to_db(owner, repo)
    commit_data = client.get_commit_history(owner, repo)

    contributor_stats = {}
    for user, commits in commit_data["details"].items():
        contributor_stats[user] = {
            "commits": len(commits),
            "additions": sum(c.get("additions", 0) for c in commits),
            "deletions": sum(c.get("deletions", 0) for c in commits),
        }

    ai_summary = ""
    team_slug = os.getenv("GITHUB_ASSIGNMENT_SLUG", "")

    return render_template(
        "contributors.html",
        contributors=contributors,
        repo=f"{owner}/{repo}",
        timeline=commit_data["timeline"],
        commit_details=commit_data["details"],
        contributor_stats=contributor_stats,
        ai_summary=ai_summary,
        team_slug=team_slug
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


@app.route('/api/ai_summary/<owner>/<repo>')
def api_ai_summary(owner, repo):
    client = GitHubClassroomClient(GITHUB_ACCESS_TOKEN)
    contributors = client.save_contributors_to_db(owner, repo)
    summary = get_ai_summary(contributors)
    return jsonify({"ai_summary": summary})


def get_ai_summary(contributors):
    """
    Convert contributors data to prompts and call the AI ​​model to generate a summary in markdown format.
    """
    # Set openai client parameters
    openai.api_key = AI_MODEL_TOKEN
    openai.api_base = AI_ENDPOINT

    # Construct prompt, you can use Chinese prompt here.
    prompt = (
    "Please generate a concise and insightful summary based on the following contributor data, "
    "entirely in valid Markdown syntax. **Do not** wrap your response in triple backticks or code blocks. "
    "Use headings, bullet points, bold, italics, etc. to structure your Markdown.\n"
    )
    for user in contributors:
        prompt += f"{user['login']} - {user['contributions']} Submissions。\n"
    prompt += "\nPlease provide only the Markdown content (no code fences)."

    try:
        response = openai.ChatCompletion.create(
            model=AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,
            top_p=1.0,
            max_tokens=1000,
        )
        summary = response.choices[0].message.content.strip()
    except Exception as e:
        summary = "AI 總結生成失敗。"
        print("Error generating AI summary:", e)
    return summary

@app.route('/freeriders/<org>/<team_slug>/<repo>')
def detect_freeriders(org, team_slug, repo):
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)
    result = client.detect_freeriders(org, team_slug, repo)

    # Debug logs
    print("👥 Team:", team_slug)
    print("📦 Repo:", repo)
    print("📊 Contributions:", result.get("contributions", {}))
    print("🔍 Freeriders:", result.get("freeriders", []))

    return jsonify(result)

@app.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/repos')
def list_assignment_repos(classroom_id, assignment_id):
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    client = GitHubClassroomClient(token)

    org_name = "your-org-name"  # ← ← ← 這邊請改成你 GitHub Classroom 的 org 名稱
    all_repos = client.list_all_org_repos(org_name)

    # 拿 assignment 的資訊來比對（例如名稱是 "assignment1"）
    assignments = client.list_assignments(classroom_id)
    assignment = next((a for a in assignments if a["id"] == assignment_id), None)
    if not assignment:
        return "Assignment not found", 404

    assignment_title = assignment["title"].lower().replace(" ", "")
    filtered_repos = [r for r in all_repos if assignment_title in r["name"].lower()]

    return render_template("repos.html", repos=filtered_repos)


if __name__ == '__main__':
    app.run(debug=True)
