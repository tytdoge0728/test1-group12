# app.py

from flask import Flask, render_template, request, redirect, url_for
from github_classroom_client import GitHubClassroomClient  # (make sure this file is in the same folder)
import os
from dotenv import load_dotenv






if __name__ == '__main__':
    load_dotenv(dotenv_path=".env.py")
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    print("Token:", token)
    