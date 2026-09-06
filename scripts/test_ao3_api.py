#!/usr/bin/env python3
"""
Test script to verify AO3 credentials & reading history scraping locally.
Usage:
    python3 scripts/test_ao3_api.py
"""

import os
import sys
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

AO3_SESSION_COOKIE = os.environ.get("AO3_SESSION_COOKIE")
AO3_USERNAME = os.environ.get("AO3_USERNAME")
AO3_PASSWORD = os.environ.get("AO3_PASSWORD")

print("=" * 65)
print("🔍 AO3 Local Authentication & Reading History Scraper Tester")
print("=" * 65)

if not AO3_SESSION_COOKIE and not (AO3_USERNAME and AO3_PASSWORD):
    print("⚠️ Missing AO3 credentials in .env file.")
    print("👉 Please add AO3_SESSION_COOKIE or (AO3_USERNAME and AO3_PASSWORD) to hugo-blog/.env")
    sys.exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

if AO3_SESSION_COOKIE:
    print("🔑 Using AO3_SESSION_COOKIE from .env")
    session.cookies.set("_otwarchive_session", AO3_SESSION_COOKIE.strip(), domain="archiveofourown.org")
else:
    print(f"🔑 Logging in as {AO3_USERNAME} using username/password...")
    try:
        login_url = "https://archiveofourown.org/users/login"
        resp = session.get(login_url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        token_el = soup.find("input", {"name": "authenticity_token"})
        if not token_el:
            print("❌ Could not find authenticity_token on AO3 login page.")
            sys.exit(1)

        token = token_el["value"]
        payload = {
            "utf8": "✓",
            "authenticity_token": token,
            "user[login]": AO3_USERNAME,
            "user[password]": AO3_PASSWORD,
            "user[remember_me]": "1",
            "commit": "Log in",
        }
        post_resp = session.post(login_url, data=payload, timeout=20, allow_redirects=True)
        if "/users/logout" in post_resp.text.lower():
            print(f"✅ Logged in successfully as {AO3_USERNAME}!")
        else:
            print("❌ Login failed. Check username/password or IP rate limits.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Login error: {e}")
        sys.exit(1)

username = AO3_USERNAME or "me"
url = f"https://archiveofourown.org/users/{username}/readings"
print(f"📡 Fetching test reading history page: {url}")

try:
    resp = session.get(url, timeout=20)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        blurbs = soup.find_all("li", class_=lambda c: c and "blurb" in c.split())
        print(f"✅ HTTP 200 OK! Found {len(blurbs)} reading blurb(s) on page 1.")

        if blurbs:
            first_blurb = blurbs[0]
            heading = first_blurb.find("h4", class_="heading")
            if heading:
                title = heading.get_text(strip=True)
                print(f"   📖 Sample Work Title: \"{title}\"")
    else:
        print(f"⚠️ HTTP {resp.status_code} received when fetching readings page.")
except Exception as e:
    print(f"❌ Error testing readings page: {e}")

print("=" * 65)
