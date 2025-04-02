import requests
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

class GitHubClassroomClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
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

    def get_commit_history(self, owner: str, repo: str, per_page=100):
        contributors_url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
        contributors_resp = requests.get(contributors_url, headers=self.headers)
        contributors_resp.raise_for_status()
        contributors = contributors_resp.json()

        timeline = defaultdict(lambda: defaultdict(int))  # 每人每天 commit 數
        detailed_commits = {}  # 每人 commit 明細

        for contributor in contributors:
            login = contributor.get("login")
            commit_url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits?author={login}&per_page={per_page}"
            commit_resp = requests.get(commit_url, headers=self.headers)

            if commit_resp.status_code != 200:
                print(f"Error fetching commits for {login}")
                continue

            commits = commit_resp.json()
            detailed_commits[login] = []

            for commit in commits:
                commit_info = commit.get("commit", {}).get("author", {})
                utc_date = commit_info.get("date", "")
                message = commit.get("commit", {}).get("message", "").strip()

                # skip if no valid date or message
                if not utc_date or not message:
                    continue

                # 轉為香港時間
                utc_time = datetime.strptime(utc_date, "%Y-%m-%dT%H:%M:%SZ")
                hkt_time = utc_time + timedelta(hours=8)
                date_str = hkt_time.strftime("%Y-%m-%d")

                # 填入 timeline + 詳細內容
                timeline[login][date_str] += 1
                detailed_commits[login].append({
                    "date": date_str,
                    "message": message
                })

            # Debug: 確認有抓到資料
            print(f"[DEBUG] {login} - commits: {len(detailed_commits[login])}")
            if detailed_commits[login]:
                print(f"Example message: {detailed_commits[login][0]['message']}")

        return {
            "timeline": {user: dict(days) for user, days in timeline.items()},
            "details": detailed_commits
        }