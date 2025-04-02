from datetime import datetime
from extensions import db

class Repository(db.Model):
    __tablename__ = 'repositories'
    
    id = db.Column(db.Integer, primary_key=True)
    github_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(255))
    url = db.Column(db.String(255))
    team_name = db.Column(db.String(255))  # or assignment_name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to commits, issues, etc.
    commits = db.relationship('Commit', backref='repository', lazy=True)
    # issues = db.relationship('Issue', backref='repository', lazy=True)
    # pull_requests = db.relationship('PullRequest', backref='repository', lazy=True)
    
    
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    github_username = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(255), nullable=True)

    # Relationship to commits, issues, etc.
    commits = db.relationship('Commit', backref='author', lazy=True)
    # issues = db.relationship('Issue', backref='creator', lazy=True)


class Commit(db.Model):
    __tablename__ = 'commits'
    
    id = db.Column(db.Integer, primary_key=True)
    commit_sha = db.Column(db.String(255), unique=True)
    repo_id = db.Column(db.Integer, db.ForeignKey('repositories.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    lines_added = db.Column(db.Integer, default=0)
    lines_deleted = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)

# Similarly, define Issue, PullRequest, Comment, etc. as needed.
