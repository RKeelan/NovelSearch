#!/usr/bin/env python3

"""
Click-based CLI tool that handles both Hugo and Nebula Best Novel winners/nominees:
  1) 'scrape': Scrape/update a JSON file with:
       title, award ("Hugo"/"Nebula"), year (from the 'Year' column, which may be row-spanned),
       pov (None initially).
  2) 'process': Sort novels by year descending, open Amazon search page for the next unprocessed
     novel, prompt user for POV (1,2,3), update JSON, or exit.

Usage:
    python3 awards_cli.py scrape
    python3 awards_cli.py process

Dependencies:
    pip install click requests beautifulsoup4 lxml

Notes:
    - The Wikipedia tables for both Nebula and Hugo have a column titled "Year".
    - We'll parse the "Year" column (as best as we can) to find the year for each novel.
    - The "title" may appear in a cell with <i> tags. We'll record each novel found in that row.
    - The tables and columns can vary over the years. This code is a best-effort parser.
    - The "year" we capture is the award year. This is used as a proxy for "most recent" ordering.
"""

import os
import json
import click
import webbrowser
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

HUGO_URL = "https://en.wikipedia.org/wiki/Hugo_Award_for_Best_Novel"
NEBULA_URL = "https://en.wikipedia.org/wiki/Nebula_Award_for_Best_Novel"
JSON_FILENAME = "award_novels.json"

def load_novels_from_json(filename=JSON_FILENAME) -> List[Dict[str, Any]]:
    """Load existing JSON data if it exists; otherwise return an empty list."""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_novels_to_json(novels: List[Dict[str, Any]], filename=JSON_FILENAME):
    """Save the novel list to JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(novels, f, indent=2, ensure_ascii=False)

def parse_int(s: str) -> int:
    """
    Safely parse an integer from a string.
    Return 0 if parsing fails.
    """
    try:
        return int(s)
    except ValueError:
        return 0

def scrape_award_novels(url: str, award_name: str) -> List[Dict[str, Any]]:
    """
    Naive parser for either Hugo or Nebula awards Wikipedia tables:
      - Identify the column named "Year" in each table's header row
      - Skip tables that have both "Year" and "Year awarded" (Retro Hugos)
      - For each subsequent row, parse that cell for the year (carry it forward if it's row-spanned)
      - Gather all <i> tags in that row as novel titles
    Returns: list of dicts: { "title": ..., "award": ..., "year": <int>, "pov": None, "read": False }
    """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    award_novels = []

    tables = soup.find_all("table", class_="wikitable")
    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        # Header row: find the column index of "Year" and check for "Year awarded"
        header_cells = rows[0].find_all(["th", "td"])
        year_col_index = None
        is_retro_table = False
        
        # Check header cells for both "Year" and "Year awarded"
        header_texts = [cell.get_text(strip=True).lower() for cell in header_cells]
        if "year" in header_texts and "year awarded" in header_texts:
            continue  # Skip this table - it's Retro Hugos
            
        # Find the year column index
        for i, cell in enumerate(header_cells):
            col_title = cell.get_text(strip=True).lower()
            if "year" in col_title and "awarded" not in col_title:
                year_col_index = i
                break

        # If there's no 'Year' column, skip
        if year_col_index is None:
            continue

        current_year = 0  # track the last nonzero year we encountered
        # Iterate body rows
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            # If we have a cell for the year column, parse it
            if len(cells) > year_col_index:
                year_cell = cells[year_col_index].get_text(strip=True)
                # Skip if this is a Retro Hugo
                if "retro" in year_cell.lower():
                    continue
                new_year = parse_int(year_cell.split()[0])  # e.g. "1976 (tie)" -> "1976"
                if new_year > 0:
                    current_year = new_year

            # Skip row if current_year is from a Retro Hugo
            if current_year == 0:
                continue

            # Collect all <i> tags for novel titles in this row
            i_tags = row.find_all("i")
            for i_tag in i_tags:
                title = i_tag.get_text(strip=True)
                if title:
                    award_novels.append({
                        "title": title,
                        "award": award_name,
                        "year": current_year,
                        "pov": None,
                        "read": False
                    })

    return award_novels

def merge_award_entries(novels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge entries for novels that received both Hugo and Nebula awards.
    The award field will be 'Hugo|Nebula' for such novels.
    """
    # Create a dictionary keyed by (title, year) for easy lookup and merging
    novel_map = {}
    for novel in novels:
        key = (novel["title"], novel["year"])
        if key not in novel_map:
            novel_map[key] = novel
        else:
            # If we find a duplicate, combine the awards
            existing = novel_map[key]
            if existing["award"] != novel["award"]:
                # Sort awards alphabetically for consistency
                awards = sorted([existing["award"], novel["award"]])
                existing["award"] = "|".join(awards)
            # Keep any existing POV data
            if novel["pov"] is not None:
                existing["pov"] = novel["pov"]
            novel_map[key] = existing

    # Convert back to list
    novel_map.values())

@click.group()
@click.version_option()
def cli():
    "Search for novels"

@cli.command()
@click.option('--after', default=1990, help='Only include novels published in or after this year')
def scrape(after):
    """
    Scrape both Hugo and Nebula Best Novel winners/nominees from Wikipedia,
    merging them into award_novels.json. Preserve existing POV data if any.
    Only includes novels from the specified year onwards (default: 1990).
    """
    print("Scraping Hugo Award novels...")
    hugo_data = scrape_award_novels(HUGO_URL, "Hugo")
    print(f"Found {len(hugo_data)} Hugo entries.")

    print("Scraping Nebula Award novels...")
    nebula_data = scrape_award_novels(NEBULA_URL, "Nebula")
    print(f"Found {len(nebula_data)} Nebula entries.")

    combined_new = hugo_data + nebula_data
    
    # Filter novels by year
    combined_new = [novel for novel in combined_new if novel["year"] >= after]

    # Load existing JSON
    existing_data = load_novels_from_json(JSON_FILENAME)
    
    # Filter existing data by year as well
    existing_data = [novel for novel in existing_data if novel["year"] >= after]

    # Convert to dict for quick lookup: key = (title, year)
    existing_map = {}
    for item in existing_data:
        key = (item["title"], item["year"])
        existing_map[key] = item

    # Merge new data
    for item in combined_new:
        key = (item["title"], item["year"])
        if key not in existing_map:
            existing_map[key] = item
        else:
            # Keep POV if it's already set in existing data
            if existing_map[key].get("pov") is not None:
                item["pov"] = existing_map[key]["pov"]
            # Combine awards if they're different
            if item["award"] != existing_map[key]["award"]:
                awards = sorted([item["award"], existing_map[key]["award"]])
                item["award"] = "|".join(awards)
            existing_map[key] = item

    # Convert back to list
    merged_data = list(existing_map.values())
    
    # Sort ascending by (year, title) for consistent ordering
    merged_data.sort(key=lambda x: (x["year"], x["title"]))

    # Save
    save_novels_to_json(merged_data)
    print(f"Saved {len(merged_data)} unique novels from {after} onwards to {JSON_FILENAME}.")

@cli.command()
def process():
    """
    Sort all novels by year descending (most recent first).
    For each novel with no POV:
    - Open an Amazon search page
    - Let user assign POV (1,2,3), optionally with 'r' to mark as read
    - Examples: '1', '1r', 'r1' all valid for first person POV
    Continues until all novels are processed or user exits.
    """
    all_novels = load_novels_from_json(JSON_FILENAME)
    if not all_novels:
        print("No award novels found. Run 'scrape' first.")
        return

    # Sort by year descending
    all_novels.sort(key=lambda x: x["year"], reverse=True)

    while True:
        # Find next novel to process
        idx_to_process = None
        for i, novel in enumerate(all_novels):
            if not novel["pov"]:
                idx_to_process = i
                break

        if idx_to_process is None:
            print("All novels have assigned POV. Nothing left to process.")
            return

        novel = all_novels[idx_to_process]
        print(f"\nProcessing: '{novel['title']}' ({novel['award']} Award, year={novel['year']})")

        # Open Amazon search page
        search_url = f"https://www.amazon.com/s?k={novel['title'].replace(' ', '+')}"
        webbrowser.open(search_url)

        while True:
            user_input = input("Enter POV (1=First, 2=Second, 3=Third, add 'r' if read) or 'quit'/'exit': ").strip().lower()
            if user_input in ["quit", "exit"]:
                print("Exiting. Progress has been saved.")
                return

            # Check if input contains 'r' for read
            is_read = 'r' in user_input
            # Remove 'r' to check for POV number
            pov_input = user_input.replace('r', '')

            if pov_input == "1":
                novel["pov"] = "first"
                novel["read"] = is_read
                break
            elif pov_input == "2":
                novel["pov"] = "second"
                novel["read"] = is_read
                break
            elif pov_input == "3":
                novel["pov"] = "third"
                novel["read"] = is_read
                break
            else:
                print("Invalid input. Please enter 1, 2, 3 (optionally with 'r'), or quit/exit.")

        # Save updated data after each novel
        save_novels_to_json(all_novels)
        read_status = "and marked as read" if novel["read"] else "and marked as unread"
        print(f"Set POV = {novel['pov']} {read_status} for '{novel['title']}'")

if __name__ == "__main__":
    cli()
