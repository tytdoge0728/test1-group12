import os

class Config:
    # Database URL: e.g., 'sqlite:///data.db' or Postgres 'postgresql://user:pass@localhost/dbname'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # GitHub Personal Access Token or GitHub App token
    GITHUB_ACCESS_TOKEN = os.environ.get('GITHUB_ACCESS_TOKEN', '')
    
    # GitHub organization and assignment name (if relevant)
    GITHUB_ORG = os.environ.get('GITHUB_ORG', 'course-org')
    GITHUB_ASSIGNMENT_SLUG = os.environ.get('GITHUB_ASSIGNMENT_SLUG', 'my-assignment')
