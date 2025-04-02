import requests
import sqlite3

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

    def get_contributors(self, owner, repo):
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

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
