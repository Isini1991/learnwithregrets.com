#!/usr/bin/env python3
"""
Sync Bandcamp releases for boy (Adam Leach) / Call Me A Friend.
Fetches https://callmeafriend.bandcamp.com/music, discovers all releases,
downloads high-res album covers, and updates data.json, data.js, and index.html.
"""

import os
import sys
import re
import json
import html as html_lib
import urllib.request
import time
from datetime import datetime
from bs4 import BeautifulSoup

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets')
DATA_JSON = os.path.join(ROOT_DIR, 'data.json')
DATA_JS = os.path.join(ROOT_DIR, 'data.js')
INDEX_HTML = os.path.join(ROOT_DIR, 'index.html')
LAST_SYNC = os.path.join(ROOT_DIR, '.github', 'last_sync.json')

BANDCAMP_URL = 'https://callmeafriend.bandcamp.com/music'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def fetch_url(url, retries=3, delay=2):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if attempt == retries - 1:
                print(f"Error fetching {url}: {e}")
                return None
            time.sleep(delay)
    return None


def download_file(url, target_path, retries=3):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            with open(target_path, 'wb') as f:
                f.write(data)
            return True
        except Exception as e:
            if attempt == retries - 1:
                print(f"Error downloading {url} -> {target_path}: {e}")
                return False
            time.sleep(2)
    return False


def get_music_catalog():
    print(f"Fetching Bandcamp music grid from {BANDCAMP_URL}...")
    page_html = fetch_url(BANDCAMP_URL)
    if not page_html:
        raise RuntimeError("Failed to fetch Bandcamp music page.")

    soup = BeautifulSoup(page_html, 'html.parser')
    grid_items = soup.find_all('li', class_=re.compile(r'music-grid-item'))

    discovered = []
    seen_urls = set()

    for li in grid_items:
        t_el = li.find('p', class_='title')
        a_el = li.find('a')
        img_el = li.find('img')
        if a_el and t_el:
            href = a_el['href']
            full_url = 'https://callmeafriend.bandcamp.com' + href if href.startswith('/') else href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            img_src = img_el.get('src', '') if img_el else ''
            art_id = None
            m_art = re.search(r'/img/a(\d+)_', img_src)
            if m_art:
                art_id = int(m_art.group(1))

            discovered.append({
                'title': t_el.text.strip(),
                'url': full_url,
                'art_id': art_id
            })

    m = re.search(r'data-client-items=\"([^\"]+)\"', page_html)
    if m:
        try:
            client_items = json.loads(html_lib.unescape(m.group(1)))
            for it in client_items:
                page_url = it.get('page_url', '')
                full_url = 'https://callmeafriend.bandcamp.com' + page_url if page_url.startswith('/') else page_url
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                discovered.append({
                    'title': it.get('title'),
                    'url': full_url,
                    'art_id': it.get('art_id'),
                    'id': str(it.get('id', ''))
                })
        except Exception as e:
            print(f"Warning: could not parse data-client-items: {e}")

    print(f"Discovered {len(discovered)} releases from Bandcamp.")
    return discovered


def fetch_album_details(url):
    html_content = fetch_url(url)
    if not html_content:
        return None

    m = re.search(r'data-tralbum=\"([^\"]+)\"', html_content)
    if not m:
        m = re.search(r'var TrAlbumData = ({.*?});', html_content, re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group(1))
    else:
        data = json.loads(html_lib.unescape(m.group(1)))

    current = data.get('current', {})
    title = current.get('title')
    aid = str(current.get('id', ''))
    about = current.get('about')
    rel_date = current.get('release_date') or current.get('publish_date')
    art_id = data.get('art_id')

    iso = ''
    date_str = ''
    if rel_date:
        try:
            dt = datetime.strptime(rel_date[:11], '%d %b %Y')
            iso = dt.strftime('%Y-%m-%d')
            date_str = dt.strftime('%b %d, %Y').upper()
        except Exception:
            pass

    trackinfo = data.get('trackinfo', [])
    tracks = []
    for t in trackinfo:
        dur = t.get('duration')
        if dur is not None:
            m_part = int(dur // 60)
            s_part = int(round(dur % 60))
            if s_part == 60:
                m_part += 1
                s_part = 0
            dur_str = f'{m_part}:{s_part:02d}'
        else:
            dur_str = ''
        tracks.append({'t': t['title'], 'd': dur_str})

    return {
        'title': title,
        'url': url,
        'id': aid,
        'art_id': art_id,
        'iso': iso,
        'date': date_str,
        'about': about,
        'tracks': tracks
    }


def update_index_html(catalog):
    if not os.path.exists(INDEX_HTML):
        return False

    with open(INDEX_HTML, 'r', encoding='utf-8') as f:
        html = f.read()

    total = len(catalog)
    latest = catalog[0]
    latest_title = latest['title']
    latest_asset = latest['asset']
    latest_upper = latest_title.upper()
    latest_about = latest.get('about') or 'A record by boy.'
    latest_url = latest.get('url', BANDCAMP_URL)

    # 1. Total counts
    html = re.sub(r'The records <sup>\d+</sup>', f'The records <sup>{total}</sup>', html)
    html = re.sub(r'\d+ RECORDS\. KEEP DIGGING\.', f'{total} RECORDS. KEEP DIGGING.', html)
    html = re.sub(r'The record shelf<span> \(\d+\)</span>', f'The record shelf<span> ({total})</span>', html)

    # 2. Hero front sleeve
    pattern_sleeve = r'(<button class=\"front-sleeve\" data-album=\"0\" aria-label=\")[^\"]*(\"><span class=\"sleeve-bar mono\"><span>BOY / )[^<]*(</span><span>SIDE A ↗</span></span><img src=\")[^\"]*(\" alt=\")[^\"]*(\")'
    repl_sleeve = rf'\g<1>Open {latest_title} in the listening room\g<2>{latest_upper}\g<3>{latest_asset}\g<4>{latest_title} album cover\g<5>'
    html = re.sub(pattern_sleeve, repl_sleeve, html)

    # 3. Listening room
    pattern_art = r'(<div class=\"feature-art\"><img src=\")[^\"]*(\" alt=\")[^\"]*(\" width=\"500\" height=\"500\" loading=\"lazy\"><span class=\"art-label mono\">BOY — )[^<]*(</span></div>)'
    repl_art = rf'\g<1>{latest_asset}\g<2>{latest_title}\g<3>{latest_upper}\g<4>'
    html = re.sub(pattern_art, repl_art, html)

    # Title in listening room: break into words
    words = latest_title.split()
    if len(words) == 1:
        h2_title = f'<em>{words[0]}.</em>'
    elif len(words) == 2:
        h2_title = f'{words[0]}<br><em>{words[1]}.</em>'
    else:
        h2_title = f"{' '.join(words[:-1])}<br><em>{words[-1]}.</em>"

    html = re.sub(
        r'(<div class=\"feature-copy\"><span class=\"eyebrow\">START HERE</span><h2>).*?(</h2>)',
        rf'\g<1>{h2_title}\g<2>',
        html,
        flags=re.DOTALL
    )

    # Description
    clean_about = latest_about.replace('\r', '').replace('\n', ' ').strip()
    html = re.sub(
        r'(<p class=\"feature-description\">).*?(</p>)',
        rf'\g<1>{clean_about}\g<2>',
        html
    )

    # Support on Bandcamp link
    html = re.sub(
        r'<a href=\"https://callmeafriend\.bandcamp\.com/album/[^\"]*\" target=\"_blank\" rel=\"noopener\">Support on Bandcamp ↗</a>',
        f'<a href="{latest_url}" target="_blank" rel="noopener">Support on Bandcamp ↗</a>',
        html
    )

    # Bump cache buster timestamp
    v_tag = int(time.time())
    html = re.sub(r'data\.js\?v=\w+', f'data.js?v={v_tag}', html)
    html = re.sub(r'app\.js\?v=\w+', f'app.js?v={v_tag}', html)

    with open(INDEX_HTML, 'w', encoding='utf-8') as f:
        f.write(html)

    return True


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, '.github'), exist_ok=True)

    # Load existing catalog
    existing_catalog = []
    if os.path.exists(DATA_JSON):
        try:
            with open(DATA_JSON, 'r', encoding='utf-8') as f:
                existing_catalog = json.load(f)
        except Exception:
            existing_catalog = []

    existing_by_url = {item['url']: item for item in existing_catalog if 'url' in item}

    discovered = get_music_catalog()
    if not discovered:
        print("No releases found on Bandcamp.")
        sys.exit(0)

    updated_catalog = []
    changes_made = []

    for item in discovered:
        url = item['url']
        art_id = item.get('art_id')
        slug = url.rstrip('/').split('/')[-1]
        asset_rel = f"assets/{slug}.jpg"
        asset_abs = os.path.join(ROOT_DIR, asset_rel)

        existing = existing_by_url.get(url)

        # Check if we can reuse existing cached data
        need_fetch = False
        if not existing:
            need_fetch = True
            changes_made.append(f"NEW ALBUM: {item['title']} ({url})")
        elif art_id and existing.get('art_id') != art_id:
            need_fetch = True
            changes_made.append(f"UPDATED COVER: {item['title']} (art_id {existing.get('art_id')} -> {art_id})")
        elif not os.path.exists(asset_abs):
            need_fetch = True
            changes_made.append(f"MISSING ASSET: {asset_rel}")

        if need_fetch:
            print(f"Fetching details for: {item['title']} ({url})...")
            details = fetch_album_details(url)
            if not details:
                print(f"Failed to fetch details for {url}, keeping existing if available.")
                if existing:
                    updated_catalog.append(existing)
                continue

            # Download artwork
            target_art_id = details.get('art_id') or art_id
            if target_art_id:
                img_download_url = f"https://f4.bcbits.com/img/a{target_art_id}_10.jpg"
                print(f"Downloading artwork {img_download_url} -> {asset_abs}...")
                download_file(img_download_url, asset_abs)

            album_entry = {
                'title': details['title'] or item['title'],
                'url': url,
                'asset': asset_rel,
                'id': details['id'],
                'art_id': target_art_id,
                'iso': details['iso'],
                'date': details['date'],
                'about': details['about'],
                'tracks': details['tracks']
            }
            updated_catalog.append(album_entry)
        else:
            # Reusing existing, ensure art_id is preserved
            if art_id and not existing.get('art_id'):
                existing['art_id'] = art_id
            updated_catalog.append(existing)

    # Check for order changes or length differences
    old_titles = [x.get('title') for x in existing_catalog]
    new_titles = [x.get('title') for x in updated_catalog]
    if old_titles != new_titles:
        changes_made.append(f"CATALOG ORDER/ITEMS CHANGED: {len(old_titles)} -> {len(new_titles)} albums")

    # Keepalive check: if no changes in 40+ days, touch last_sync to prevent GitHub Actions cron disable
    try:
        import subprocess
        res = subprocess.run(['git', 'log', '-1', '--format=%ct'], cwd=ROOT_DIR, capture_output=True, text=True)
        if res.stdout.strip():
            last_ts = int(res.stdout.strip())
            days_since = (time.time() - last_ts) / 86400
            if days_since >= 40 and not changes_made:
                changes_made.append(f"KEEPALIVE: {days_since:.1f} days since last commit; refreshing cron timer")
    except Exception as e:
        print(f"Keepalive check notice: {e}")

    print(f"\nFinal catalog contains {len(updated_catalog)} releases.")

    # Write data.json
    with open(DATA_JSON, 'w', encoding='utf-8') as f:
        json.dump(updated_catalog, f, ensure_ascii=False, indent=2)

    # Write data.js
    with open(DATA_JS, 'w', encoding='utf-8') as f:
        f.write('window.CATALOG=' + json.dumps(updated_catalog, ensure_ascii=False) + ';\n')

    # Update index.html
    update_index_html(updated_catalog)

    # Write keepalive / sync record
    sync_record = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'total_releases': len(updated_catalog),
        'latest_album': updated_catalog[0]['title'] if updated_catalog else '',
        'changes': changes_made
    }
    with open(LAST_SYNC, 'w', encoding='utf-8') as f:
        json.dump(sync_record, f, indent=2)

    if changes_made:
        print("\nSummary of updates:")
        for c in changes_made:
            print(" -", c)
    else:
        print("\nNo new albums or cover changes detected.")

    print("\nSync completed successfully.")


if __name__ == '__main__':
    main()
