from extensions import db
from models import Repository, User, Commit
from github_classroom_client import fetch_repos_for_org, fetch_commits

def sync_repositories():
    """
    Example: fetch the repositories from GitHub and upsert them into the DB.
    """
    repos_data = fetch_repos_for_org()
    for r in repos_data:
        # If using requests approach, r is a dict
        # If using PyGithub, r is a Repo object
        github_id = r['id'] if isinstance(r, dict) else r.id
        name = r['name'] if isinstance(r, dict) else r.name
        html_url = r['html_url'] if isinstance(r, dict) else r.html_url
        
        existing_repo = Repository.query.filter_by(github_id=github_id).first()
        if not existing_repo:
            existing_repo = Repository(github_id=github_id, name=name, url=html_url)
            db.session.add(existing_repo)
        else:
            existing_repo.name = name
            existing_repo.url = html_url
    db.session.commit()


def sync_commits():
    """
    Iterate over known repositories in the DB, fetch commits from GitHub, and store them.
    """
    repos = Repository.query.all()
    for repo in repos:
        # parse owner/repo from the URL or from the name
        # e.g., 'https://github.com/org_name/repo_name' -> ('org_name', 'repo_name')
        # or store org_name separately.
        if "github.com/" in repo.url:
            _, owner, repo_name = repo.url.rsplit("github.com/", 1)[-1].split("/", 2)
        else:
            # fallback or parse differently
            continue
        
        commits_data = fetch_commits(owner, repo_name)
        for c in commits_data:
            # If using requests, c is a dict
            # If using PyGithub, c is a Commit object
            commit_sha = c['sha'] if isinstance(c, dict) else c.sha
            
            existing_commit = Commit.query.filter_by(commit_sha=commit_sha).first()
            if existing_commit:
                # Already in DB, skip or update as needed
                continue
            
            # Grab author info
            if isinstance(c, dict):
                author_data = c['commit']['author']
                username = c['author']['login'] if c.get('author') else 'unknown'
                message = c['commit']['message']
                # lines_added, lines_deleted might require separate "stats" call
            else:
                # PyGithub
                username = c.author.login if c.author else 'unknown'
                message = c.commit.message
                # c.stats.additions, c.stats.deletions (requires expansions)
            
            # Upsert user
            user = User.query.filter_by(github_username=username).first()
            if not user:
                user = User(github_username=username)
                db.session.add(user)
                db.session.flush()  # get user.id
            
            new_commit = Commit(
                commit_sha=commit_sha,
                repo_id=repo.id,
                user_id=user.id,
                # parse the commit timestamp
                timestamp=None,  # parse from c['commit']['author']['date'] if needed
                message=message
                # lines_added=..., lines_deleted=...
            )
            db.session.add(new_commit)
        db.session.commit()
