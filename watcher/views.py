import os
import requests
from django.shortcuts import render, redirect
from django.contrib import messages
from threading import Thread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

URL = "https://api.github.com/repos/{}/{}/stargazers?per_page=100&page={}"

CONFIG = []
notifications = [] 

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
    global CONFIG, notifications
    while True:
        for repo in CONFIG:
            username, reponame = repo['owner'], repo['repo']
            current_stargazers = fetch_stargazers(username, reponame)

            prev_users = repo.get('stargazers', [])
            traitors = set(prev_users).difference(current_stargazers)

            if traitors:
                notifications.append(f"Unstargazers detected in {username}/{reponame}: {', '.join(traitors)}. Email will be sent shortly.")
                send_email(traitors, username, reponame)

            repo['stargazers'] = current_stargazers

        time.sleep(60)

def start_watching():
    """Start the background thread to watch repositories."""
    thread = Thread(target=watch_repositories)
    thread.daemon = True
    thread.start()

def index(request):
    global CONFIG, notifications

    for repo in CONFIG:
        username, reponame = repo['owner'], repo['repo']
        repo['stargazer_count'] = len(fetch_stargazers(username, reponame))

    if request.method == "POST":
        repo_input = request.POST.get("repo")
        if repo_input:
            try:
                owner, repo = repo_input.split('/')
                data = {"owner": owner, "repo": repo, "stargazers": len(fetch_stargazers(owner, repo))}
                if data not in CONFIG:
                    CONFIG.append({"owner": owner, "repo": repo, "stargazers": fetch_stargazers(owner, repo)})
            except ValueError:
                notifications.append("Invalid input. Please use the format 'user/repo'.")
    
    context = {
        "repos": CONFIG,
        "notifications": notifications, 
    }

    notifications = []

    return render(request, 'index.html', context)


def remove_repo(request, index):
    global CONFIG
    del CONFIG[index]
    return redirect('index')

from django.urls import path

urlpatterns = [
    path('', index, name='index'),
    path('remove/<int:index>/', remove_repo, name='remove_repo'),
]
