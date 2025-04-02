# github_classroom_client.py
import requests

class GitHubClassroomClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
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
