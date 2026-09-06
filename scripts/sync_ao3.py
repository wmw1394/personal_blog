#!/usr/bin/env python3
"""
Sync AO3 reading history data to local Hugo YAML cache (data/ao3/{year}.yaml).
Supports authentication via AO3_SESSION_COOKIE or AO3_USERNAME + AO3_PASSWORD.
"""

import os
import re
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup
import yaml
from dotenv import load_dotenv

# Load local .env file if present
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Environment variables
AO3_SESSION_COOKIE = os.environ.get("AO3_SESSION_COOKIE")
AO3_USERNAME = os.environ.get("AO3_USERNAME")
AO3_PASSWORD = os.environ.get("AO3_PASSWORD")
AO3_MAX_PAGES = int(os.environ.get("AO3_MAX_PAGES", "10"))

AO3_BASE_URL = "https://archiveofourown.org"


def parse_ao3_date(date_str: str) -> str:
    """Parse AO3 date string like '06 Sep 2026' into 'YYYY-MM-DD'."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    date_str = date_str.strip()
    try:
        dt = datetime.strptime(date_str, "%d %b %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d")


def create_ao3_session() -> Optional[requests.Session]:
    """Create an authenticated requests Session for AO3."""
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
        logging.info("Using AO3_SESSION_COOKIE for authentication.")
        session.cookies.set("_otwarchive_session", AO3_SESSION_COOKIE.strip(), domain="archiveofourown.org")
        return session

    if AO3_USERNAME and AO3_PASSWORD:
        logging.info(f"Attempting password login for AO3 user: {AO3_USERNAME}")
        try:
            login_url = f"{AO3_BASE_URL}/users/login"
            resp = session.get(login_url, timeout=15)
            if resp.status_code != 200:
                logging.error(f"Failed to fetch login page: HTTP {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            token_el = soup.find("input", {"name": "authenticity_token"})
            if not token_el:
                logging.error("Could not find authenticity_token on AO3 login page.")
                return None

            token = token_el.get("value", "")
            payload = {
                "utf8": "✓",
                "authenticity_token": token,
                "user[login]": AO3_USERNAME.strip(),
                "user[password]": AO3_PASSWORD.strip(),
                "user[remember_me]": "1",
                "commit": "Log in",
            }

            post_resp = session.post(login_url, data=payload, timeout=20, allow_redirects=True)
            if "/users/logout" in post_resp.text.lower() or post_resp.status_code == 200:
                logging.info(f"Successfully logged in as {AO3_USERNAME}")
                return session
            else:
                logging.error("AO3 login failed. Check username/password or IP rate limits.")
                return None
        except Exception as e:
            logging.error(f"Error during AO3 login: {e}")
            return None

    logging.error("No AO3_SESSION_COOKIE or (AO3_USERNAME & AO3_PASSWORD) supplied.")
    return None


def parse_blurb(blurb) -> Optional[Dict[str, Any]]:
    """Parse a single AO3 work blurb element into a dictionary."""
    classes = blurb.get("class", [])
    if "deleted" in classes:
        # Handle deleted work blurb
        viewed_heading = blurb.find("h4", class_="viewed")
        viewed_text = viewed_heading.get_text(strip=True) if viewed_heading else ""
        
        visited_count = 1
        count_match = re.search(r"Visited (\d+) time", viewed_text, re.I)
        if count_match:
            visited_count = int(count_match.group(1))

        last_visited = ""
        date_match = re.search(r"Last visited:\s*(\d{2}\s+[A-Za-z]{3}\s+\d{4})", viewed_text)
        if date_match:
            last_visited = parse_ao3_date(date_match.group(1))
        else:
            last_visited = datetime.now().strftime("%Y-%m-%d")

        # Try to find deleted work ID if present
        work_id = ""
        id_match = re.search(r"work-(\d+)", " ".join(classes))
        if id_match:
            work_id = id_match.group(1)
        else:
            work_id = f"deleted_{int(datetime.now().timestamp())}"

        return {
            "work_id": str(work_id),
            "title": "Deleted Work",
            "authors": ["Unknown"],
            "fandoms": ["Deleted Work"],
            "rating": "Not Rated",
            "warnings": [],
            "categories": [],
            "relationships": [],
            "characters": [],
            "freeforms": [],
            "summary": "This work has been deleted from Archive of Our Own.",
            "words": 0,
            "chapters": "N/A",
            "is_complete": True,
            "visited_count": visited_count,
            "last_visited_date": last_visited,
            "created_time": f"{last_visited}T00:00:00Z",
            "url": f"{AO3_BASE_URL}/works/{work_id}" if not work_id.startswith("deleted_") else f"{AO3_BASE_URL}/",
            "is_deleted": True,
        }

    # Standard work blurb
    heading = blurb.find("h4", class_="heading")
    if not heading:
        return None

    title_a = heading.find("a", href=re.compile(r"^/works/\d+"))
    if not title_a:
        return None

    title = title_a.get_text(strip=True)
    href = title_a.get("href", "")
    work_id_match = re.search(r"/works/(\d+)", href)
    if not work_id_match:
        return None
    work_id = work_id_match.group(1)

    # Authors
    authors = [a.get_text(strip=True) for a in heading.find_all("a", rel="author")]
    if not authors:
        authors = ["Anonymous"]

    # Fandoms
    fandoms_h5 = blurb.find("h5", class_="fandoms")
    fandoms = [a.get_text(strip=True) for a in fandoms_h5.find_all("a", class_="tag")] if fandoms_h5 else []

    # Required tags (Rating, Warnings, Category)
    rating = "Not Rated"
    rating_span = blurb.find("span", class_=re.compile(r"rating-"))
    if rating_span:
        rating_classes = rating_span.get("class", [])
        for c in rating_classes:
            if c == "rating-explicit":
                rating = "Explicit"
            elif c == "rating-mature":
                rating = "Mature"
            elif c == "rating-teen":
                rating = "Teen And Up Audiences"
            elif c == "rating-general-audience":
                rating = "General Audiences"
            elif c == "rating-notrated":
                rating = "Not Rated"

    warnings = [a.get_text(strip=True) for a in blurb.select("ul.required-tags li:nth-of-type(2) a.tag")]
    categories = [a.get_text(strip=True) for a in blurb.select("ul.required-tags li:nth-of-type(3) a.tag")]

    # Tags
    relationships = [a.get_text(strip=True) for a in blurb.select("li.relationships a.tag")]
    characters = [a.get_text(strip=True) for a in blurb.select("li.characters a.tag")]
    freeforms = [a.get_text(strip=True) for a in blurb.select("li.freeforms a.tag")]

    # Summary
    summary_box = blurb.find("blockquote", class_="userstuff")
    summary = summary_box.get_text(separator="\n", strip=True) if summary_box else ""

    # Stats
    words = 0
    words_dd = blurb.find("dd", class_="words")
    if words_dd:
        try:
            words = int(words_dd.get_text(strip=True).replace(",", ""))
        except ValueError:
            words = 0

    chapters = "1/1"
    chapters_dd = blurb.find("dd", class_="chapters")
    if chapters_dd:
        chapters = chapters_dd.get_text(strip=True)

    is_complete = True
    if "/" in chapters:
        ch_parts = chapters.split("/")
        if len(ch_parts) == 2 and ch_parts[0] != ch_parts[1]:
            is_complete = False

    # Viewed reading history
    viewed_div = blurb.find("h4", class_="viewed") or blurb.find("div", class_="viewed")
    viewed_text = viewed_div.get_text(strip=True) if viewed_div else ""

    visited_count = 1
    if "visited once" in viewed_text.lower():
        visited_count = 1
    else:
        v_match = re.search(r"Visited (\d+) time", viewed_text, re.I)
        if v_match:
            visited_count = int(v_match.group(1))

    last_visited = datetime.now().strftime("%Y-%m-%d")
    date_match = re.search(r"Last visited:\s*(\d{2}\s+[A-Za-z]{3}\s+\d{4})", viewed_text)
    if date_match:
        last_visited = parse_ao3_date(date_match.group(1))

    return {
        "work_id": str(work_id),
        "title": title,
        "authors": authors,
        "fandoms": fandoms,
        "rating": rating,
        "warnings": warnings,
        "categories": categories,
        "relationships": relationships,
        "characters": characters,
        "freeforms": freeforms,
        "summary": summary,
        "words": words,
        "chapters": chapters,
        "is_complete": is_complete,
        "visited_count": visited_count,
        "last_visited_date": last_visited,
        "created_time": f"{last_visited}T00:00:00Z",
        "url": f"{AO3_BASE_URL}/works/{work_id}",
        "is_deleted": False,
    }


def fetch_reading_history(session: requests.Session, username: str, max_pages: int = 10) -> List[Dict[str, Any]]:
    """Fetch reading history items for given user up to max_pages."""
    all_items = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = f"{AO3_BASE_URL}/users/{username}/readings?page={page}"
        logging.info(f"Fetching AO3 readings page {page}: {url}")

        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                logging.warning(f"Failed to fetch page {page}: HTTP {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            blurbs = soup.find_all("li", class_=re.compile(r"\bblurb\b"))

            if not blurbs:
                logging.info(f"No more reading entries found on page {page}.")
                break

            page_item_count = 0
            for blurb in blurbs:
                item = parse_blurb(blurb)
                if item and item["work_id"] not in seen_ids:
                    seen_ids.add(item["work_id"])
                    all_items.append(item)
                    page_item_count += 1

            logging.info(f"Extracted {page_item_count} items from page {page}.")

            # Check pagination end
            next_link = soup.find("li", class_="next")
            if not next_link or "disabled" in next_link.get("class", []):
                logging.info("Reached last page of reading history.")
                break

        except Exception as e:
            logging.warning(f"Error scraping AO3 readings page {page}: {e}")
            break

    return all_items


def save_items_to_yaml(items: List[Dict[str, Any]], data_dir: str = "data/ao3") -> None:
    """Group items by year and merge into data/ao3/{year}.yaml."""
    os.makedirs(data_dir, exist_ok=True)
    items_by_year: Dict[str, List[Dict[str, Any]]] = {}

    for item in items:
        year_str = item["last_visited_date"][:4] if item.get("last_visited_date") else str(datetime.now().year)
        items_by_year.setdefault(year_str, []).append(item)

    for year, new_items in items_by_year.items():
        file_path = os.path.join(data_dir, f"{year}.yaml")
        existing_items = []

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_items = yaml.safe_load(f) or []
            except Exception as e:
                logging.warning(f"Could not load existing {file_path}: {e}")
                existing_items = []

        # Index existing items by work_id
        item_map: Dict[str, Dict[str, Any]] = {str(item["work_id"]): item for item in existing_items if "work_id" in item}

        for new_item in new_items:
            wid = str(new_item["work_id"])
            if wid in item_map:
                # Idempotently update missing or updated fields, preserving custom user notes
                curr = item_map[wid]
                for key, val in new_item.items():
                    if key not in curr or (curr[key] is None or curr[key] == ""):
                        curr[key] = val
                    elif key in ["visited_count", "last_visited_date", "words", "chapters", "is_complete"]:
                        curr[key] = val
            else:
                item_map[wid] = new_item

        final_list = list(item_map.values())
        # Sort by last_visited_date descending
        final_list.sort(key=lambda x: x.get("last_visited_date", ""), reverse=True)

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(final_list, f, allow_unicode=True, sort_keys=False)

        logging.info(f"Saved {len(final_list)} AO3 entries to {file_path}")


def main():
    session = create_ao3_session()
    if not session:
        logging.error("Authentication failed. Cannot sync AO3 reading history.")
        sys.exit(1)

    username = AO3_USERNAME
    if not username:
        # Infer username from session profile page
        try:
            profile_resp = session.get(f"{AO3_BASE_URL}/", timeout=15)
            soup = BeautifulSoup(profile_resp.text, "html.parser")
            user_link = soup.find("a", href=re.compile(r"^/users/[^/]+/profile"))
            if user_link:
                u_match = re.search(r"/users/([^/]+)/profile", user_link["href"])
                if u_match:
                    username = u_match.group(1)
        except Exception:
            pass

    if not username:
        logging.error("Could not determine AO3 username. Please set AO3_USERNAME environment variable.")
        sys.exit(1)

    logging.info(f"Starting AO3 reading history sync for username: {username} (max_pages={AO3_MAX_PAGES})")
    items = fetch_reading_history(session, username, max_pages=AO3_MAX_PAGES)

    if items:
        save_items_to_yaml(items)
        logging.info(f"AO3 sync finished successfully! Synced {len(items)} works.")
    else:
        logging.warning("No items scraped from AO3 reading history.")


if __name__ == "__main__":
    main()
