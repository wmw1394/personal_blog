#!/usr/bin/env python3
"""
Test script to verify NeoDB API connectivity, token validity, and endpoint response locally.
Usage:
    python3 scripts/test_neodb_api.py
"""

import os
import sys
import json
import requests

# Try loading python-dotenv if available, or fall back to manual .env parser
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Lightweight fallback .env loader
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("'\"")

NEODB_TOKEN = os.environ.get("NEODB_TOKEN")

print("=" * 60)
print("🔍 NeoDB API Local Connectivity & Endpoint Tester")
print("=" * 60)

if not NEODB_TOKEN or NEODB_TOKEN == "YOUR_NEODB_TOKEN_HERE":
    print("❌ Error: NEODB_TOKEN is missing or not configured in .env file.")
    print("👉 Please edit hugo-blog/.env and set your actual token from https://neodb.social/developer")
    sys.exit(1)

print(f"🔑 Using NEODB_TOKEN: {NEODB_TOKEN[:6]}...{NEODB_TOKEN[-4:] if len(NEODB_TOKEN) > 10 else ''}")

# Headers to test
headers = {
    "Authorization": f"Bearer {NEODB_TOKEN}",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Endpoints to test
test_endpoints = [
    ("Standard Endpoint", "https://neodb.social/api/me/shelf/complete?page=1"),
    ("Trailing Slash Endpoint", "https://neodb.social/api/me/shelf/complete/?page=1"),
    ("All Shelf Endpoint", "https://neodb.social/api/me/shelf/all?page=1"),
]

success = False

for label, url in test_endpoints:
    print(f"\n📡 Testing [{label}]: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        print(f"   Status Code: HTTP {resp.status_code}")

        if resp.status_code == 200:
            success = True
            try:
                data = resp.json()
                items = data.get("data", [])
                total_pages = data.get("pages", 1)
                count = len(items)
                print(f"   ✅ SUCCESS! Retrieved {count} item(s) on page 1 (Total pages: {total_pages})")
                
                if items:
                    sample = items[0]
                    item_info = sample.get("item", {})
                    title = item_info.get("title") or sample.get("title") or "Unknown Title"
                    category = item_info.get("category") or sample.get("category") or "Unknown Category"
                    print(f"   📖 Sample Item: \"{title}\" (Category: {category})")
                break
            except Exception as json_err:
                print(f"   ⚠️ Could not parse JSON response: {json_err}")
                print(f"   Raw output snippet: {resp.text[:200]}")
        else:
            print(f"   ❌ HTTP {resp.status_code} Response text snippet: {resp.text[:150]}")

    except Exception as err:
        print(f"   ❌ Network error calling {url}: {err}")

print("\n" + "=" * 60)
if success:
    print("🎉 NeoDB API test PASSED! You can now run python3 scripts/sync_neodb.py")
else:
    print("⚠️ NeoDB API test FAILED for all tested endpoints.")
    print("👉 Recommendations:")
    print("   1. Verify your NEODB_TOKEN is valid at https://neodb.social/developer")
    print("   2. Check if your NeoDB account has at least 1 item on your shelf.")
print("=" * 60)
