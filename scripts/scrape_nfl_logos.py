#!/usr/bin/env python3
"""
Scrape modern NFL team logos from Wikipedia.

Downloads the current primary logos (*.logo.svg format) for all 32 NFL teams.
"""

import os
import re
import time
from pathlib import Path
from urllib.parse import unquote

import requests

# Modern team logos - the primary logo files
MODERN_LOGOS = [
    "Arizona_Cardinals_logo.svg",
    "Atlanta_Falcons_logo.svg",
    "Baltimore_Ravens_logo.svg",
    "Buffalo_Bills_logo.svg",
    "Carolina_Panthers_logo.svg",
    "Chicago_Bears_logo.svg",
    "Cincinnati_Bengals_logo.svg",
    "Cleveland_Browns_logo.svg",
    "Dallas_Cowboys_logo.svg",
    "Denver_Broncos_logo.svg",
    "Detroit_Lions_logo.svg",
    "Green_Bay_Packers_logo.svg",
    "Houston_Texans_logo.svg",
    "Indianapolis_Colts_logo.svg",
    "Jacksonville_Jaguars_logo.svg",
    "Kansas_City_Chiefs_logo.svg",
    "Las_Vegas_Raiders_logo.svg",
    "Los_Angeles_Chargers_logo.svg",
    "Los_Angeles_Rams_logo.svg",
    "Miami_Dolphins_logo.svg",
    "Minnesota_Vikings_logo.svg",
    "New_England_Patriots_logo.svg",
    "New_Orleans_Saints_logo.svg",
    "New_York_Giants_logo.svg",
    "New_York_Jets_logo.svg",
    "Philadelphia_Eagles_logo.svg",
    "Pittsburgh_Steelers_logo.svg",
    "San_Francisco_49ers_logo.svg",
    "Seattle_Seahawks_logo.svg",
    "Tampa_Bay_Buccaneers_logo.svg",
    "Tennessee_Titans_logo.svg",
    "Washington_Commanders_logo.svg",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

OUTPUT_DIR = Path(__file__).parent.parent / "sprite-pipeline" / "input" / "logos"


def get_image_url(file_name: str) -> str | None:
    """
    Get the direct image URL from a Wikipedia File: page.

    The URL pattern for Wikipedia images is:
    https://upload.wikimedia.org/wikipedia/en/{hash}/{hash2}/{filename}

    We can construct this by fetching the file page and finding the direct link.
    """
    file_page_url = f"https://en.wikipedia.org/wiki/File:{file_name}"

    try:
        response = requests.get(file_page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        # Find the direct image link in the page
        # Look for the full-resolution link pattern
        pattern = rf'href="(//upload\.wikimedia\.org/wikipedia/\w+/[a-f0-9]/[a-f0-9]{{2}}/{re.escape(file_name)})"'
        match = re.search(pattern, response.text)

        if match:
            return "https:" + match.group(1)

        # Alternative pattern - sometimes in different format
        pattern2 = rf'(https://upload\.wikimedia\.org/wikipedia/\w+/[a-f0-9]/[a-f0-9]{{2}}/{re.escape(file_name)})'
        match2 = re.search(pattern2, response.text)

        if match2:
            return match2.group(1)

        # Try commons pattern
        pattern3 = rf'href="(//upload\.wikimedia\.org/wikipedia/commons/[a-f0-9]/[a-f0-9]{{2}}/{re.escape(file_name)})"'
        match3 = re.search(pattern3, response.text)

        if match3:
            return "https:" + match3.group(1)

        print(f"  Could not find image URL in page for {file_name}")
        return None

    except requests.RequestException as e:
        print(f"  Error fetching {file_page_url}: {e}")
        return None


def download_logo(file_name: str, output_dir: Path) -> bool:
    """Download a single logo file."""
    print(f"Processing: {file_name}")

    image_url = get_image_url(file_name)
    if not image_url:
        return False

    try:
        response = requests.get(image_url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # Save with a cleaner filename
        clean_name = file_name.replace("_logo", "").replace("_", " ")
        output_path = output_dir / file_name

        output_path.write_bytes(response.content)
        print(f"  Downloaded: {output_path.name} ({len(response.content)} bytes)")
        return True

    except requests.RequestException as e:
        print(f"  Error downloading {image_url}: {e}")
        return False


def main():
    """Download all modern NFL team logos."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(MODERN_LOGOS)} NFL team logos to {OUTPUT_DIR}\n")

    success = 0
    failed = []

    for logo in MODERN_LOGOS:
        if download_logo(logo, OUTPUT_DIR):
            success += 1
        else:
            failed.append(logo)

        # Be nice to Wikipedia servers
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Downloaded: {success}/{len(MODERN_LOGOS)} logos")

    if failed:
        print(f"\nFailed ({len(failed)}):")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
