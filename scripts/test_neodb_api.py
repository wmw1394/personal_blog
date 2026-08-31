#!/usr/bin/env python3
"""
Test script to verify NeoDB API connectivity and response locally.
Usage:
    python3 scripts/test_neodb_api.py
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load local .env file
load_dotenv()

NEODB_TOKEN = os.environ.get("NEODB_TOKEN")

print("=" * 65)
print("🔍 NeoDB API Local Connectivity & Endpoint Tester")
print("=" * 65)

if not NEODB_TOKEN or NEODB_TOKEN == "YOUR_NEODB_TOKEN_HERE":
    print("❌ Error: NEODB_TOKEN is missing or set to placeholder in .env file.")
    print("👉 Please edit hugo-blog/.env and set your token from https://neodb.social/developer")
    sys.exit(1)

print(f"🔑 Using NEODB_TOKEN: {NEODB_TOKEN[:6]}...{NEODB_TOKEN[-4:] if len(NEODB_TOKEN) > 10 else ''}")

headers = {
    "Authorization": f"Bearer {NEODB_TOKEN}",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Test matrix: categories and shelf types
categories = ["book", "movie", "tv", "music", "game", "podcast"]
shelf_types = ["complete", "wishlist", "progress", "dropped"]

success_count = 0

print("\n📡 Testing NeoDB API Endpoints:")
print("   URL Format: https://neodb.social/api/me/shelf/all?category={category}&type={type}")

for category in categories:
    for shelf_type in shelf_types:
        url = f"https://neodb.social/api/me/shelf/all?category={category}&type={shelf_type}&page=1"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            
            # Alternative query param fallback if type is shelf_type
            if resp.status_code != 200:
                alt_url = f"https://neodb.social/api/me/shelf/{shelf_type}?category={category}&page=1"
                resp = requests.get(alt_url, headers=headers, timeout=15)
                url = alt_url

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                total_pages = data.get("pages", 1)
                count = len(items)
                success_count += 1
                print(f"   ✅ [HTTP 200] category={category:<8} type={shelf_type:<10} => {count} item(s) (pages: {total_pages})")
                
                if items and success_count == 1:
                    sample = items[0]
                    item_info = sample.get("item", {})
                    title = item_info.get("title") or sample.get("title") or "Untitled"
                    print(f"      📖 Sample Item: \"{title}\"")
            else:
                print(f"   ⚠️ [HTTP {resp.status_code}] category={category:<8} type={shelf_type:<10}")

        except Exception as err:
            print(f"   ❌ Network error for category={category} type={shelf_type}: {err}")

print("\n" + "=" * 65)
if success_count > 0:
    print(f"🎉 API test completed successfully ({success_count} endpoint combinations returned HTTP 200).")
    print("👉 You can now run python3 scripts/sync_neodb.py to populate data/neodb/*.yaml")
else:
    print("⚠️ API test completed but no endpoints returned 200 OK.")
    print("👉 Please check your NEODB_TOKEN at https://neodb.social/developer")
print("=" * 65)
