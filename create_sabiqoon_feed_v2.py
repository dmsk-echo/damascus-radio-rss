#!/usr/bin/env python3
"""
Create an RSS podcast feed for "السابقون" from the official Sonaar playlist JSON.

Usage:
    source .venv/bin/activate.fish   # Fish shell; omit if already activated
    python -m pip install requests
    python create_sabiqoon_feed.py

Output:
    sabiqoon.xml

The ALBUM_IDS list comes from the Sonaar playlist request observed in Firefox.
If Radio Damascus adds episodes, refresh the series page, copy its updated
playlist.json request, and replace ALBUM_IDS below.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlencode, unquote

import requests

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)
ITUNES = "{" + ITUNES_NS + "}"

BASE_URL = "https://damasradio.fm/"
ALBUM_IDS = (
    "58314,58318,58321,58339,58342,58345,58348,58351,59010,59116,"
    "59425,59620,59844,60015,60213,60348,60483,60649,60876,61051,"
    "61253,61383,61539,61660,61938,62076,62210,62438,62714"
)
OUTPUT = "sabiqoon.xml"

PARAMS = {
    "load": "playlist.json",
    "title": "",
    "albums": ALBUM_IDS,
    "category": "",
    "posts_not_in": "",
    "category_not_in": "",
    "author": "",
    "feed_title": "",
    "feed": "",
    "feed_img": "",
    "el_widget_id": "",
    "artwork": "",
    "posts_per_pages": "-1",
    "all_category": "",
    "single_playlist": "1",
    "reverse_tracklist": "",
    "audio_meta_field": "",
    "repeater_meta_field": "",
    "import_file": "",
    "rss_items": "-1",
    "rss_item_title": "",
    "is_favorite": "",
    "is_recentlyplayed": "",
    "srp_order": "menu_order_asc",
}

SERIES_URL = "https://damasradio.fm/drama/السابقون/"
COVER_URL = "https://damasradio.fm/wp-content/uploads/2026/11/السابقون_29-400x300.webp"

def add_text(parent, tag, value):
    el = ET.SubElement(parent, tag)
    el.text = str(value)
    return el

def main():
    url = BASE_URL + "?" + urlencode(PARAMS)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": BASE_URL,
    }

    print("Lade Sonaar-Playlist von Radio Damaskus …")
    response = requests.get(url, headers=headers, timeout=40)
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError:
        print("Fehler: Die Serverantwort ist kein gültiges JSON.", file=sys.stderr)
        print(response.text[:1500], file=sys.stderr)
        return 2

    tracks = payload.get("tracks", []) if isinstance(payload, dict) else []
    if not isinstance(tracks, list):
        print("Fehler: JSON enthält keine gültige 'tracks'-Liste.", file=sys.stderr)
        return 2

    # Keep only tracks that belong to this series and have a usable audio URL.
    episodes = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        title = str(track.get("track_title") or track.get("album_title") or "").strip()
        audio = str(track.get("mp3") or "").strip()
        if not title or not audio.startswith("https://media.damasradio.fm/"):
            continue
        if "/السابقون/" not in unquote(audio):
            continue
        match = re.search(r"(?:الحلقة|ح)\s*\(?\s*(\d+)", title)
        number = int(match.group(1)) if match else len(episodes) + 1
        episodes.append({
            "number": number,
            "title": title,
            "audio": audio,
            "poster": str(track.get("poster") or COVER_URL),
        })

    if not episodes:
        print("Keine passenden Folgen gefunden. JSON-Struktur oder Playlist-IDs prüfen.", file=sys.stderr)
        return 3

    episodes.sort(key=lambda item: item["number"])

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    add_text(channel, "title", "السابقون – إذاعة دمشق")
    add_text(channel, "link", SERIES_URL)
    add_text(channel, "description", "السابقون – مسلسل إذاعي من إذاعة دمشق.")
    add_text(channel, "language", "ar")
    add_text(channel, "lastBuildDate", format_datetime(datetime.now(timezone.utc)))
    add_text(channel, ITUNES + "author", "إذاعة دمشق")
    add_text(channel, ITUNES + "explicit", "false")
    add_text(channel, ITUNES + "summary", "السابقون – مسلسل إذاعي من إذاعة دمشق.")
    image = ET.SubElement(channel, ITUNES + "image", {"href": COVER_URL})

    for ep in episodes:
        item = ET.SubElement(channel, "item")
        add_text(item, "title", ep["title"])
        add_text(item, "description", ep["title"])
        add_text(item, "link", SERIES_URL)
        add_text(item, "guid", ep["audio"]).set("isPermaLink", "false")
        ET.SubElement(item, "enclosure", {
            "url": ep["audio"],
            "length": "0",
            "type": "audio/mpeg",
        })
        add_text(item, ITUNES + "episode", ep["number"])
        add_text(item, ITUNES + "episodeType", "full")
        ET.SubElement(item, ITUNES + "image", {"href": ep["poster"]})

    ET.indent(rss, space="  ")
    tree = ET.ElementTree(rss)
    tree.write(OUTPUT, encoding="utf-8", xml_declaration=True)

    print(f"RSS-Feed erstellt: {OUTPUT}")
    print(f"Erkannte Folgen: {len(episodes)}")
    print(f"Folgenbereich: {episodes[0]['number']} bis {episodes[-1]['number']}")
    print("Hinweis: Die Website liefert keine Veröffentlichungsdaten oder Dateigrößen;")
    print("deshalb werden pubDate weggelassen und enclosure length auf 0 gesetzt.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
