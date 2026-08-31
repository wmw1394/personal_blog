#!/usr/bin/env python3
"""
Sync NeoDB shelf data to local Hugo YAML cache and upload covers to Cloudflare R2.
"""

import os
import re
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Environment variables
NEODB_TOKEN = os.environ.get("NEODB_TOKEN")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.environ.get("R2_BUCKET")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_DOMAIN = os.environ.get("R2_DOMAIN")

NEODB_API_BASE = "https://neodb.social/api"
SHELF_TYPES = ["complete", "wishlist", "progress", "dropped"]

# Optional boto3 client for Cloudflare R2
s3_client = None
if R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET and R2_ACCOUNT_ID:
    try:
        import boto3
        from botocore.exceptions import ClientError

        r2_endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        logging.info("Cloudflare R2 client initialized successfully.")
    except Exception as e:
        logging.warning(f"Failed to initialize boto3 R2 client: {e}")


def get_image_ext(url: str, content_type: Optional[str]) -> str:
    """Determine image file extension from content-type or URL."""
    if content_type:
        if "png" in content_type:
            return ".png"
        elif "gif" in content_type:
            return ".gif"
        elif "webp" in content_type:
            return ".webp"
        elif "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
    
    clean_url = url.split("?")[0]
    for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        if clean_url.lower().endswith(ext):
            return ext
    return ".jpg"


def upload_cover_to_r2(item_uuid: str, original_url: str) -> str:
    """
    Download cover image from NeoDB and upload to Cloudflare R2 idempotently.
    Returns the public R2 cover URL if successful, otherwise returns original_url.
    """
    if not s3_client or not R2_BUCKET or not original_url:
        return original_url

    try:
        # Fetch original cover image
        resp = requests.get(original_url, timeout=15)
        if resp.status_code != 200:
            logging.warning(f"Failed to download image from {original_url}: HTTP {resp.status_code}")
            return original_url

        content_type = resp.headers.get("Content-Type", "")
        ext = get_image_ext(original_url, content_type)
        r2_key = f"neodb/covers/{item_uuid}{ext}"

        # Check if object already exists in R2 for idempotency
        try:
            s3_client.head_object(Bucket=R2_BUCKET, Key=r2_key)
            logging.info(f"Cover already exists in R2: {r2_key}")
        except ClientError as e:
            # 404 means object does not exist, so we upload
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["404", "NoSuchKey", "NotFound"]:
                s3_client.put_object(
                    Bucket=R2_BUCKET,
                    Key=r2_key,
                    Body=resp.content,
                    ContentType=content_type or "image/jpeg",
                )
                logging.info(f"Uploaded cover to R2: {r2_key}")
            else:
                logging.warning(f"R2 head_object error for {r2_key}: {e}")
                return original_url

        # Format public URL
        domain = (R2_DOMAIN or "").strip().rstrip("/")
        if domain:
            if not domain.startswith("http://") and not domain.startswith("https://"):
                domain = f"https://{domain}"
            return f"{domain}/{r2_key}"
        return original_url

    except Exception as e:
        logging.warning(f"Error processing R2 cover upload for {item_uuid}: {e}")
        return original_url


def fetch_shelf_data(shelf_type: str, token: str) -> List[Dict[str, Any]]:
    """Fetch all pages for a given shelf status from NeoDB API."""
    items = []
    page = 1
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "Hugo-NeoDB-Sync/1.0"}

    while True:
        url = f"{NEODB_API_BASE}/me/shelf/{shelf_type}?page={page}"
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                logging.warning(f"Failed fetching {shelf_type} page {page}: HTTP {resp.status_code}")
                break

            data = resp.json()
            page_data = data.get("data", [])
            if not page_data:
                break

            items.extend(page_data)

            total_pages = data.get("pages", 1)
            if page >= total_pages:
                break
            page += 1

        except Exception as e:
            logging.warning(f"Exception fetching {shelf_type} page {page}: {e}")
            break

    logging.info(f"Fetched {len(items)} items from shelf '{shelf_type}'.")
    return items


def parse_year(created_time_str: Optional[str]) -> str:
    """Extract 4-digit year from created_time string, defaulting to current year."""
    if created_time_str:
        match = re.search(r"\b(20\d{2})\b", str(created_time_str))
        if match:
            return match.group(1)
    return str(datetime.now().year)


def process_items(raw_items_by_shelf: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Process and deduplicate raw API shelf items.
    Returns dictionary mapping year -> { uuid -> item_dict }.
    """
    # Map by year -> uuid -> item_dict
    grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for shelf_type, items in raw_items_by_shelf.items():
        for raw in items:
            try:
                item_info = raw.get("item", {})
                uuid = item_info.get("uuid") or raw.get("uuid")
                if not uuid:
                    continue

                title = item_info.get("title") or ""
                category = item_info.get("category") or ""
                cover_url = item_info.get("cover_image_url") or item_info.get("cover_url") or ""
                created_time = raw.get("created_time") or raw.get("created_at") or ""
                comment_text = raw.get("comment_text") or raw.get("body") or ""

                # Upload cover to Cloudflare R2 if available
                if cover_url:
                    cover_url = upload_cover_to_r2(uuid, cover_url)

                year = parse_year(created_time)

                if year not in grouped:
                    grouped[year] = {}

                # Build standardized item schema
                item_entry = {
                    "uuid": uuid,
                    "title": title,
                    "category": category,
                    "cover_url": cover_url,
                    "created_time": created_time,
                    "shelf_type": shelf_type,
                    "comment_text": comment_text,
                }

                # Keep first occurrence or deduplicate by uuid
                if uuid not in grouped[year]:
                    grouped[year][uuid] = item_entry

            except Exception as e:
                logging.warning(f"Error processing single item: {e}")
                continue

    return grouped


def merge_and_save(grouped_new_data: Dict[str, Dict[str, Dict[str, Any]]], data_dir: str):
    """
    Merge fetched data with local data/neodb/{year}.yaml files.
    Preserves existing title, cover_url, comment_text if present locally.
    """
    os.makedirs(data_dir, exist_ok=True)

    for year, new_uuid_map in grouped_new_data.items():
        yaml_path = os.path.join(data_dir, f"{year}.yaml")
        existing_items: List[Dict[str, Any]] = []

        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, list):
                        existing_items = loaded
            except Exception as e:
                logging.warning(f"Error reading existing YAML {yaml_path}: {e}")

        # Build map of existing items by uuid
        existing_map: Dict[str, Dict[str, Any]] = {}
        for item in existing_items:
            if isinstance(item, dict) and "uuid" in item:
                existing_map[item["uuid"]] = item

        # Merge strategy:
        # Match existing entries by uuid. Fill missing fields only.
        # NEVER overwrite existing title, cover_url, comment_text if present!
        merged_list: List[Dict[str, Any]] = []

        for uuid, new_item in new_uuid_map.items():
            if uuid in existing_map:
                loc_item = existing_map[uuid]
                merged = {
                    "uuid": uuid,
                    "title": loc_item.get("title") or new_item.get("title") or "",
                    "category": loc_item.get("category") or new_item.get("category") or "",
                    "cover_url": loc_item.get("cover_url") or new_item.get("cover_url") or "",
                    "created_time": loc_item.get("created_time") or new_item.get("created_time") or "",
                    "shelf_type": loc_item.get("shelf_type") or new_item.get("shelf_type") or "",
                    "comment_text": loc_item.get("comment_text") or new_item.get("comment_text") or "",
                }
                merged_list.append(merged)
                del existing_map[uuid]
            else:
                merged_list.append(new_item)

        # Retain any remaining existing items not returned by API
        for remaining_item in existing_map.values():
            merged_list.append(remaining_item)

        # Sort items by created_time descending
        merged_list.sort(key=lambda x: str(x.get("created_time", "")), reverse=True)

        # Save back to YAML
        try:
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(merged_list, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            logging.info(f"Updated {yaml_path} with {len(merged_list)} items.")
        except Exception as e:
            logging.warning(f"Failed saving {yaml_path}: {e}")


def main():
    if not NEODB_TOKEN:
        logging.warning("NEODB_TOKEN environment variable is not set. Skipping NeoDB sync.")
        return

    logging.info("Starting NeoDB shelf synchronization...")
    raw_data_by_shelf: Dict[str, List[Dict[str, Any]]] = {}

    for shelf_type in SHELF_TYPES:
        raw_data_by_shelf[shelf_type] = fetch_shelf_data(shelf_type, NEODB_TOKEN)

    grouped_data = process_items(raw_data_by_shelf)

    # Base directory for YAML cache
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, "data", "neodb")

    merge_and_save(grouped_data, data_dir)
    logging.info("NeoDB sync completed successfully.")


if __name__ == "__main__":
    main()
