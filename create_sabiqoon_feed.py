#!/usr/bin/env python3
"""Build an RSS feed for إذاعة دمشق's السابقون from its public episode pages.

Install: python3 -m pip install --user requests beautifulsoup4
Run:     python3 create_sabiqoon_feed.py
Output:  sabiqoon.xml (audio is streamed from the radio station; not downloaded)
"""
import re, html, sys
from pathlib import Path
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

SERIES = 'https://damasradio.fm/drama/السابقون/'
OUT = Path('sabiqoon.xml')
MEDIA_RE = re.compile(r'''https?://media\.damasradio\.fm/[^"'<>\\\s]+?\.(?:mp3|m4a|aac|wav)(?:\?[^"'<>\\\s]*)?''', re.I)
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0', 'Accept-Language': 'ar,en;q=0.8'}

def media_from(source, soup):
    for tag in soup.find_all(['audio', 'source', 'a']):
        for attr in ('src', 'href', 'data-src', 'data-audio', 'data-url'):
            value = tag.get(attr)
            if value and 'media.damasradio.fm/' in value and re.search(r'\.(mp3|m4a|aac|wav)(\?|$)', value, re.I):
                return html.unescape(value).replace(r'\\/', '/')
    found = MEDIA_RE.findall(source.replace(r'\\/', '/'))
    if found:
        found.sort(key=lambda u: (not u.lower().split('?')[0].endswith('.mp3'), len(u)))
        return html.unescape(found[0])
    return None

def x(value):
    return (value or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

def main():
    s = requests.Session(); s.headers.update(HEADERS)
    print('Abrufe Serienübersicht:', SERIES)
    r = s.get(SERIES, timeout=30); r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        u = urljoin(SERIES, a['href'])
        if '/drama-episode/' in u and u not in links: links.append(u)
    if not links:
        print('Keine Episodenlinks gefunden. Website-Struktur könnte geändert worden sein.', file=sys.stderr); return 2
    eps = []
    for i, link in enumerate(links, 1):
        try:
            page = s.get(link, timeout=30); page.raise_for_status()
            sp = BeautifulSoup(page.text, 'html.parser')
            og = sp.find('meta', attrs={'property':'og:title'})
            h1 = sp.find('h1')
            title = (og.get('content','').strip() if og else '') or (h1.get_text(' ',strip=True) if h1 else '') or f'السابقون – الحلقة {i}'
            md = sp.find('meta', attrs={'name':'description'})
            desc = md.get('content','').strip() if md else title
            audio = media_from(page.text, sp)
            if not audio:
                print('[ÜBERSPRUNGEN] Keine Audio-URL:', title); continue
            m = re.search(r'(?:الحلقة|ح)\s*[:(]?\s*(\d+)', title)
            number = int(m.group(1)) if m else i
            eps.append((number, title, desc, link, audio))
            print(f'[OK] Folge {number}: {title}')
        except Exception as e:
            print('[WARNUNG]', link, e, file=sys.stderr)
    eps.sort(key=lambda z:z[0])
    if not eps:
        print('Keine abspielbaren Audio-URLs extrahiert. Bitte Ausgabe zur Fehlersuche senden.', file=sys.stderr); return 3
    items=[]
    for n,title,desc,link,audio in eps:
        items.append(f'''    <item>\n      <title>{x(title)}</title>\n      <description>{x(desc)}</description>\n      <link>{x(link)}</link>\n      <guid isPermaLink="false">{x(audio)}</guid>\n      <enclosure url="{x(audio)}" length="0" type="audio/mpeg" />\n      <itunes:episode>{n}</itunes:episode>\n      <itunes:episodeType>full</itunes:episodeType>\n    </item>''')
    now = format_datetime(datetime.now(timezone.utc))
    feed = f'''<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n  <channel>\n    <title>السابقون – إذاعة دمشق</title>\n    <link>{SERIES}</link>\n    <description>برنامج تاريخي ديني يوثق سير وأمجاد كوكبة من الصحابة الأجلاء – إذاعة دمشق.</description>\n    <language>ar</language>\n    <lastBuildDate>{now}</lastBuildDate>\n    <itunes:author>إذاعة دمشق</itunes:author>\n    <itunes:explicit>false</itunes:explicit>\n    <itunes:category text="History" />\n{chr(10).join(items)}\n  </channel>\n</rss>\n'''
    OUT.write_text(feed, encoding='utf-8')
    print(f'\nFeed erstellt: {OUT.resolve()}')
    print(f'Abspielbare Folgen: {len(eps)} von {len(links)} gefundenen Episodenseiten')
    print('Hinweis: Die Audiodateien werden nicht heruntergeladen; der Feed verweist auf den Originalserver.')
    print('Für AntennaPod muss sabiqoon.xml unter einer öffentlichen HTTPS-Adresse erreichbar sein.')
    return 0

if __name__ == '__main__': raise SystemExit(main())
