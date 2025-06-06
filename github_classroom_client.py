import requests
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

class GitHubClassroomClient:
    BASE_URL = "https://api.github.com"
    

    def __init__(self, token: str):
        self.token = token
        self.api_url = "https://api.github.com"  
        self.init_feedback_table()
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MyGitHubClassroomApp/1.0"
        }
        
    def list_classrooms(self):
        url = f"{self.BASE_URL}/classrooms"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def list_assignments(self, classroom_id: int):
        url = f"{self.BASE_URL}/classrooms/{classroom_id}/assignments"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def list_assignment_repos(self, classroom_id: int, assignment_id: int):
        url = f"{self.BASE_URL}/classrooms/{classroom_id}/assignments/{assignment_id}/repos"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def get_contributors(self, owner: str, repo: str):
        contributors_url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
        contributors_resp = requests.get(contributors_url, headers=self.headers)
        contributors_resp.raise_for_status()

        contributors = contributors_resp.json()
        result = []

        for contributor in contributors:
            login = contributor.get("login")
            commit_url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits?author={login}&per_page=100"
            commit_resp = requests.get(commit_url, headers=self.headers)
            if commit_resp.status_code != 200:
                print(f"Error fetching commits for {login}")
                continue
            commit_data = commit_resp.json()

            result.append({
                "login": login,
                "avatar_url": contributor.get("avatar_url"),
                "html_url": contributor.get("html_url"),
                "contributions": contributor.get("contributions"),
                "commits": [{
                    "date": c["commit"]["author"]["date"],
                    "message": c["commit"]["message"]
                } for c in commit_data]
            })

        return result

    def save_contributors_to_db(self, owner: str, repo: str):
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            print(f"Error fetching contributors: {response.status_code} {response.text}")
            return []

        contributors = response.json()

        conn = sqlite3.connect("github_users.db")
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contributors (
                id INTEGER PRIMARY KEY,
                login TEXT,
                avatar_url TEXT,
                html_url TEXT,
                contributions INTEGER,
                repo TEXT
            )
        ''')

        for user in contributors:
            cursor.execute('''
                INSERT OR REPLACE INTO contributors (id, login, avatar_url, html_url, contributions, repo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user["id"],
                user["login"],
                user["avatar_url"],
                user["html_url"],
                user["contributions"],
                f"{owner}/{repo}"
            ))

        conn.commit()
        conn.close()

        return contributors

    def get_commit_history(self, owner, repo):
        timeline = {}
        details = {}
        url = f"{self.api_url}/repos/{owner}/{repo}/commits"
        headers = {"Authorization": f"Bearer {self.token}"}

        r = requests.get(url, headers=headers)
        r.raise_for_status()
        commits = r.json()

        for commit in commits:
            author = commit.get("author", {}).get("login")
            if not author:
                continue

            # commit date
            date = commit["commit"]["author"]["date"][:10]
            timeline.setdefault(author, {})
            timeline[author][date] = timeline[author].get(date, 0) + 1

            # additions & deletions
            sha = commit["sha"]
            commit_detail_url = f"{self.api_url}/repos/{owner}/{repo}/commits/{sha}"
            rd = requests.get(commit_detail_url, headers=headers)
            rd.raise_for_status()
            commit_data = rd.json()

            additions = commit_data.get("stats", {}).get("additions", 0)
            deletions = commit_data.get("stats", {}).get("deletions", 0)
            message = commit_data.get("commit", {}).get("message", "")

            details.setdefault(author, []).append({
                "date": date,
                "message": message,
                "additions": additions,
                "deletions": deletions
            })

        return {"timeline": timeline, "details": details}

    def list_all_org_repos(self, org_name):
        repos = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/orgs/{org_name}/repos?per_page=100&page={page}"
            resp = requests.get(url, headers=self.headers)
            if resp.status_code != 200:
                print(f"[ERROR] Cannot fetch repos for org {org_name}: {resp.text}")
                break
            batch = resp.json()
            if not batch:
                break
            repos.extend(batch)
            page += 1
        return repos
    def init_feedback_table(self):
        conn = sqlite3.connect("github_users.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT UNIQUE,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def save_manual_feedback(self, repo: str, content: str):
        conn = sqlite3.connect("github_users.db")
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO feedback (repo, content)
            VALUES (?, ?)
        ''', (repo, content))

        conn.commit()
        conn.close()
    def get_manual_feedback(self, repo: str):
        conn = sqlite3.connect("github_users.db")
        cursor = conn.cursor()
        cursor.execute('SELECT content FROM feedback WHERE repo = ?', (repo,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""

    def delete_manual_feedback(self, repo: str):
        conn = sqlite3.connect("github_users.db")
        cursor = conn.cursor()
        cursor.execute('DELETE FROM feedback WHERE repo = ?', (repo,))
        conn.commit()
        conn.close()
        
    def detect_freeriders(self, org, team_slug, repo):
        # Step 1: Get commit history
        commits = self.get_commit_history(org, repo)
        contributions = {user: len(logs) for user, logs in commits["details"].items()}

        # Step 2: 動態計算平均門檻
        if not contributions:
            return {"freeriders": [], "contributions": {}}

        values = list(contributions.values())
        average = sum(values) / len(values)

        # Step 3: 設定自由騎士門檻（例如低於 30% 平均）
        threshold = average * 0.3

        freeriders = [user for user, count in contributions.items() if count < threshold]

        return {
            "freeriders": freeriders,
            "contributions": contributions
        }
#ver2 
    # def detect_freeriders(self, org, team_slug, repo):
    #     # 1. Get team members
    #     team_url = f"{self.api_url}/orgs/{org}/teams/{team_slug}/members"
    #     team_resp = requests.get(team_url, headers=self.headers)
    #     team_resp.raise_for_status()
    #     team_members = [m["login"] for m in team_resp.json()]
    #     print("🎯 Team Members:", team_members)

    #     # 2. Get repo events (public activity)
    #     events_url = f"{self.api_url}/repos/{org}/{repo}/events"
    #     events_resp = requests.get(events_url, headers=self.headers)
    #     events_resp.raise_for_status()
    #     events = events_resp.json()

    #     # 3. Count events per user (only team members)
    #     contributions = {member: 0 for member in team_members}
    #     for event in events:
    #         actor = event.get("actor", {}).get("login")
    #         if actor in contributions:
    #             contributions[actor] += 1

    #     # 4. Threshold 判斷
    #     THRESHOLD = 5
    #     freeriders = [user for user, count in contributions.items() if count < THRESHOLD]

    #     print("📊 Contributions:", contributions)
    #     print("🔍 Freeriders:", freeriders)

    #     return {
    #         "freeriders": freeriders,
    #         "contributions": contributions,
    #         "threshold": THRESHOLD
    #     }

##ver3
    # def detect_freeriders(self, org: str, team_slug: str, repo: str):
    #     # 用 repo 中每個人 commit 數做分析
    #     history = self.get_commit_history(org, repo)
    #     contributions = {user: sum(commits[date] for date in commits) for user, commits in history["timeline"].items()}

    #     if not contributions:
    #         return {"freeriders": [], "contributions": {}}

    #     avg = sum(contributions.values()) / len(contributions)
    #     threshold = max(1, avg * 0.3)  # 根據 PDF 建議，小於平均值的 30% 算 freerider

    #     freeriders = [user for user, count in contributions.items() if count < threshold]

    #     return {
    #         "freeriders": freeriders,
    #         "contributions": contributions
    #     }