import os
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
import json
from threading import Thread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables for Gmail configuration
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

URL = "https://api.github.com/repos/{}/{}/stargazers?per_page=100&page={}"

CONFIG_FILE = "watched_repos.json"

def load_config():
    """Load repo configurations from file."""
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return []

def save_config(watched_repos):
    """Save repo configurations to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(watched_repos, f)

def fetch_stargazers(username, reponame):
    """Fetch all the stargazers for a repository."""
    users = []
    cnt = 1
    stars = True

    while stars:
        url = URL.format(username, reponame, cnt)
        response = requests.get(url).json()
        if response and isinstance(response, list):
            for i in response:
                users.append(i["login"])
            cnt += 1
        else:
            stars = False

    return users

def send_email(traitors, username, reponame):
    """Send an email notification if traitors are found."""
    subject = f"Traitor Alert: {len(traitors)} unstargazers in {username}/{reponame}"
    body = f"The following users have unstared the repository {username}/{reponame}:\n" + "\n".join(traitors)

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_RECEIVER, text)
        server.quit()
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def watch_repositories():
    """Continuously watch for unstargazers every hour."""
    watched_repos = load_config()
    while True:
        for repo in watched_repos:
            username, reponame = repo['owner'], repo['repo']
            current_stargazers = fetch_stargazers(username, reponame)

            # Load previously saved stargazers for this repo
            prev_users = repo.get('stargazers', [])
            traitors = set(prev_users).difference(current_stargazers)

            if traitors:
                send_email(traitors, username, reponame)

            # Update the saved stargazers list
            repo['stargazers'] = current_stargazers

        # Save the updated configurations
        save_config(watched_repos)

        # Sleep for an hour
        time.sleep(3600)

def start_watching():
    """Start the background thread to watch repositories."""
    thread = Thread(target=watch_repositories)
    thread.daemon = True
    thread.start()

# View to handle the listing and adding/removing of repos
def index(request):
    watched_repos = load_config()
    if request.method == "POST":
        # Add a new repository
        repo_input = request.POST.get("repo")
        if repo_input:
            try:
                owner, repo = repo_input.split('/')
                watched_repos.append({"owner": owner, "repo": repo, "stargazers": fetch_stargazers(owner, repo)})
                save_config(watched_repos)
            except ValueError:
                return JsonResponse({"error": "Invalid input. Please use the format 'user/repo'."})

    return render(request, 'index.html', {"repos": watched_repos})

# View to remove a repository
def remove_repo(request, index):
    watched_repos = load_config()
    del watched_repos[index]
    save_config(watched_repos)
    return redirect('index')

# URL mapping
from django.urls import path

urlpatterns = [
    path('', index, name='index'),
    path('remove/<int:index>/', remove_repo, name='remove_repo'),
]
