# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from github_classroom_client import GitHubClassroomClient  # (make sure this file is in the same folder)
import os
import openai
import requests
from dotenv import load_dotenv

# 讀取其他環境變數，例如 AI_MODEL_TOKEN，但 GitHub token 將從登入頁取得
load_dotenv(dotenv_path=".env")

AI_MODEL_TOKEN = os.getenv("AI_MODEL_TOKEN", "")
AI_ENDPOINT = "https://models.inference.ai.azure.com"
AI_MODEL_NAME = "gpt-4o"

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 請務必改成一個安全的隨機字串

# 登入頁面路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        token = request.form.get('github_token')
        if token:
            session['GITHUB_ACCESS_TOKEN'] = token
            return redirect(url_for('index'))
        else:
            error = "請輸入 GitHub Personal Access Token"
            return render_template('login.html', error=error)
    return render_template('login.html')


# 登出（選用，可清除 session）
@app.route('/logout')
def logout():
    session.pop('GITHUB_ACCESS_TOKEN', None)
    return redirect(url_for('login'))


# 每個需要 token 的路由都先從 session 讀取，如果沒有則導向登入頁
@app.route('/')
def index():
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
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
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    client = GitHubClassroomClient(token)
    classrooms = client.list_classrooms()
    return render_template("classrooms.html", classrooms=classrooms)


@app.route('/classroom/<int:classroom_id>/assignments')
def list_assignments(classroom_id):
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    client = GitHubClassroomClient(token)
    assignments = client.list_assignments(classroom_id)
    return render_template("assignments.html", classroom_id=classroom_id, assignments=assignments)


@app.route('/repo/<owner>/<repo>/contributors')
def show_contributors(owner, repo):
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
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

    team_slug = os.getenv("GITHUB_ASSIGNMENT_SLUG", "")
    ai_summary = ""
    return render_template("contributors.html",
                           contributors=contributors,
                           repo=f"{owner}/{repo}",
                           timeline=commit_data["timeline"],
                           commit_details=commit_data["details"],
                           contributor_stats=contributor_stats,
                           ai_summary=ai_summary,
                           team_slug=team_slug)


@app.route('/api/ai_summary/<owner>/<repo>')
def api_ai_summary(owner, repo):
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    client = GitHubClassroomClient(token)
    contributors = client.save_contributors_to_db(owner, repo)
    summary = get_ai_summary(contributors)
    return jsonify({"ai_summary": summary})


def get_ai_summary(contributors):
    """
    Convert contributors data to prompts and call the AI model to generate a summary in markdown format.
    """
    openai.api_key = AI_MODEL_TOKEN
    openai.api_base = AI_ENDPOINT

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
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    client = GitHubClassroomClient(token)
    result = client.detect_freeriders(org, team_slug, repo)

    print("👥 Team:", team_slug)
    print("📦 Repo:", repo)
    print("📊 Contributions:", result.get("contributions", {}))
    print("🔍 Freeriders:", result.get("freeriders", []))

    return jsonify(result)


@app.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/repos')
def list_assignment_repos(classroom_id, assignment_id):
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    client = GitHubClassroomClient(token)

    org_name = "your-org-name"  # ← 請改成你 GitHub Classroom 的 org 名稱
    all_repos = client.list_all_org_repos(org_name)

    assignments = client.list_assignments(classroom_id)
    assignment = next((a for a in assignments if a["id"] == assignment_id), None)
    if not assignment:
        return "Assignment not found", 404

    assignment_title = assignment["title"].lower().replace(" ", "")
    filtered_repos = [r for r in all_repos if assignment_title in r["name"].lower()]

    return render_template("repos.html", repos=filtered_repos)


@app.route('/api/save_feedback', methods=['POST'])
def api_save_feedback():
    data = request.get_json()
    repo = data.get("repo")
    content = data.get("content")

    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    try:
        client = GitHubClassroomClient(token)
        client.save_manual_feedback(repo, content)
        return jsonify({"success": True})
    except Exception as e:
        print("❌ Error saving feedback:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/feedback/<owner>/<repo>', methods=['GET'])
def api_get_feedback(owner, repo):
    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    client = GitHubClassroomClient(token)
    content = client.get_manual_feedback(f"{owner}/{repo}")
    return jsonify({"content": content})


@app.route('/api/delete_feedback', methods=['POST'])
def api_delete_feedback():
    data = request.get_json()
    repo = data.get("repo")

    token = session.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return redirect(url_for('login'))
    try:
        client = GitHubClassroomClient(token)
        client.delete_manual_feedback(repo)
        return jsonify({"success": True})
    except Exception as e:
        print("❌ Error deleting feedback:", e)
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
