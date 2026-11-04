import argparse
from datetime import datetime, time
import glob
import json
import os
import re
import sqlite3
import sys

COREDATA_EPOCH = datetime(2001, 1, 1).timestamp()
CONTAINER_DIR = os.path.expanduser(
    "~/Library/Containers/com.apple.iBooksX/Data/Documents"
)


def find_db(subfolder: str, prefix: str) -> str:
  search_dir = os.path.join(CONTAINER_DIR, subfolder)
  matches = glob.glob(os.path.join(search_dir, f"{prefix}*.sqlite"))
  valid = [f for f in matches if not f.endswith(("-wal", "-shm"))]
  if not valid:
    sys.exit(
        f"Error: Could not locate {prefix} database in {search_dir}.\n"
        "Ensure Apple Books has run on this Mac and Terminal has Full Disk"
        " Access."
    )
  return valid[0]


def coredata_to_datetime(val: float | None) -> datetime | None:
  if val is not None:
    return datetime.fromtimestamp(COREDATA_EPOCH + val)
  return None


def sanitize_filename(name: str) -> str:
  return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def parse_args():
  parser = argparse.ArgumentParser(
      description="Export Apple Books reading activity and highlights."
  )
  parser.add_argument(
      "--start-date",
      type=str,
      default=None,
      help="Start date in YYYY-MM-DD format (defaults to start of today).",
  )
  parser.add_argument(
      "--end-date",
      type=str,
      default=None,
      help="End date in YYYY-MM-DD format (defaults to end of today).",
  )
  parser.add_argument(
      "--output-dir",
      type=str,
      default="./ibooks_export",
      help="Directory to save JSON and Markdown output (default: ./ibooks_export).",
  )
  return parser.parse_args()


def main():
  args = parse_args()
  today = datetime.now().date()

  # Determine start and end timestamps
  if args.start_date:
    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
  else:
    start_dt = datetime.combine(today, time.min)

  if args.end_date:
    end_dt = datetime.combine(
        datetime.strptime(args.end_date, "%Y-%m-%d").date(), time.max
    )
  else:
    end_dt = datetime.combine(today, time.max)

  start_cd = start_dt.timestamp() - COREDATA_EPOCH
  end_cd = end_dt.timestamp() - COREDATA_EPOCH

  os.makedirs(args.output_dir, exist_ok=True)
  md_notes_dir = os.path.join(args.output_dir, "notes")
  os.makedirs(md_notes_dir, exist_ok=True)

  lib_db = find_db("BKLibrary", "BKLibrary")
  notes_db = find_db("AEAnnotation", "AEAnnotation")

  # 1. Fetch library books
  books_catalog = {}
  recent_reading = []

  with sqlite3.connect(f"file:{lib_db}?mode=ro", uri=True) as conn:
    cursor = conn.cursor()
    cursor.execute("""
            SELECT 
                ZASSETID, 
                ZTITLE, 
                ZAUTHOR, 
                ZREADINGPROGRESS, 
                ZLASTOPENDATE 
            FROM ZBKLIBRARYASSET 
            WHERE ZTITLE IS NOT NULL
        """)
    for row in cursor.fetchall():
      asset_id, title, author, progress, last_open = row
      open_dt = coredata_to_datetime(last_open)

      books_catalog[asset_id] = {
          "title": title,
          "author": author or "Unknown",
          "progress_percent": round((progress or 0.0) * 100, 2),
          "last_opened": open_dt.isoformat() if open_dt else None,
      }

      if last_open and (start_cd <= last_open <= end_cd):
        recent_reading.append({
            "asset_id": asset_id,
            "title": title,
            "author": author or "Unknown",
            "progress_percent": round((progress or 0.0) * 100, 2),
            "last_opened": open_dt.isoformat(),
        })

  # 2. Fetch highlights & annotations within range
  annotations_by_book = {}

  with sqlite3.connect(f"file:{notes_db}?mode=ro", uri=True) as conn:
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT 
                ZANNOTATIONASSETID,
                ZANNOTATIONSELECTEDTEXT,
                ZANNOTATIONNOTE,
                ZANNOTATIONCREATIONDATE,
                ZANNOTATIONMODIFICATIONDATE,
                ZANNOTATIONSTYLE
            FROM ZAEANNOTATION
            WHERE ZANNOTATIONDELETED = 0
              AND (
                  (ZANNOTATIONCREATIONDATE BETWEEN ? AND ?) 
                  OR (ZANNOTATIONMODIFICATIONDATE BETWEEN ? AND ?)
              )
              AND (ZANNOTATIONSELECTEDTEXT IS NOT NULL OR ZANNOTATIONNOTE IS NOT NULL)
            ORDER BY ZANNOTATIONCREATIONDATE ASC
        """,
        (start_cd, end_cd, start_cd, end_cd),
    )

    for row in cursor.fetchall():
      asset_id, text, note, created, modified, style = row
      meta = books_catalog.get(
          asset_id, {"title": "Unknown Title", "author": "Unknown"}
      )
      title = meta["title"]

      if title not in annotations_by_book:
        annotations_by_book[title] = {
            "author": meta["author"],
            "asset_id": asset_id,
            "annotations": [],
        }

      created_dt = coredata_to_datetime(created)
      modified_dt = coredata_to_datetime(modified)

      annotations_by_book[title]["annotations"].append({
          "highlight": text.strip() if text else None,
          "note": note.strip() if note else None,
          "created_at": created_dt.isoformat() if created_dt else None,
          "modified_at": modified_dt.isoformat() if modified_dt else None,
          "style_code": style,
      })

  # 3. Export JSON Snapshot
  tag_start = start_dt.strftime("%Y-%m-%d")
  tag_end = end_dt.strftime("%Y-%m-%d")
  json_filename = f"snapshot_{tag_start}_to_{tag_end}.json"
  json_filepath = os.path.join(args.output_dir, json_filename)

  payload = {
      "query_window": {
          "start": start_dt.isoformat(),
          "end": end_dt.isoformat(),
      },
      "books_opened_in_range": recent_reading,
      "annotations_in_range": annotations_by_book,
  }

  with open(json_filepath, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

  # 4. Export Markdown Files for Highlights
  md_count = 0
  for title, data in annotations_by_book.items():
    filename = f"{sanitize_filename(title)}.md"
    file_path = os.path.join(md_notes_dir, filename)

    with open(file_path, "w", encoding="utf-8") as md:
      md.write(f"# {title}\n\n")
      md.write(f"- **Author:** {data['author']}\n")
      md.write(f"- **Date Range:** {tag_start} to {tag_end}\n")
      md.write(f"- **Highlights Extracted:** {len(data['annotations'])}\n\n")
      md.write("---\n\n")

      for item in data["annotations"]:
        if item["highlight"]:
          md.write(f"> {item['highlight']}\n\n")
        if item["note"]:
          md.write(f"**Note:** {item['note']}\n\n")
        md.write(f"*(Added: {item['created_at']})*\n\n---\n\n")

    md_count += 1

  print(f"Export complete for period: {tag_start} to {tag_end}")
  print(f"- Books opened in range: {len(recent_reading)}")
  print(
      f"- Books with new annotations: {len(annotations_by_book)} (saved to"
      f" {md_count} .md files)"
  )
  print(f"- Snapshot JSON: {json_filepath}")
  print(f"- Markdown folder: {md_notes_dir}/")


if __name__ == "__main__":
  main()