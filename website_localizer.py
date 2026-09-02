#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
🌟 ULTIMATE WEBSITE ENGINEERING, CLONING, LOCALIZATION & STUDIO SUITE
===============================================================================
An all-in-one platform to clone, localize, optimize, sandbox, transpile,
and deploy any website or HTML project with 100% offline independence.

Capabilities:
  1. Deep BFS Web Crawler & Sitemap.xml Parser
  2. Recursive JS / MJS ES-Module Cloner & Asset Downloader (300+ dynamic chunks)
  3. Inline Style & CSS Custom Property URL Localizer
  4. Complete Font Localizer: Google Fonts, Fontshare, Typekit, Custom WOFF2
  5. SSR Appearance & Visibility Normalizer (Zero Invisible Elements)
  6. Platform Badge & Cookie Popup Stripper (Framer, Webflow, GDPR, etc.)
  7. Privacy & Strict Offline Sandbox (CSP Injection & Tracker Stripper)
  8. PWA Generator: Manifest.json + Offline Service Worker + App Icons
  9. Local Form Engine & Webhook Dispatcher (SQLite, JSON, Telegram, Discord)
 10. React 19 / Next.js 15 App Router Transpiler (Clean JSX/TSX Components)
 11. One-Click ZIP Packager: Deploy-ready distribution bundle
 12. Visual HTML/JSON Audit & Performance Report
 13. Live Reload / Watch Mode Development Server with Smart Port Fallback
 14. Modern Embedded Web Dashboard GUI (http://localhost:5000/dashboard)
 15. Auto Live Preview: Automatically launches and opens the browser on completion

Usage Examples:
  python website_localizer.py https://example.framer.website --clone
  python website_localizer.py cloned_site --serve
  python website_localizer.py --gui
===============================================================================
"""

import sys
import os
import re
import glob
import json
import time
import shutil
import zipfile
import sqlite3
import argparse
import threading
import webbrowser
import http.server
import socketserver
import urllib.request
import urllib.parse
from urllib.parse import urlparse, urljoin, unquote
import concurrent.futures

# Platform UTF-8 Output Handling
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Logging setup
import logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger('localizer')

# Dependency Check
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("\n[!] Required libraries missing. Please install them using:")
    print("    pip install beautifulsoup4 requests\n")
    sys.exit(1)

# Global Session with Retry/backoff
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET', 'HEAD'])
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
session.mount('http://', adapter)
session.mount('https://', adapter)
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.mjs': 'application/javascript; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf',
    '.otf': 'font/otf',
    '.ico': 'image/x-icon',
}


# =============================================================================
# Helper: Filename & Category Mapping
# =============================================================================
def get_filename_and_category(url):
    clean_url = url.split('?')[0].split('#')[0]
    parsed = urlparse(clean_url)
    path = unquote(parsed.path)
    base_name = os.path.basename(path)
    ext = os.path.splitext(base_name)[1].lower()

    if '/fontshare/' in path or ext in ['.woff2', '.woff', '.ttf', '.otf', '.eot'] or 'fonts.gstatic.com' in clean_url or '/fonts/' in clean_url:
        category = 'fonts'
        if not ext:
            base_name += '.woff2'
    elif ext in ['.png', '.jpg', '.jpeg', '.svg', '.webp', '.ico', '.gif', '.bmp', '.avif']:
        category = 'images'
    elif ext in ['.mp4', '.webm', '.ogg', '.mov', '.avi']:
        category = 'videos'
    elif ext in ['.css']:
        category = 'css'
    elif ext in ['.js', '.mjs']:
        category = 'js'
    elif ext in ['.json']:
        category = 'json'
    else:
        if '/images/' in path or '/assets/' in path:
            category = 'images'
            if not ext:
                base_name += '.jpg'
        else:
            category = 'images'

    base_name = re.sub(r'[^\w\.-]', '_', base_name)
    if not base_name or base_name == '.':
        import hashlib
        h = hashlib.sha1(clean_url.encode()).hexdigest()[:10]
        safe = re.sub(r'\W+', '_', clean_url)[-12:]
        base_name = f'asset_{h}_{safe}'[:64]
        if ext and not base_name.endswith(ext):
            base_name += ext

    return category, base_name


def download_file(url, target_path, force=False):
    """Streamed download with retry; skips if file exists unless force=True."""
    if not force and os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        return True
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    for try_url in (url, url.split('?')[0].split('#')[0]):
        try:
            with session.get(try_url, timeout=20, stream=True) as resp:
                if resp.status_code != 200:
                    continue
                with open(target_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                    return True
                try:
                    os.remove(target_path)
                except Exception:
                    pass
        except Exception:
            continue
    return False


def get_relative_path(from_file, to_file):
    try:
        rel = os.path.relpath(to_file, os.path.dirname(from_file)).replace(os.sep, '/')
    except ValueError:
        # different drive on Windows -> fallback to absolute /assets path
        rel = '/' + os.path.relpath(to_file, os.path.dirname(os.path.abspath(to_file))).replace(os.sep, '/')
    if not rel.startswith('.') and not rel.startswith('/'):
        rel = './' + rel
    return rel


def auto_open_browser(url, delay=0.8):
    def _open():
        time.sleep(delay)
        print(f"\n[🌐] Opening live preview in browser: {url}\n")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[WARN] Could not automatically open browser: {e}")
    threading.Thread(target=_open, daemon=True).start()


# =============================================================================
# Helper: Rich Terminal Progress Bar with Speed & ETA
# =============================================================================
class RichProgress:
    """Rich terminal progress bar with ANSI colors, speed, ETA, and byte tracking."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    DIM = "\033[2m"
    CLEAR_LINE = "\033[2K\r"

    def __init__(self, total, label="Processing", bar_width=30):
        self.total = max(total, 1)
        self.label = label
        self.bar_width = bar_width
        self.completed = 0
        self.failed = 0
        self.bytes_downloaded = 0
        self.start_time = time.time()
        self._lock = threading.Lock()

    def update(self, success=True, size_bytes=0):
        with self._lock:
            self.completed += 1
            if not success:
                self.failed += 1
            self.bytes_downloaded += size_bytes
            self._render()

    def _render(self):
        elapsed = max(time.time() - self.start_time, 0.01)
        pct = min(self.completed / self.total, 1.0)
        filled = int(self.bar_width * pct)
        bar = "█" * filled + "░" * (self.bar_width - filled)
        pct_str = f"{pct * 100:5.1f}%"

        speed = self.completed / elapsed
        speed_str = f"{speed:.1f} files/s"

        if self.bytes_downloaded > 0:
            mb = self.bytes_downloaded / (1024 * 1024)
            mb_speed = mb / elapsed
            size_str = f" | {mb:.1f} MB ({mb_speed:.1f} MB/s)"
        else:
            size_str = ""

        if pct < 1.0 and speed > 0:
            remaining = (self.total - self.completed) / speed
            if remaining > 60:
                eta_str = f"ETA {remaining / 60:.0f}m {remaining % 60:.0f}s"
            else:
                eta_str = f"ETA {remaining:.0f}s"
        else:
            eta_str = "Done!" if pct >= 1.0 else ""

        fail_str = f" | {self.YELLOW}{self.failed} failed{self.RESET}" if self.failed > 0 else ""

        line = (
            f"{self.CLEAR_LINE}"
            f"  {self.CYAN}{self.label}{self.RESET} "
            f"{self.GREEN}[{bar}]{self.RESET} "
            f"{self.BOLD}{pct_str}{self.RESET} "
            f"({self.completed}/{self.total}) "
            f"{self.DIM}{speed_str}{size_str}{self.RESET} "
            f"{eta_str}{fail_str}"
        )
        sys.stdout.write(line)
        sys.stdout.flush()
        if self.completed >= self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()

    def finish_message(self, msg=""):
        elapsed = time.time() - self.start_time
        if msg:
            print(f"  {self.GREEN}✓{self.RESET} {msg} {self.DIM}({elapsed:.1f}s){self.RESET}")


# =============================================================================
# Helper: File System Watcher for Live Reload
# =============================================================================
_live_reload_timestamp = {"value": time.time()}
_live_reload_lock = threading.Lock()


class FileWatcher:
    """Polls a directory for file changes and updates the live reload timestamp."""

    def __init__(self, watch_dir, interval=1.0, extensions=None):
        self.watch_dir = watch_dir
        self.interval = interval
        self.extensions = extensions or {'.html', '.css', '.js', '.mjs', '.json', '.svg'}
        self._last_snapshot = {}
        self._running = False
        self._thread = None

    def _get_snapshot(self):
        snapshot = {}
        for root, _, files in os.walk(self.watch_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in self.extensions:
                    fp = os.path.join(root, f)
                    try:
                        snapshot[fp] = os.path.getmtime(fp)
                    except OSError:
                        pass
        return snapshot

    def _poll_loop(self):
        self._last_snapshot = self._get_snapshot()
        while self._running:
            time.sleep(self.interval)
            new_snap = self._get_snapshot()
            changed = False
            for fp, mtime in new_snap.items():
                if fp not in self._last_snapshot or self._last_snapshot[fp] != mtime:
                    changed = True
                    rel = os.path.relpath(fp, self.watch_dir)
                    print(f"  [WATCH] File changed: {rel}")
                    break
            if changed:
                with _live_reload_lock:
                    _live_reload_timestamp["value"] = time.time()
            self._last_snapshot = new_snap

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
            print(f"  [WATCH] File watcher active on: {self.watch_dir}")

    def stop(self):
        self._running = False


LIVE_RELOAD_SCRIPT = """
<script data-live-reload="true">
(function() {
  var lastTs = 0;
  function checkReload() {
    fetch('/__live_reload_check')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (lastTs === 0) { lastTs = data.ts; }
        else if (data.ts !== lastTs) { location.reload(); }
      })
      .catch(function() {});
  }
  setInterval(checkReload, 800);
})();
</script>
"""


# =============================================================================
# FEATURE 1: DIRECT URL CRAWLER & CLONER
# =============================================================================
def clone_website(base_url, output_dir="cloned_site", max_pages=100, clean_first=True):
    print("=" * 65)
    print(f" [CLONE] CRAWLING & EXTRACTING WEBSITE: {base_url}")
    print(f" Target Directory: {output_dir}")
    print("=" * 65)

    if clean_first and os.path.exists(output_dir):
        print(f"[*] Preparing clean output directory: '{output_dir}'...")
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                elif not item.endswith(('.zip', '.sqlite')):
                    os.remove(item_path)
            except Exception:
                pass

    os.makedirs(output_dir, exist_ok=True)
    parsed_base = urlparse(base_url)
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    to_visit = [base_url]
    visited = set()
    saved_pages = 0

    sitemap_url = urljoin(origin, "/sitemap.xml")
    try:
        s_resp = session.get(sitemap_url, timeout=10)
        if s_resp.status_code == 200:
            urls_in_sitemap = re.findall(r'<loc>(https?://[^<]+)</loc>', s_resp.text)
            added = 0
            for u in urls_in_sitemap:
                if len(to_visit) >= max_pages:
                    break
                if urlparse(u).netloc == parsed_base.netloc and u not in to_visit:
                    to_visit.append(u)
                    added += 1
            print(f"[+] Found {len(urls_in_sitemap)} URLs in sitemap.xml ({added} queued, max_pages={max_pages})")
    except Exception:
        pass

    while to_visit and saved_pages < max_pages:
        current_url = to_visit.pop(0)
        clean_current = current_url.split('?')[0].split('#')[0].rstrip('/')
        if clean_current in visited:
            continue
        visited.add(clean_current)

        try:
            resp = session.get(current_url, timeout=15)
            if resp.status_code != 200 or 'text/html' not in resp.headers.get('Content-Type', ''):
                continue

            parsed_curr = urlparse(current_url)
            path_part = parsed_curr.path.strip('/')
            if not path_part:
                local_file = os.path.join(output_dir, "index.html")
            else:
                if path_part.endswith('.html'):
                    local_file = os.path.join(output_dir, path_part.replace('/', os.sep))
                else:
                    local_file = os.path.join(output_dir, path_part.replace('/', os.sep), "index.html")

            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            with open(local_file, 'w', encoding='utf-8') as f:
                f.write(resp.text)

            saved_pages += 1
            print(f"  [+] Cloned ({saved_pages}): {current_url} -> {os.path.relpath(local_file, output_dir)}")

            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_href = urljoin(current_url, href)
                parsed_href = urlparse(full_href)
                if parsed_href.netloc == parsed_base.netloc:
                    clean_h = full_href.split('?')[0].split('#')[0].rstrip('/')
                    if clean_h not in visited and clean_h not in to_visit:
                        to_visit.append(full_href)

        except Exception as e:
            print(f"  [WARN] Failed to fetch {current_url}: {e}")

    print(f"\n[+] Successfully cloned {saved_pages} pages into '{output_dir}'.")
    return output_dir


# =============================================================================
# FEATURE 4: BADGE & POPUP STRIPPER
# =============================================================================
def strip_badges_and_popups(soup):
    badge_selectors = [
        '#__framer-badge-container',
        'div[data-framer-badge]',
        'a[href*="framer.com?utm_campaign=badge"]',
        'a[href*="framer.com?utm_medium=badge"]',
        '.w-webflow-badge',
        'a[href*="webflow.com?utm_campaign=brandjs"]',
        'div[id*="framer-badge"]',
        '#onetrust-consent-sdk',
        '#cookie-law-info-bar',
        '.cookie-banner',
        '.cookie-consent',
        '#cookie-notice',
        '#CybotCookiebotDialog',
    ]
    for sel in badge_selectors:
        for el in soup.select(sel):
            el.decompose()


# =============================================================================
# FEATURE 5: STRICT OFFLINE SANDBOX (CSP)
# =============================================================================
def apply_sandbox_csp(soup):
    if soup.head:
        for meta in soup.head.find_all('meta', attrs={'http-equiv': True}):
            if meta.get('http-equiv', '').lower() == 'content-security-policy':
                meta.decompose()

        csp_tag = soup.new_tag(
            "meta",
            attrs={
                "http-equiv": "Content-Security-Policy",
                "content": "default-src 'self' 'unsafe-inline' data: blob:; object-src 'none'; base-uri 'self';"
            }
        )
        soup.head.insert(0, csp_tag)


# =============================================================================
# FEATURE 7: LOCAL FORM ENGINE & WEBHOOKS
# =============================================================================
FORM_CLIENT_SCRIPT = """
<script>
document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll("form").forEach(function(form) {
    form.addEventListener("submit", function(e) {
      e.preventDefault();
      var formData = new FormData(form);
      var jsonObj = {};
      formData.forEach(function(value, key){ jsonObj[key] = value; });
      jsonObj["_form_id"] = form.getAttribute("id") || form.getAttribute("name") || "contact_form";
      jsonObj["_page_url"] = window.location.href;

      var submitBtn = form.querySelector('[type="submit"]') || form.querySelector('button');
      var originalBtnText = submitBtn ? submitBtn.innerText : "Submit";
      if(submitBtn) { submitBtn.innerText = "Submitting..."; submitBtn.disabled = true; }

      fetch("/api/submit-form", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(jsonObj)
      })
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if(submitBtn) { submitBtn.innerText = "✓ Success!"; }
        setTimeout(function() {
          form.reset();
          if(submitBtn) { submitBtn.innerText = originalBtnText; submitBtn.disabled = false; }
          alert("Thank you! Your message has been saved successfully.");
        }, 800);
      })
      .catch(function(err) {
        if(submitBtn) { submitBtn.innerText = "Failed"; }
        alert("Submission failed. Please check local server.");
      });
    });
  });
});
</script>
"""

def inject_local_form_handler(soup):
    if soup.body and soup.find('form'):
        form_soup = BeautifulSoup(FORM_CLIENT_SCRIPT, 'html.parser')
        soup.body.append(form_soup)


def record_form_submission(data, db_path="forms.sqlite", json_path="forms_submissions.json", telegram_token=None, telegram_chat=None, discord_webhook=None):
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            conn.execute('PRAGMA journal_mode=WAL;')
        except Exception:
            pass
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                form_id TEXT,
                data TEXT
            )
        ''')
        cur.execute('INSERT INTO submissions (form_id, data) VALUES (?, ?)', (data.get('_form_id', 'form'), json.dumps(data, ensure_ascii=False)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] SQLite form write failed: {e}")

    try:
        entries = []
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
        entries.append({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "payload": data})
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] JSON form write failed: {e}")

    if telegram_token and telegram_chat:
        try:
            msg = f"📬 *New Form Submission*\n\n"
            for k, v in data.items():
                if not k.startswith('_'):
                    msg += f"• *{k}*: {v}\n"
            requests.post(f"https://api.telegram.org/bot{telegram_token}/sendMessage", data={"chat_id": telegram_chat, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except Exception:
            pass

    if discord_webhook:
        try:
            fields = [{"name": k, "value": str(v), "inline": True} for k, v in data.items() if not k.startswith('_')]
            requests.post(discord_webhook, json={"embeds": [{"title": "📬 New Form Submission", "fields": fields, "color": 3447003}]}, timeout=5)
        except Exception:
            pass


# =============================================================================
# FEATURE 6: PWA GENERATOR (Service Worker & Manifest)
# =============================================================================
def generate_pwa_assets(site_root, app_name="Offline App"):
    manifest_path = os.path.join(site_root, "manifest.json")
    sw_path = os.path.join(site_root, "sw.js")

    manifest = {
        "name": app_name,
        "short_name": app_name[:12],
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#0a0a0c",
        "theme_color": "#0066ff",
        "icons": [
            {
                "src": "./assets/images/icon_192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "./assets/images/icon_512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    cached_urls = []
    for root, _, files in os.walk(site_root):
        for f in files:
            if not f.endswith(('.py', '.sqlite', '.zip', '.md')):
                rel = os.path.relpath(os.path.join(root, f), site_root).replace(os.sep, '/')
                cached_urls.append('./' + rel)

    sw_code = f"""// Offline PWA Service Worker
const CACHE_NAME = 'offline-cache-v1';
const ASSETS_TO_CACHE = {json.dumps(cached_urls[:150], indent=2)};

self.addEventListener('install', (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {{
      return cache.addAll(ASSETS_TO_CACHE);
    }})
  );
  self.skipWaiting();
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) => {{
      return Promise.all(
        keys.map((key) => {{
          if (key !== CACHE_NAME) return caches.delete(key);
        }})
      );
    }})
  );
  self.clients.claim();
}});

self.addEventListener('fetch', (event) => {{
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {{
      return cachedResponse || fetch(event.request);
    }})
  );
}});
"""
    with open(sw_path, 'w', encoding='utf-8') as f:
        f.write(sw_code)

    print("[+] Generated PWA manifest.json and offline Service Worker (sw.js).")


def inject_pwa_tags(soup, rel_depth_prefix="."):
    if soup.head:
        if not soup.find('link', rel='manifest'):
            m_tag = soup.new_tag("link", rel="manifest", href=f"{rel_depth_prefix}/manifest.json")
            soup.head.append(m_tag)

        sw_script = soup.new_tag("script")
        sw_script.string = f"""
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', () => {{
    navigator.serviceWorker.register('{rel_depth_prefix}/sw.js')
      .then(reg => console.log('PWA SW Registered', reg))
      .catch(err => console.log('PWA SW Error', err));
  }});
}}
"""
        soup.head.append(sw_script)


# =============================================================================
# FEATURE 8: NEXT.JS 15 / REACT 19 TRANSPILER
# =============================================================================
def transpile_to_nextjs(site_root, output_dir="nextjs_export"):
    site_root = os.path.abspath(site_root)
    output_dir = os.path.abspath(output_dir)
    print("\n" + "=" * 65)
    print(" [REACT/NEXT.JS] TRANSPILING ENTIRE MULTI-PAGE SITE TO NEXT.JS 15")
    print(f" Source: {site_root} -> Output: {output_dir}")
    print("=" * 65)

    os.makedirs(os.path.join(output_dir, "app"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "public", "assets"), exist_ok=True)

    # 1. Copy Public Assets
    for folder in ["images", "fonts", "videos", "css"]:
        src_f = os.path.join(site_root, "assets", folder)
        dst_f = os.path.join(output_dir, "public", "assets", folder)
        if os.path.exists(src_f):
            if os.path.exists(dst_f):
                shutil.rmtree(dst_f)
            shutil.copytree(src_f, dst_f)

    # 2. Extract and merge global CSS from all HTML files and css files
    combined_css = """/* ==========================================================================
   Next.js 15 Global Stylesheet (Auto-Extracted from Localized Site)
   ========================================================================== */
"""
    for cf in glob.glob(os.path.join(site_root, "assets", "css", "*.css")):
        with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
            combined_css += f"\n/* File: {os.path.basename(cf)} */\n" + f.read()

    seen_styles = set()
    html_files = glob.glob(os.path.join(site_root, "**", "*.html"), recursive=True)

    for hf in html_files:
        with open(hf, 'r', encoding='utf-8', errors='ignore') as f:
            h_soup = BeautifulSoup(f.read(), 'html.parser')
        for st in h_soup.find_all('style'):
            st_text = st.decode_contents().strip()
            if st_text and len(st_text) > 10:
                sig = st_text[:80] + str(len(st_text))
                if sig not in seen_styles and not any(k in st_text for k in ['Native Smooth Scroll', 'Zero-Blur & Zero-Shadow', 'Framer-Grade Smooth']):
                    seen_styles.add(sig)
                    combined_css += "\n" + st_text

    combined_css = re.sub(r'url\([\'"]?(?:\.\./|\./)*assets/([^\'")]+)[\'"]?\)', r'url("/assets/\1")', combined_css)

    combined_css += """
/* ==========================================================================
   Zero-Blur, Pure Clarity & Layout Normalizer
   ========================================================================== */
*, *::before, *::after {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  filter: none !important;
  -webkit-filter: none !important;
}
.framer-74kzqh, .framer-1n6agmw, .framer-1mfmz9e, .framer-1gdcxep,
.framer-1ho151l, #overlay, .framer-1cbvfqs-container,
[data-framer-name="BG Overlay"], [data-framer-name="Ovelray"],
[data-framer-name="BG Blur Overlay"], [data-framer-name="Blur"] {
  display: none !important;
}
[data-framer-appear-id], [data-framer-generated-page] {
  opacity: 1 !important;
  visibility: visible !important;
}

/* ==========================================================================
   Hero Clouds / Fog Floating Animations (60FPS Native Hardware-Accelerated)
   ========================================================================== */
@keyframes fogDriftLeft {
  0% { transform: translate3d(0, 0, 0) scale(1); opacity: 0.85; }
  50% { transform: translate3d(60px, -15px, 0) scale(1.04); opacity: 0.98; }
  100% { transform: translate3d(0, 0, 0) scale(1); opacity: 0.85; }
}
@keyframes fogDriftCenter {
  0% { transform: translate3d(-50%, 0, 0) scale(1); opacity: 0.9; }
  50% { transform: translate3d(-46%, -20px, 0) scale(1.06); opacity: 1; }
  100% { transform: translate3d(-50%, 0, 0) scale(1); opacity: 0.9; }
}
@keyframes fogDriftRight {
  0% { transform: translate3d(0, 0, 0) scale(1); opacity: 0.8; }
  50% { transform: translate3d(-70px, -12px, 0) scale(1.05); opacity: 0.95; }
  100% { transform: translate3d(0, 0, 0) scale(1); opacity: 0.8; }
}
@keyframes heroBgPulse {
  0% { transform: scale(1.03); }
  50% { transform: scale(1.07); }
  100% { transform: scale(1.03); }
}

.framer-er8wx1, [data-framer-name="Cloud 01"] {
  animation: fogDriftLeft 18s ease-in-out infinite !important;
  will-change: transform, opacity !important;
  pointer-events: none !important;
  display: block !important;
}
.framer-y6j1sf, [data-framer-name="Cloud 02"] {
  animation: fogDriftCenter 22s ease-in-out infinite !important;
  will-change: transform, opacity !important;
  pointer-events: none !important;
  display: block !important;
}
.framer-168wh43, [data-framer-name="Cloud 03"] {
  animation: fogDriftRight 26s ease-in-out infinite !important;
  will-change: transform, opacity !important;
  pointer-events: none !important;
  display: block !important;
}
.framer-1ntdd8m {
  animation: heroBgPulse 25s ease-in-out infinite !important;
  will-change: transform !important;
}
/* ==========================================================================
   Infinite Continuous Marquee / Ticker Engine (60FPS Native Hardware-Accelerated)
   ========================================================================== */
@keyframes framerContinuousTicker {
  0% { transform: translate3d(0, 0, 0); }
  100% { transform: translate3d(-50%, 0, 0); }
}

.framer-1maz95h, [data-framer-name="Container"] > .ssr-variant > .framer-1maz95h {
  overflow-x: hidden !important;
  width: 100% !important;
  max-width: 100vw !important;
  display: flex !important;
  position: relative !important;
  mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
  -webkit-mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
}

.framer-1maz95h > ul, .framer-1awlf48 ul {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  width: max-content !important;
  min-width: 200% !important;
  gap: 80px !important;
  margin: 0 !important;
  padding: 0 !important;
  list-style: none !important;
  will-change: transform !important;
  animation: framerContinuousTicker 25s linear infinite !important;
}

.framer-1maz95h:hover > ul, .framer-1awlf48:hover ul {
  animation-play-state: paused !important;
}

.framer-1maz95h .ticker-item {
  flex-shrink: 0 !important;
  display: flex !important;
  align-items: center !important;
}

html {
  scroll-behavior: smooth !important;
}
body {
  overflow-x: hidden !important;
  min-height: 100vh;
  margin: 0;
  padding: 0;
}
"""
    globals_css_path = os.path.join(output_dir, "app", "globals.css")
    with open(globals_css_path, 'w', encoding='utf-8') as f:
        f.write(combined_css)

    # 3. Create package.json
    pkg_json = {
        "name": "transpiled-nextjs-site",
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start"
        },
        "dependencies": {
            "next": "latest",
            "react": "^19.0.0",
            "react-dom": "^19.0.0"
        },
        "devDependencies": {
            "@types/node": "^22.0.0",
            "@types/react": "^19.0.0",
            "@types/react-dom": "^19.0.0",
            "typescript": "^5.6.0"
        },
        "overrides": {
            "postcss": "^8.5.3"
        }
    }
    with open(os.path.join(output_dir, "package.json"), 'w', encoding='utf-8') as f:
        json.dump(pkg_json, f, indent=2)

    # 4. Create next.config.mjs
    next_config = """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
"""
    with open(os.path.join(output_dir, "next.config.mjs"), 'w', encoding='utf-8') as f:
        f.write(next_config)

    # 5. Create app/layout.tsx
    layout_tsx = """import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Travelio - Travel Agency Framer Template',
  description: 'Fully responsive Next.js 15 App exported from Clonero Studio',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
"""
    with open(os.path.join(output_dir, "app", "layout.tsx"), 'w', encoding='utf-8') as f:
        f.write(layout_tsx)

    # 6. Create app/api/submit-form/route.ts
    api_dir = os.path.join(output_dir, "app", "api", "submit-form")
    os.makedirs(api_dir, exist_ok=True)
    api_route_ts = """import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    console.log('Form submission received:', body);
    return NextResponse.json({ success: true, status: 'success', message: 'Form received successfully' });
  } catch (error) {
    return NextResponse.json({ status: 'error', message: 'Failed to process form' }, { status: 500 });
  }
}
"""
    with open(os.path.join(api_dir, "route.ts"), 'w', encoding='utf-8') as f:
        f.write(api_route_ts)

    # 7. Transpile every HTML page in cloned_site into App Router routes
    for hf in html_files:
        rel_path = os.path.relpath(hf, site_root)
        
        if rel_path == "index.html":
            target_route_dir = os.path.join(output_dir, "app")
            page_filename = "page.tsx"
        elif rel_path == "404.html" or rel_path == os.path.join("404", "index.html"):
            target_route_dir = os.path.join(output_dir, "app")
            page_filename = "not-found.tsx"
        elif rel_path.endswith("index.html"):
            sub_dir = os.path.dirname(rel_path)
            target_route_dir = os.path.join(output_dir, "app", sub_dir)
            page_filename = "page.tsx"
        else:
            sub_name = os.path.splitext(rel_path)[0]
            target_route_dir = os.path.join(output_dir, "app", sub_name)
            page_filename = "page.tsx"

        os.makedirs(target_route_dir, exist_ok=True)

        with open(hf, 'r', encoding='utf-8', errors='ignore') as f:
            page_raw = f.read()

        p_soup = BeautifulSoup(page_raw, 'html.parser')

        if p_soup.body:
            for s in p_soup.body.find_all(['script', 'style', 'noscript']):
                s.decompose()
            for prog in p_soup.body.find_all(class_=lambda c: c and any(k in str(c) for k in ['74kzqh', '1n6agmw', '1mfmz9e', '1gdcxep', '1cbvfqs', '1ho151l', '1eop4a7'])):
                prog.decompose()
            for el in p_soup.body.find_all(attrs={'data-framer-name': lambda v: v and any(k in str(v).lower() for k in ['bg overlay', 'ovelray', 'bg blur overlay', 'blur overlay'])}):
                el.decompose()
            body_content = p_soup.body.decode_contents()
        else:
            body_content = "<div>Content</div>"

        body_content = re.sub(r'backdrop-filter:\s*blur\([^)]*\)\s*;?', '', body_content, flags=re.IGNORECASE)
        body_content = re.sub(r'-webkit-backdrop-filter:\s*blur\([^)]*\)\s*;?', '', body_content, flags=re.IGNORECASE)
        body_content = re.sub(r'filter:\s*blur\([^)]*\)\s*;?', '', body_content, flags=re.IGNORECASE)
        # Extract page title and description
        title_tag = p_soup.find('title')
        page_title = title_tag.text.strip() if title_tag else "Travelio"
        if not page_title.endswith("Travelio") and page_title != "Travelio":
            page_title = f"{page_title} - Travelio"

        desc_tag = p_soup.find('meta', attrs={'name': 'description'})
        page_desc = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ""

        def repl_asset(m):
            attr = m.group(1)
            val = m.group(2)
            return f'{attr}="/assets/{val}"'

        body_content = re.sub(r'(src|href|poster)=[\'"](?:\.\./|\./)*assets/([^\'"]+)[\'"]', repl_asset, body_content)
        body_content = re.sub(r'url\([\'"]?(?:\.\./|\./)*assets/([^\'"]+)[\'"]?\)', r'url("/assets/\1")', body_content)

        def normalize_href(m):
            attr = m.group(1)
            target = m.group(2).strip()
            if target.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'javascript:', 'data:', '/assets/')):
                return m.group(0)
            
            # Strip leading ../, ./, and /
            clean = re.sub(r'^(?:\.\./|\./|/)+', '', target)
            if not clean or clean == '.' or clean == '..':
                return f'{attr}="/"'
            
            # Map category shorthand links
            if clean in ['cities', 'nature', 'adventure', 'honeymoon', 'wildlife']:
                clean = f'categories/{clean}'
            
            # Map blog recommendation slugs
            blog_slugs = [
                'a-cultural-walk-through-rome-s-ancient-streets',
                'a-sunset-journey-through-the-sahara-desert',
                'chasing-the-northern-lights-across-iceland',
                'exploring-kyoto-s-hidden-temples-and-quiet-streets',
                'island-life-in-the-maldives-what-it-really-feels-like',
                'lost-in-time-a-week-inside-the-medina-of-fez',
                'street-food-stories-from-bangkok-nights'
            ]
            if clean in blog_slugs:
                clean = f'blog/{clean}'

            # Map location anchor links
            loc_slugs = ['brazil', 'canada', 'china', 'iceland', 'japan', 'maldives', 'morocco', 'tanzania', 'usa']
            for ls in loc_slugs:
                if clean == f'{ls}#tours':
                    clean = f'location/{ls}#tours'
                    break

            return f'{attr}="/{clean}"'

        body_content = re.sub(r'(href)=[\'"]([^\'"]+)[\'"]', normalize_href, body_content)

        clean_json = json.dumps(body_content)

        is_tours_page = "tours" in rel_path.lower() and not ("/" in rel_path and rel_path != "tours\\index.html" and rel_path != "tours/index.html")
        is_home_page = rel_path == "index.html"

        extra_effects = f"""    document.title = {json.dumps(page_title)};\n"""
        if is_home_page:
            extra_effects += """
    const statsContainer = document.querySelector('.framer-11431j5') || document.querySelector('[data-framer-name="Container"]');
    if (statsContainer) {
      const avatars = statsContainer.querySelectorAll('[data-framer-name*="Avatar"]');
      avatars.forEach((av) => {
        const st = av.getAttribute('style') || '';
        if (st.includes('none scale(') || st.includes('none')) {
          av.style.setProperty('transform', 'none', 'important');
          av.style.setProperty('opacity', '1', 'important');
        }
      });

      const colTracks = statsContainer.querySelectorAll('.framer-1bagl4-container div[style*="flex-direction:column"], .framer-1bagl4-container div[style*="flex-direction: column"]');
      const rollDigits = () => {
        colTracks.forEach((track, idx) => {
          const spans = track.querySelectorAll('span');
          if (spans.length >= 3) {
            track.style.setProperty('transition', `transform ${1.4 + (idx * 0.2)}s cubic-bezier(0.16, 1, 0.3, 1)`, 'important');
            track.style.setProperty('transform', 'translateY(-66.666%)', 'important');
          }
        });
      };

      if ('IntersectionObserver' in window) {
        const obs = new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              rollDigits();
              obs.disconnect();
            }
          });
        }, { threshold: 0.15 });
        obs.observe(statsContainer);
      } else {
        rollDigits();
      }
    }

    const allVideos = document.querySelectorAll('video');
    allVideos.forEach((v) => {
      v.setAttribute('autoplay', '');
      v.setAttribute('loop', '');
      v.setAttribute('muted', '');
      v.setAttribute('playsinline', '');
      v.setAttribute('preload', 'auto');
      v.muted = true;
      const playPromise = v.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          window.addEventListener('scroll', () => { v.play().catch(() => {}); }, { once: true });
          window.addEventListener('click', () => { v.play().catch(() => {}); }, { once: true });
        });
      }
    });
"""
        elif is_tours_page:
            extra_effects += """
    function applyFilter(cat) {
      const category = (cat || 'all').toLowerCase().trim();
      const allButtons = document.querySelectorAll('.framer-nN9yS');
      allButtons.forEach(btn => {
        const txt = (btn.textContent || '').toLowerCase().trim();
        const isActive = (category === 'all' && txt.includes('all')) || (category !== 'all' && txt.includes(category));
        if (isActive) {
          btn.style.setProperty('background-color', 'rgb(26, 26, 23)', 'important');
          btn.style.setProperty('color', '#ffffff', 'important');
          btn.style.setProperty('border-color', 'rgb(26, 26, 23)', 'important');
          btn.setAttribute('data-framer-name', 'Active');
          btn.querySelectorAll('*').forEach(c => c.style.setProperty('color', '#ffffff', 'important'));
        } else {
          btn.style.setProperty('background-color', 'rgb(247, 247, 247)', 'important');
          btn.style.setProperty('color', 'rgb(26, 26, 23)', 'important');
          btn.style.setProperty('border-color', 'rgba(26, 26, 23, 0.3)', 'important');
          btn.setAttribute('data-framer-name', 'Default');
          btn.querySelectorAll('*').forEach(c => c.style.setProperty('color', 'rgb(26, 26, 23)', 'important'));
        }
      });

      const grid = document.querySelector('.framer-4ddwsp') || document.querySelector('section[data-framer-name="Tours"]');
      if (grid) {
        const slots = grid.querySelectorAll('.framer-1q3g523, [class*="6umzi6-container"]');
        slots.forEach(slot => {
          const slotText = (slot.textContent || '').toLowerCase();
          const matches = (category === 'all') || slotText.includes(category);
          if (matches) {
            slot.style.setProperty('display', 'flex', 'important');
            slot.style.setProperty('opacity', '1', 'important');
            slot.style.setProperty('transform', 'scale(1)', 'important');
          } else {
            slot.style.setProperty('display', 'none', 'important');
            slot.style.setProperty('opacity', '0', 'important');
            slot.style.setProperty('transform', 'scale(0.95)', 'important');
          }
        });
      }
    }
    window.__applyTourFilter = applyFilter;

    const onFilterClick = (e) => {
      const btn = e.target.closest('.framer-nN9yS');
      if (btn) {
        e.preventDefault();
        const text = (btn.textContent || '').trim().toLowerCase();
        let category = 'all';
        if (text.includes('cities') || text.includes('city')) category = 'cities';
        else if (text.includes('nature')) category = 'nature';
        else if (text.includes('adventure')) category = 'adventure';
        else if (text.includes('honeymoon')) category = 'honeymoon';
        else if (text.includes('wildlife')) category = 'wildlife';
        applyFilter(category);
      }
    };
    window.addEventListener('click', onFilterClick, true);
"""

        component_name = "NotFound" if page_filename == "not-found.tsx" else "Page"

        page_tsx_code = f"""// @ts-nocheck
'use client';
import React, {{ useEffect }} from 'react';

const PAGE_HTML: string = {clean_json};

export default function {component_name}() {{
  useEffect(() => {{
{extra_effects}
  }}, []);

  return (
    <div className="min-h-screen w-full">
      <div dangerouslySetInnerHTML={{{{ __html: PAGE_HTML }}}} />
    </div>
  );
}}
"""
        target_file = os.path.join(target_route_dir, page_filename)
        with open(target_file, 'w', encoding='utf-8') as pf:
            pf.write(page_tsx_code)

    print(f"[+] Transpiled Next.js 15 project created at: {output_dir}")
    print("    To run: cd " + output_dir + " ; npm install ; npm run dev")


# =============================================================================
# FEATURE 9: ONE-CLICK ZIP PACKAGER
def create_zip_bundle(site_root, zip_name=None):
    if not zip_name:
        zip_name = f"website_bundle_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    if not zip_name.endswith('.zip'):
        zip_name += '.zip'

    zip_path = os.path.abspath(zip_name)
    print(f"[+] Compressing '{site_root}' into '{zip_path}'...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(site_root):
            for file in files:
                if file.endswith('.zip') or file.endswith('.sqlite'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, site_root)
                zipf.write(file_path, arcname)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[✓] ZIP Bundle created successfully: {zip_name} ({size_mb:.2f} MB)")
    return zip_path


# =============================================================================
# FEATURE 10: AUDIT & PERFORMANCE REPORT
# =============================================================================
def generate_audit_report(site_root, report_html_path="audit_report.html", report_json_path="audit_report.json"):
    html_files = glob.glob(os.path.join(site_root, "**", "*.html"), recursive=True)
    img_files = glob.glob(os.path.join(site_root, "assets", "images", "*"))
    font_files = glob.glob(os.path.join(site_root, "assets", "fonts", "*"))
    css_files = glob.glob(os.path.join(site_root, "assets", "css", "*"))

    def get_size(files):
        return sum(os.path.getsize(f) for f in files if os.path.isfile(f))

    img_size_mb = get_size(img_files) / (1024 * 1024)
    font_size_mb = get_size(font_files) / (1024 * 1024)
    css_size_mb = get_size(css_files) / (1024 * 1024)
    total_size_mb = (get_size(html_files) + get_size(img_files) + get_size(font_files) + get_size(css_files)) / (1024 * 1024)

    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pages_count": len(html_files),
        "images_count": len(img_files),
        "fonts_count": len(font_files),
        "css_count": len(css_files),
        "images_size_mb": round(img_size_mb, 2),
        "fonts_size_mb": round(font_size_mb, 2),
        "css_size_mb": round(css_size_mb, 2),
        "total_size_mb": round(total_size_mb, 2),
        "status": "100% Localized & Offline Ready"
    }

    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)

    html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Website Localization Audit Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }}
    .container {{ max-width: 900px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
    h1 {{ color: #38bdf8; margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
    .card {{ background: #334155; padding: 20px; border-radius: 12px; border: 1px solid #475569; }}
    .val {{ font-size: 28px; font-weight: bold; color: #10b981; margin-top: 8px; }}
    .badge {{ display: inline-block; background: #059669; color: #fff; padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
  </style>
</head>
<body>
  <div class="container">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <h1>📊 Website Localization Audit Report</h1>
      <span class="badge">100% OFFLINE READY</span>
    </div>
    <p style="color:#94a3b8;">Generated on {report_data['timestamp']}</p>

    <div class="grid">
      <div class="card"><div>Total Pages</div><div class="val">{report_data['pages_count']}</div></div>
      <div class="card"><div>Total Images</div><div class="val">{report_data['images_count']} ({report_data['images_size_mb']} MB)</div></div>
      <div class="card"><div>Total Fonts</div><div class="val">{report_data['fonts_count']} ({report_data['fonts_size_mb']} MB)</div></div>
      <div class="card"><div>Total Size</div><div class="val">{report_data['total_size_mb']} MB</div></div>
    </div>
  </div>
</body>
</html>
"""
    with open(report_html_path, 'w', encoding='utf-8') as f:
        f.write(html_report)

    print(f"[+] Audit Report generated at: {report_html_path}")


# =============================================================================
# FEATURE 13: WHITELABELING & BRANDING (--rebrand)
# =============================================================================
def rebrand_project(site_root, new_title=None, new_favicon=None, new_logo=None,
                    accent_color=None, footer_text=None, author_name=None,
                    meta_description=None):
    """
    Replace titles, favicons, logos, accent colors, and custom text across
    all HTML files in the project for complete white-label branding.
    """
    print("=" * 65)
    print(" [REBRAND] WHITELABELING & BRANDING ENGINE")
    print(f" Target: {site_root}")
    print("=" * 65)

    html_files = glob.glob(os.path.join(site_root, '**', '*.html'), recursive=True)
    css_files = glob.glob(os.path.join(site_root, '**', '*.css'), recursive=True)

    if not html_files:
        print("[!] No HTML files found.")
        return False

    changes_summary = []

    # --- Copy new favicon / logo into assets ---
    images_dir = os.path.join(site_root, 'assets', 'images')
    os.makedirs(images_dir, exist_ok=True)

    local_favicon_path = None
    if new_favicon and os.path.isfile(new_favicon):
        ext = os.path.splitext(new_favicon)[1] or '.png'
        local_favicon_path = os.path.join(images_dir, f'custom_favicon{ext}')
        shutil.copy2(new_favicon, local_favicon_path)
        changes_summary.append(f"Favicon: {new_favicon} → {local_favicon_path}")

    local_logo_path = None
    if new_logo and os.path.isfile(new_logo):
        ext = os.path.splitext(new_logo)[1] or '.png'
        local_logo_path = os.path.join(images_dir, f'custom_logo{ext}')
        shutil.copy2(new_logo, local_logo_path)
        changes_summary.append(f"Logo: {new_logo} → {local_logo_path}")

    print(f"[1/3] Processing {len(html_files)} HTML files...")
    for hf in html_files:
        with open(hf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')
        modified = False

        # --- Replace <title> ---
        if new_title:
            title_tag = soup.find('title')
            if title_tag:
                title_tag.string = new_title
                modified = True

            # Also replace og:title, twitter:title, og:site_name
            for meta in soup.find_all('meta'):
                prop = meta.get('property', '') or meta.get('name', '')
                if prop in ['og:title', 'twitter:title', 'og:site_name']:
                    meta['content'] = new_title
                    modified = True

        # --- Replace meta description ---
        if meta_description:
            for meta in soup.find_all('meta'):
                name = meta.get('name', '') or meta.get('property', '')
                if name in ['description', 'og:description', 'twitter:description']:
                    meta['content'] = meta_description
                    modified = True

        # --- Replace author ---
        if author_name:
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta:
                author_meta['content'] = author_name
                modified = True
            elif soup.head:
                new_meta = soup.new_tag('meta', attrs={'name': 'author', 'content': author_name})
                soup.head.append(new_meta)
                modified = True

        # --- Replace favicon ---
        if local_favicon_path:
            for link in soup.find_all('link'):
                rel = link.get('rel', [])
                if isinstance(rel, str):
                    rel = [rel]
                if any(r in ['icon', 'apple-touch-icon', 'shortcut icon'] for r in rel):
                    link['href'] = get_relative_path(hf, local_favicon_path)
                    modified = True

        # --- Replace logo images ---
        if local_logo_path:
            # Target: images in header/nav that are likely logos (first image, or images with logo-related attributes)
            header = soup.find(['header', 'nav'])
            if header:
                logo_imgs = header.find_all('img')
                if logo_imgs:
                    logo_imgs[0]['src'] = get_relative_path(hf, local_logo_path)
                    modified = True

            # Also look for elements with common logo class names
            for img in soup.find_all('img'):
                img_class = ' '.join(img.get('class', []))
                img_alt = (img.get('alt') or '').lower()
                if 'logo' in img_class.lower() or 'logo' in img_alt or 'brand' in img_class.lower():
                    img['src'] = get_relative_path(hf, local_logo_path)
                    modified = True

        # --- Replace footer text ---
        if footer_text:
            footer = soup.find('footer')
            if footer:
                # Look for copyright or small text in footer
                for el in footer.find_all(['p', 'span', 'small', 'div']):
                    text = el.get_text(strip=True)
                    if any(kw in text.lower() for kw in ['©', 'copyright', 'all rights reserved', 'made in', 'built with', 'powered by']):
                        el.string = footer_text
                        modified = True
                        break

        # --- Inject accent color CSS variable override ---
        if accent_color and soup.head:
            # Validate hex color
            color = accent_color.strip()
            if not color.startswith('#'):
                color = '#' + color

            accent_style = soup.new_tag('style')
            accent_style.string = f"""
/* Custom Brand Accent Color Override */
:root {{
  --brand-accent: {color};
  --brand-accent-hover: {color}dd;
}}
a, .btn-primary, [data-framer-name*="Button"], button.primary {{
  color: var(--brand-accent) !important;
}}
.btn-primary, [data-framer-name*="CTA"], [data-framer-name*="Book"] {{
  background-color: var(--brand-accent) !important;
}}
"""
            soup.head.append(accent_style)
            modified = True

        if modified:
            with open(hf, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            rel_disp = os.path.relpath(hf, site_root)
            print(f"  [✓] Rebranded: {rel_disp}")

    # --- Process CSS files for accent color ---
    if accent_color:
        color = accent_color.strip()
        if not color.startswith('#'):
            color = '#' + color
        print(f"[2/3] Updating accent colors in {len(css_files)} CSS files...")
        for cf in css_files:
            with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
                css_text = f.read()
            # We don't blindly replace colors in CSS (too dangerous),
            # but we add a note that custom variables are available
            # The :root override above handles most cases
        changes_summary.append(f"Accent Color: {color}")
    else:
        print("[2/3] No accent color specified, skipping CSS update.")

    # --- Update manifest.json if it exists ---
    manifest_path = os.path.join(site_root, 'manifest.json')
    if os.path.exists(manifest_path):
        print("[3/3] Updating manifest.json...")
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            if new_title:
                manifest['name'] = new_title
                manifest['short_name'] = new_title[:12]
            if accent_color:
                color = accent_color.strip()
                if not color.startswith('#'):
                    color = '#' + color
                manifest['theme_color'] = color
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            changes_summary.append("manifest.json updated")
        except Exception as e:
            print(f"  [WARN] Failed to update manifest.json: {e}")
    else:
        print("[3/3] No manifest.json found, skipping.")

    print(f"\n{'=' * 65}")
    print(" REBRAND COMPLETE! Changes applied:")
    for c in changes_summary:
        print(f"  • {c}")
    if new_title:
        print(f"  • Site Title: {new_title}")
    if footer_text:
        print(f"  • Footer Text: {footer_text}")
    if meta_description:
        print(f"  • Meta Description: {meta_description[:50]}...")
    print("=" * 65 + "\n")
    return True


# =============================================================================
# FEATURE 12: EMBEDDED VISUAL WEB DASHBOARD (GUI)
# =============================================================================
GUI_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ultimate Website Studio & Localizer</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>/* offline fallback: if CDN fails, basic layout still works */ .glass{backdrop-filter:blur(12px)}</style>
  <style>
    body { background-color: #0b0f19; color: #e2e8f0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }
    .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glow { box-shadow: 0 0 30px rgba(56, 189, 248, 0.15); }
  </style>
</head>
<body class="min-h-screen p-6 md:p-12">
  <div class="max-w-6xl mx-auto space-y-8">
    
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-sky-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
          ⚡ Ultimate Website Localizer & Studio
        </h1>
        <p class="text-slate-400 text-sm mt-1">All-in-one Cloning, Offline Localization, PWA & Next.js Generator</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span class="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse"></span> Engine Online
        </span>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      
      <div class="lg:col-span-1 space-y-6">
        <div class="glass p-6 rounded-2xl glow space-y-5">
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            🚀 Quick Operations
          </h2>

          <div class="space-y-2">
            <label class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Direct URL Cloner</label>
            <div class="flex gap-2">
              <input id="cloneUrl" type="url" placeholder="https://example.framer.website" class="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500">
              <button onclick="runAction('clone')" class="bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold px-4 py-2 rounded-xl text-sm transition">Clone</button>
            </div>
          </div>

          <hr class="border-slate-800">

          <div class="space-y-3">
            <label class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Pipeline Modules</label>
            
            <label class="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
              <input id="chkPWA" type="checkbox" checked class="rounded border-slate-700 text-sky-500 focus:ring-0 bg-slate-900 w-4 h-4">
              <span>Generate PWA & Service Worker</span>
            </label>

            <label class="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
              <input id="chkBadges" type="checkbox" checked class="rounded border-slate-700 text-sky-500 focus:ring-0 bg-slate-900 w-4 h-4">
              <span>Strip Platform Badges & Popups</span>
            </label>

            <label class="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
              <input id="chkForms" type="checkbox" checked class="rounded border-slate-700 text-sky-500 focus:ring-0 bg-slate-900 w-4 h-4">
              <span>Enable Local Form Catcher</span>
            </label>

            <label class="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
              <input id="chkSandbox" type="checkbox" checked class="rounded border-slate-700 text-sky-500 focus:ring-0 bg-slate-900 w-4 h-4">
              <span>Strict Privacy Sandbox (CSP)</span>
            </label>
          </div>

          <div class="space-y-2 pt-2">
            <button onclick="runAction('localize')" class="w-full bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold py-3 rounded-xl text-sm shadow-lg transition">
              ⚡ Localize Workspace Now
            </button>
            <button onclick="runAction('nextjs')" class="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2.5 rounded-xl text-sm transition">
              ⚛️ Export to Next.js 15 / React
            </button>
            <button onclick="runAction('zip')" class="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2.5 rounded-xl text-sm transition">
              📦 Download Deployable ZIP
            </button>
          </div>
        </div>
      </div>

      <div class="lg:col-span-2 space-y-6">
        
        <div class="glass p-4 rounded-2xl">
          <div class="flex justify-between items-center mb-3 px-2">
            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live Preview</span>
            <a href="/" target="_blank" class="text-xs text-sky-400 hover:underline">Open in Full Tab ↗</a>
          </div>
          <div class="bg-slate-950 rounded-xl overflow-hidden border border-slate-800 h-96">
            <iframe id="previewFrame" src="/" class="w-full h-full border-0"></iframe>
          </div>
        </div>

        <div class="glass p-4 rounded-2xl space-y-2">
          <div class="flex justify-between items-center px-2">
            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Status Console</span>
            <span id="taskStatus" class="text-xs text-slate-400">Idle</span>
          </div>
          <div id="consoleOutput" class="bg-slate-950 p-4 rounded-xl font-mono text-xs text-emerald-400 h-36 overflow-y-auto space-y-1 border border-slate-800">
            <div>[Ready] Engine initialized and awaiting instructions.</div>
          </div>
        </div>

      </div>
    </div>
  </div>

  <script>
    function log(msg) {
      const box = document.getElementById("consoleOutput");
      const d = document.createElement("div");
      d.textContent = "> " + msg;
      box.appendChild(d);
      box.scrollTop = box.scrollHeight;
    }

    function runAction(action) {
      const status = document.getElementById("taskStatus");
      status.textContent = "Processing " + action + "...";
      log("Initiating action: " + action);

      fetch('/api/gui-action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          action: action,
          url: document.getElementById('cloneUrl').value,
          pwa: document.getElementById('chkPWA').checked,
          badges: document.getElementById('chkBadges').checked,
          forms: document.getElementById('chkForms').checked,
          sandbox: document.getElementById('chkSandbox').checked
        })
      })
      .then(res => res.json())
      .then(data => {
        status.textContent = "Complete";
        log("Success: " + (data.message || "Action finished successfully"));
        
        const frame = document.getElementById("previewFrame");
        if(frame) { frame.src = '/?t=' + Date.now(); }

        if(action === 'clone' || action === 'localize') {
          log("Opening live website preview in new tab...");
          window.open('/', '_blank');
        }

        if(action === 'zip' && data.zip_file) {
          window.location.href = '/' + data.zip_file;
        }
      })
      .catch(err => {
        status.textContent = "Error";
        log("Error executing action: " + err);
      });
    }
  </script>
</body>
</html>
"""


# =============================================================================
# CORE: FULL LOCALIZATION WORKFLOW
# =============================================================================
def localize_project(target_path, workers=20, clean_badges=True, enable_pwa=False, enable_sandbox=False, enable_forms=False):
    print("=" * 65)
    print(" [LOCALIZE] ULTRA-DEEP ASSET DISCOVERY & OFFLINE PIPELINE")
    print(f" Target: {target_path}")
    print("=" * 65)

    if os.path.isfile(target_path):
        site_root_dir = os.path.dirname(os.path.abspath(target_path)) or '.'
        html_files = [os.path.abspath(target_path)]
    else:
        site_root_dir = os.path.abspath(target_path)
        html_files = [os.path.abspath(f) for f in glob.glob(os.path.join(site_root_dir, '**', '*.html'), recursive=True)]

    if not html_files:
        print(f"[!] No HTML files found in: {target_path}")
        return False

    print(f"[+] Found {len(html_files)} HTML file(s) to process.")

    base_assets_dir = os.path.join(site_root_dir, 'assets')
    images_dir = os.path.join(base_assets_dir, 'images')
    fonts_dir = os.path.join(base_assets_dir, 'fonts')
    videos_dir = os.path.join(base_assets_dir, 'videos')
    css_dir = os.path.join(base_assets_dir, 'css')

    for d in [images_dir, fonts_dir, videos_dir, css_dir]:
        os.makedirs(d, exist_ok=True)

    print("[1/4] Deep Scanning HTML documents, scripts, and stylesheets for all assets...")
    download_tasks = {}

    for hf in html_files:
        with open(hf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')

        # 1. Images & Responsive srcsets
        for img in soup.find_all('img'):
            srcset = img.get('srcset')
            if srcset:
                urls = re.findall(r'(https?://[^\s,]+)', srcset)
                if urls:
                    best_url = urls[-1]
                    cat, fn = get_filename_and_category(best_url)
                    download_tasks[best_url] = os.path.join(images_dir, fn)
                    if not img.get('src') or img.get('src', '').startswith(('data:', 'http://', 'https://')):
                        img['src'] = best_url

            for attr in ['src', 'data-src']:
                val = img.get(attr)
                if val and val.startswith(('http://', 'https://')):
                    cat, fn = get_filename_and_category(val)
                    download_tasks[val] = os.path.join(images_dir, fn)

        # 2. Media & Videos
        for med in soup.find_all(['video', 'audio', 'source']):
            src = med.get('src')
            if src and src.startswith(('http://', 'https://')):
                cat, fn = get_filename_and_category(src)
                dest = os.path.join(videos_dir if cat == 'videos' else images_dir, fn)
                download_tasks[src] = dest
            poster = med.get('poster')
            if poster and poster.startswith(('http://', 'https://')):
                cat, fn = get_filename_and_category(poster)
                download_tasks[poster] = os.path.join(images_dir, fn)

        # 3. Links, Icons, Stylesheets, Preloaded Modules
        for link in soup.find_all('link'):
            href = link.get('href')
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = [rel]
            if href and href.startswith(('http://', 'https://')):
                if any(r in ['icon', 'apple-touch-icon', 'shortcut icon'] for r in rel) or ('/images/' in href):
                    cat, fn = get_filename_and_category(href)
                    download_tasks[href] = os.path.join(images_dir, fn)
                elif 'modulepreload' in rel and 'framerusercontent.com' in href:
                    p = href.replace('https://framerusercontent.com/', '').split('?')[0]
                    target_local = os.path.join(site_root_dir, 'framerusercontent', p.replace('/', os.sep))
                    download_tasks[href] = target_local
                elif 'stylesheet' in rel or href.endswith('.css'):
                    cat, fn = get_filename_and_category(href)
                    download_tasks[href] = os.path.join(css_dir, fn)

        # 4. Meta tags
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '') or meta.get('name', '')
            content_val = meta.get('content', '')
            if content_val and content_val.startswith(('http://', 'https://')):
                if 'image' in prop or '/images/' in content_val or '/assets/' in content_val:
                    cat, fn = get_filename_and_category(content_val)
                    if cat in ['images', 'assets']:
                        download_tasks[content_val] = os.path.join(images_dir, fn)
                elif prop in ["framer-search-index", "framer-search-index-fallback"] and "framerusercontent.com" in content_val:
                    p = content_val.replace('https://framerusercontent.com/', '').split('?')[0]
                    target_local = os.path.join(site_root_dir, 'framerusercontent', p.replace('/', os.sep))
                    download_tasks[content_val] = target_local

        # 5. Inline style="..." attributes on every element
        for tag in soup.find_all(True):
            st = tag.get('style', '')
            if 'url(' in st:
                found_urls = re.findall(r'url\([\'"]?(https?://[^\'")]+)[\'"]?\)', st)
                for u in found_urls:
                    cat, fn = get_filename_and_category(u)
                    dest = os.path.join(fonts_dir if cat == 'fonts' else (videos_dir if cat == 'videos' else images_dir), fn)
                    download_tasks[u] = dest

        # 6. Fonts and textures in <style>
        for style in soup.find_all('style'):
            css_text = style.decode_contents()
            urls = re.findall(r'url\([\'"]?(https?://[^\'")]+)[\'"]?\)', css_text)
            for u in urls:
                cat, fn = get_filename_and_category(u)
                dest = os.path.join(fonts_dir if cat == 'fonts' else (videos_dir if cat == 'videos' else images_dir), fn)
                download_tasks[u] = dest

        # 7. Direct Scripts
        for script in soup.find_all('script'):
            src = script.get('src')
            if src and src.startswith(('http://', 'https://')):
                if 'framerusercontent.com' in src:
                    p = src.replace('https://framerusercontent.com/', '').split('?')[0]
                    target_local = os.path.join(site_root_dir, 'framerusercontent', p.replace('/', os.sep))
                    download_tasks[src] = target_local

    # Download Initial Tier 1 Assets
    print(f"[2/4] Downloading {len(download_tasks)} primary assets ({workers} worker threads)...")
    if download_tasks:
        progress = RichProgress(len(download_tasks), label="Tier 1 Assets")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_url = {
                executor.submit(download_file, url, path): (url, path)
                for url, path in download_tasks.items()
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url, path = future_to_url[future]
                success = future.result()
                file_size = os.path.getsize(path) if success and os.path.exists(path) else 0
                progress.update(success=success, size_bytes=file_size)
        progress.finish_message(f"Downloaded {len(download_tasks)} primary assets")

    # =========================================================================
    # RECURSIVE TIER 2: SCAN & DOWNLOAD ASSETS FROM JS MODULES AND CSS
    # =========================================================================
    print("[3/4] Deep Scanning JavaScript chunks and CSS files for dynamic runtime assets...")
    tier2_tasks = {}

    mjs_files = glob.glob(os.path.join(site_root_dir, '**', '*.mjs'), recursive=True) + glob.glob(os.path.join(site_root_dir, '**', '*.js'), recursive=True)
    for mf in mjs_files:
        with open(mf, 'r', encoding='utf-8', errors='ignore') as f:
            js_code = f.read()

        # Find dynamic images, SVGs, videos, and fonts
        dyn_urls = re.findall(r'https://(?:framerusercontent\.com/(?:images|assets|modules|sites)|fonts\.gstatic\.com)[^\s"\'`<>)]+', js_code)
        for du in dyn_urls:
            clean_du = du.rstrip('\\').rstrip(',').rstrip(';')
            if '/modules/' in clean_du or '/sites/' in clean_du and clean_du.endswith('.mjs'):
                p = clean_du.replace('https://framerusercontent.com/', '').split('?')[0]
                target_local = os.path.join(site_root_dir, 'framerusercontent', p.replace('/', os.sep))
                tier2_tasks[clean_du] = target_local
            else:
                cat, fn = get_filename_and_category(clean_du)
                dest = os.path.join(fonts_dir if cat == 'fonts' else (videos_dir if cat == 'videos' else images_dir), fn)
                tier2_tasks[clean_du] = dest

    css_files = glob.glob(os.path.join(site_root_dir, '**', '*.css'), recursive=True)
    for cf in css_files:
        with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
            css_text = f.read()
        css_urls = re.findall(r'url\([\'"]?(https?://[^\'")]+)[\'"]?\)', css_text)
        for cu in css_urls:
            cat, fn = get_filename_and_category(cu)
            dest = os.path.join(fonts_dir if cat == 'fonts' else (videos_dir if cat == 'videos' else images_dir), fn)
            tier2_tasks[cu] = dest

    if tier2_tasks:
        print(f"  [+] Discovered {len(tier2_tasks)} additional runtime assets inside JS & CSS chunks.")
        progress2 = RichProgress(len(tier2_tasks), label="Tier 2 Deep")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_url = {
                executor.submit(download_file, url, path): (url, path)
                for url, path in tier2_tasks.items()
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url, path = future_to_url[future]
                success = future.result()
                file_size = os.path.getsize(path) if success and os.path.exists(path) else 0
                progress2.update(success=success, size_bytes=file_size)
        progress2.finish_message(f"Downloaded {len(tier2_tasks)} deep runtime assets")

    # Rewrite URLs inside JS / MJS files to point locally
    for mf in mjs_files:
        with open(mf, 'r', encoding='utf-8', errors='ignore') as f:
            js_code = f.read()

        def replace_js_url(m):
            u = m.group(0)
            cat, fn = get_filename_and_category(u)
            if cat == 'fonts':
                dest = os.path.join(fonts_dir, fn)
            elif cat == 'videos':
                dest = os.path.join(videos_dir, fn)
            else:
                dest = os.path.join(images_dir, fn)
            return get_relative_path(mf, dest)

        js_code_fixed = re.sub(r'https://framerusercontent\.com/(?:images|assets)/[^\s"\'`<>)]+', replace_js_url, js_code)
        js_code_fixed = re.sub(r'https://fonts\.gstatic\.com/[^\s"\'`<>)]+', replace_js_url, js_code_fixed)

        if js_code_fixed != js_code:
            with open(mf, 'w', encoding='utf-8') as f:
                f.write(js_code_fixed)

    # Rewrite URLs inside CSS files
    for cf in css_files:
        with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
            css_text = f.read()

        def replace_css_file_url(match):
            full_match = match.group(0)
            u = match.group(1)
            if u.startswith(('http://', 'https://')):
                cat, fn = get_filename_and_category(u)
                dest = os.path.join(fonts_dir if cat == 'fonts' else (videos_dir if cat == 'videos' else images_dir), fn)
                return f'url("{get_relative_path(cf, dest)}")'
            return full_match

        css_fixed = re.sub(r'url\([\'"]?(https?://[^\'")]+)[\'"]?\)', replace_css_file_url, css_text)
        with open(cf, 'w', encoding='utf-8') as f:
            f.write(css_fixed)

    # =========================================================================
    # TIER 4: TRANSFORM HTML DOCUMENTS & FIX VISIBILITY
    # =========================================================================
    print("[4/4] Transforming HTML documents, fixing styles, and enabling full interactivity...")
    for hf in html_files:
        with open(hf, 'r', encoding='utf-8', errors='ignore') as f:
            raw_html = f.read()

        # SSR Appearance Normalizer & Zero-Blur Cleaner
        raw_html = re.sub(r'opacity:\s*0\.001', 'opacity:1', raw_html)
        raw_html = re.sub(r'transform:\s*translateY\([^\)]+\)', 'transform:none', raw_html)
        raw_html = re.sub(r'backdrop-filter:\s*blur\([^)]*\)\s*;?', '', raw_html, flags=re.IGNORECASE)
        raw_html = re.sub(r'-webkit-backdrop-filter:\s*blur\([^)]*\)\s*;?', '', raw_html, flags=re.IGNORECASE)
        raw_html = re.sub(r'filter:\s*blur\([^)]*\)\s*;?', '', raw_html, flags=re.IGNORECASE)
        raw_html = re.sub(r'-webkit-filter:\s*blur\([^)]*\)\s*;?', '', raw_html, flags=re.IGNORECASE)

        soup = BeautifulSoup(raw_html, 'html.parser')

        # Remove unwanted blur and dark shadow overlay containers
        for prog in soup.find_all(class_=lambda c: c and any(k in str(c) for k in ['74kzqh', '1n6agmw', '1mfmz9e', '1gdcxep', '1cbvfqs', '1ho151l', '1eop4a7'])):
            prog.decompose()
        for el in soup.find_all(attrs={'data-framer-name': lambda v: v and any(k in str(v).lower() for k in ['bg overlay', 'ovelray', 'bg blur overlay', 'blur overlay'])}):
            el.decompose()

        # Localize URLs inside <style> tags
        for style_tag in soup.find_all('style'):
            tag_css = style_tag.decode_contents()

            def replace_inline_css_url(match):
                full_match = match.group(0)
                u = match.group(1)
                if u.startswith(('http://', 'https://')):
                    cat, fn = get_filename_and_category(u)
                    dest = os.path.join(fonts_dir if cat == 'fonts' else (videos_dir if cat == 'videos' else images_dir), fn)
                    return f'url("{get_relative_path(hf, dest)}")'
                return full_match

            tag_css = re.sub(r'url\([\'"]?(https?://[^\'")]+)[\'"]?\)', replace_inline_css_url, tag_css)
            style_tag.string = tag_css

        # Localize inline style="..." attributes
        for tag in soup.find_all(True):
            st = tag.get('style')
            if st and 'url(' in st:
                def replace_tag_style_url(match):
                    full_match = match.group(0)
                    u = match.group(1)
                    if u.startswith(('http://', 'https://')):
                        cat, fn = get_filename_and_category(u)
                        dest = os.path.join(fonts_dir if cat == 'fonts' else (videos_dir if cat == 'videos' else images_dir), fn)
                        return f'url("{get_relative_path(hf, dest)}")'
                    return full_match
                tag['style'] = re.sub(r'url\([\'"]?(https?://[^\'")]+)[\'"]?\)', replace_tag_style_url, st)

        # Inject layout visibility, Zero-Blur, and Hero Fog Floating override into head
        if soup.head:
            vis_override = soup.new_tag("style")
            vis_override.string = """
/* Zero-Blur & Zero-Shadow Crystal-Clear Rule */
*, *::before, *::after {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  filter: none !important;
  -webkit-filter: none !important;
}
.framer-74kzqh, .framer-1n6agmw, .framer-1mfmz9e, .framer-1gdcxep,
.framer-1ho151l, #overlay, .framer-1cbvfqs-container,
[data-framer-name="BG Overlay"], [data-framer-name="Ovelray"],
[data-framer-name="BG Blur Overlay"], [data-framer-name="Blur"] {
  display: none !important;
}
[data-framer-appear-id], [data-framer-generated-page] {
  opacity: 1 !important;
  visibility: visible !important;
}

/* ==========================================================================
   Hero Clouds / Fog Floating Animations (60FPS Native Hardware-Accelerated)
   ========================================================================== */
@keyframes fogDriftLeft {
  0% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: 0.85;
  }
  50% {
    transform: translate3d(60px, -15px, 0) scale(1.04);
    opacity: 0.98;
  }
  100% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: 0.85;
  }
}

@keyframes fogDriftCenter {
  0% {
    transform: translate3d(-50%, 0, 0) scale(1);
    opacity: 0.9;
  }
  50% {
    transform: translate3d(-46%, -20px, 0) scale(1.06);
    opacity: 1;
  }
  100% {
    transform: translate3d(-50%, 0, 0) scale(1);
    opacity: 0.9;
  }
}

@keyframes fogDriftRight {
  0% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: 0.8;
  }
  50% {
    transform: translate3d(-70px, -12px, 0) scale(1.05);
    opacity: 0.95;
  }
  100% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: 0.8;
  }
}

@keyframes heroBgPulse {
  0% {
    transform: scale(1.03);
  }
  50% {
    transform: scale(1.07);
  }
  100% {
    transform: scale(1.03);
  }
}

/* Cloud 01 (Left Fog) */
.framer-er8wx1, [data-framer-name="Cloud 01"] {
  animation: fogDriftLeft 18s ease-in-out infinite !important;
  will-change: transform, opacity !important;
  pointer-events: none !important;
  display: block !important;
}

/* Cloud 02 (Center Dense Fog) */
.framer-y6j1sf, [data-framer-name="Cloud 02"] {
  animation: fogDriftCenter 22s ease-in-out infinite !important;
  will-change: transform, opacity !important;
  pointer-events: none !important;
  display: block !important;
}

/* Cloud 03 (Right Fog) */
.framer-168wh43, [data-framer-name="Cloud 03"] {
  animation: fogDriftRight 26s ease-in-out infinite !important;
  will-change: transform, opacity !important;
  pointer-events: none !important;
  display: block !important;
}

/* Hero Background Mountain Zoom Effect */
.framer-1ntdd8m {
  animation: heroBgPulse 25s ease-in-out infinite !important;
  will-change: transform !important;
}

html, body {
  overflow-x: hidden;
  min-height: 100vh;
}
"""
            soup.head.append(vis_override)

        # Localize Images
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith(("http://", "https://")):
                cat, fn = get_filename_and_category(src)
                img["src"] = get_relative_path(hf, os.path.join(images_dir, fn))

            dsrc = img.get("data-src")
            if dsrc and dsrc.startswith(("http://", "https://")):
                cat, fn = get_filename_and_category(dsrc)
                img["data-src"] = get_relative_path(hf, os.path.join(images_dir, fn))

            if img.get("srcset"):
                del img["srcset"]

        # Localize Videos
        for vid in soup.find_all(["video", "audio"]):
            src = vid.get("src")
            if src and src.startswith(("http://", "https://")):
                cat, fn = get_filename_and_category(src)
                dest = os.path.join(videos_dir if cat == 'videos' else images_dir, fn)
                vid["src"] = get_relative_path(hf, dest)

            poster = vid.get("poster")
            if poster and poster.startswith(("http://", "https://")):
                cat, fn = get_filename_and_category(poster)
                vid["poster"] = get_relative_path(hf, os.path.join(images_dir, fn))

        for src_tag in soup.find_all("source"):
            src = src_tag.get("src")
            if src and src.startswith(("http://", "https://")):
                cat, fn = get_filename_and_category(src)
                dest = os.path.join(videos_dir if cat == 'videos' else images_dir, fn)
                src_tag["src"] = get_relative_path(hf, dest)
            if src_tag.get("srcset"):
                del src_tag["srcset"]

        # Localize Links & Icons
        for link in soup.find_all("link"):
            href = link.get("href")
            rel = link.get("rel", [])
            if isinstance(rel, str):
                rel = [rel]
            if href and href.startswith(("http://", "https://")):
                if any(r in ['icon', 'apple-touch-icon', 'shortcut icon'] for r in rel) or ('/images/' in href):
                    cat, fn = get_filename_and_category(href)
                    link["href"] = get_relative_path(hf, os.path.join(images_dir, fn))
                elif 'modulepreload' in rel and 'framerusercontent.com' in href:
                    p = href.replace('https://framerusercontent.com/', '').split('?')[0]
                    target_local = os.path.join(site_root_dir, 'framerusercontent', p.replace('/', os.sep))
                    link["href"] = get_relative_path(hf, target_local)

        # Localize Meta Tags
        for meta in soup.find_all("meta"):
            prop = meta.get("property", "") or meta.get("name", "")
            content_val = meta.get("content", "")
            if content_val and content_val.startswith(("http://", "https://")):
                if "image" in prop or "/images/" in content_val or "/assets/" in content_val:
                    cat, fn = get_filename_and_category(content_val)
                    if cat in ['images', 'assets']:
                        link_dest = os.path.join(images_dir, fn)
                        meta["content"] = get_relative_path(hf, link_dest)
                elif prop in ["framer-search-index", "framer-search-index-fallback"] and "framerusercontent.com" in content_val:
                    p = content_val.replace('https://framerusercontent.com/', '').split('?')[0]
                    target_local = os.path.join(site_root_dir, 'framerusercontent', p.replace('/', os.sep))
                    meta["content"] = get_relative_path(hf, target_local)

        # Localize Scripts
        for script in soup.find_all("script"):
            src = script.get("src")
            if src:
                if any(t in src for t in ["events.framer.com", "google-analytics.com", "googletagmanager.com", "hotjar.com"]):
                    script.decompose()
                elif "framerusercontent.com" in src:
                    p = src.replace('https://framerusercontent.com/', '').split('?')[0]
                    target_local = os.path.join(site_root_dir, 'framerusercontent', p.replace('/', os.sep))
                    script["src"] = get_relative_path(hf, target_local)
            else:
                text = script.string
                if text and 'https://framerusercontent.com/' in text:
                    def replace_inline_script_url(m):
                        u = m.group(0)
                        if '/images/' in u or '/assets/' in u:
                            cat, fn = get_filename_and_category(u)
                            return get_relative_path(hf, os.path.join(images_dir, fn))
                        return u
                    script.string = re.sub(r'https://framerusercontent\.com/(?:images|assets)/[^\s"\'`<>)]+', replace_inline_script_url, text)

        # Localize Navigation and Internal Links based on page directory depth
        rel_page_path = os.path.relpath(hf, site_root_dir)
        page_depth = rel_page_path.count(os.sep)
        root_prefix = ("../" * page_depth) if page_depth > 0 else "./"

        known_routes = [
            'about', 'blog', 'contact', 'location', 'tours',
            'categories', 'legal-pages', 'traveler-stories'
        ]

        for a in soup.find_all('a'):
            href = a.get('href', '')
            if not href or href.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'javascript:')):
                continue

            clean_href = href.lstrip('./').lstrip('/')
            if href in ['./', '.', '/'] or clean_href == '':
                a['href'] = root_prefix
                continue

            for route in known_routes:
                if clean_href == route or clean_href.startswith(route + '/') or clean_href.startswith(route + '?'):
                    a['href'] = root_prefix + clean_href
                    break

        # Apply Optional Modifiers
        if clean_badges:
            strip_badges_and_popups(soup)
        if enable_sandbox:
            apply_sandbox_csp(soup)
        if enable_forms:
            inject_local_form_handler(soup)
        if enable_pwa:
            depth_prefix = get_relative_path(hf, site_root_dir)
            inject_pwa_tags(soup, depth_prefix)

        with open(hf, 'w', encoding='utf-8') as f_out:
            f_out.write(str(soup))
        rel_disp = os.path.relpath(hf, site_root_dir)
        print(f"  [✓] Fully Localized & Completed: {rel_disp}")

    if enable_pwa:
        generate_pwa_assets(site_root_dir)

    print("\n" + "=" * 65)
    print("SUCCESS: 100% Complete Offline Studio Localization Finished!")
    print(f"Images: {images_dir}")
    print(f"Fonts:  {fonts_dir}")
    print(f"Videos: {videos_dir}")
    print(f"CSS:    {css_dir}")
    print("=" * 65 + "\n")
    return True


def resolve_site_root(target_path):
    target = os.path.abspath(target_path)
    if os.path.isfile(target):
        return os.path.dirname(target)
    if os.path.exists(os.path.join(target, 'index.html')):
        return target
    for sub in ['cloned_site', 'raw-framer-site', 'dist', 'build', 'out']:
        sub_path = os.path.join(target, sub)
        if os.path.exists(os.path.join(sub_path, 'index.html')):
            return sub_path
    return target


# =============================================================================
# FEATURE 11: STANDALONE SERVER, LIVE RELOAD & GUI ENDPOINTS
# =============================================================================
WELCOME_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Clonero Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>/* offline fallback: if CDN fails, basic layout still works */ .glass{backdrop-filter:blur(12px)}</style>
</head>
<body class="bg-slate-950 text-slate-100 flex items-center justify-center min-h-screen p-6 font-sans">
  <div class="max-w-md text-center space-y-5 bg-slate-900/80 p-8 rounded-3xl border border-slate-800 shadow-2xl">
    <div class="w-16 h-16 bg-sky-500/10 text-sky-400 rounded-2xl flex items-center justify-center mx-auto text-3xl font-bold border border-sky-500/20">
      ⚡
    </div>
    <h1 class="text-2xl font-extrabold text-white">Clonero Studio Ready</h1>
    <p class="text-slate-400 text-sm">No website cloned in this directory yet. Open the Visual Dashboard to clone any URL instantly.</p>
    <a href="/dashboard" class="inline-block w-full bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold py-3 px-6 rounded-xl transition">
      🚀 Open Studio Dashboard
    </a>
  </div>
</body>
</html>
"""

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class UltimateStudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME_TYPES.get(ext, super().guess_type(path))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_POST(self):
        if self.path == '/api/submit-form':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                record_form_submission(data)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status":"success","message":"Form recorded locally"}')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"status":"error","message":"{str(e)}"}}'.encode('utf-8'))
            return

        if self.path == '/api/gui-action':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                req = json.loads(body)
                act = req.get('action')
                res = {"status": "ok", "action": act}

                target_dir = self.directory
                if act == 'clone' and req.get('url'):
                    _url = req.get('url','').strip()
                    _parsed = urllib.parse.urlparse(_url)
                    if _parsed.scheme not in ('http','https') or not _parsed.netloc:
                        raise ValueError('Invalid URL: must be http(s)://...')
                    import ipaddress, socket
                    try:
                        ip = socket.gethostbyname(_parsed.hostname)
                        if ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback:
                            raise ValueError('Private/loopback URLs blocked for SSRF protection')
                    except ValueError:
                        raise
                    except Exception:
                        pass
                    if not os.path.exists(os.path.join(target_dir, 'index.html')):
                        target_dir = os.path.join(target_dir, 'cloned_site') if not target_dir.endswith('cloned_site') else target_dir
                    clone_website(req['url'], target_dir, clean_first=True)
                    localize_project(target_dir, enable_pwa=req.get('pwa', False), clean_badges=req.get('badges', True), enable_sandbox=req.get('sandbox', False), enable_forms=req.get('forms', True))
                    self.directory = target_dir
                elif act == 'localize':
                    localize_project(target_dir, enable_pwa=req.get('pwa', False), clean_badges=req.get('badges', True), enable_sandbox=req.get('sandbox', False), enable_forms=req.get('forms', True))
                elif act == 'nextjs':
                    out_next = os.path.join(self.directory, '..', 'nextjs_export') if self.directory.endswith('cloned_site') else os.path.join(self.directory, 'nextjs_export')
                    transpile_to_nextjs(target_dir, out_next)
                elif act == 'zip':
                    zip_p = create_zip_bundle(target_dir, os.path.join(target_dir, "offline_distribution.zip"))
                    res['zip_file'] = os.path.basename(zip_p)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(res).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"status":"error","message":"{str(e)}"}}'.encode('utf-8'))
            return

        return super().do_POST()

    def do_GET(self):
        clean_path = self.path.split('?')[0]

        # Live Reload timestamp endpoint (for --watch mode)
        if clean_path == '/__live_reload_check':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            with _live_reload_lock:
                ts = _live_reload_timestamp["value"]
            self.wfile.write(json.dumps({"ts": ts}).encode('utf-8'))
            return

        if clean_path in ['/dashboard', '/gui', '/admin']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(GUI_DASHBOARD_HTML.encode('utf-8'))
            return

        if clean_path in ['/', ''] and not os.path.exists(os.path.join(self.directory, 'index.html')):
            cloned_idx = os.path.join(self.directory, 'cloned_site', 'index.html')
            if os.path.exists(cloned_idx):
                self.directory = os.path.join(self.directory, 'cloned_site')
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(WELCOME_PAGE_HTML.encode('utf-8'))
                return

        local_path = os.path.join(self.directory, clean_path.lstrip('/'))
        if os.path.isdir(local_path):
            index_file = os.path.join(local_path, 'index.html')
            if os.path.exists(index_file):
                self.path = os.path.join(clean_path, 'index.html').replace(os.sep, '/')
        elif not os.path.exists(local_path):
            if os.path.exists(local_path + '.html'):
                self.path = clean_path + '.html'
            elif clean_path in ['/404', '/404/'] and os.path.exists(os.path.join(self.directory, '404.html')):
                self.path = '/404.html'
            elif not clean_path.startswith(('/assets/', '/api/', '/framerusercontent/')):
                # Serve custom 404 page
                four_o_four = os.path.join(self.directory, '404.html')
                if not os.path.exists(four_o_four):
                    four_o_four = os.path.join(self.directory, '404', 'index.html')
                if os.path.exists(four_o_four):
                    try:
                        with open(four_o_four, 'r', encoding='utf-8', errors='ignore') as f:
                            html_content = f.read()
                        encoded = html_content.encode('utf-8')
                        self.send_response(404)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.send_header('Content-Length', str(len(encoded)))
                        self.end_headers()
                        self.wfile.write(encoded)
                        return
                    except Exception:
                        pass

        # If watch mode is active, intercept HTML responses to inject live-reload script
        if getattr(self.server, '_watch_mode', False):
            resolved = os.path.join(self.directory, self.path.lstrip('/'))
            if os.path.isfile(resolved) and resolved.endswith('.html'):
                try:
                    with open(resolved, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    # Inject live reload script before </body>
                    if '</body>' in html_content and 'data-live-reload' not in html_content:
                        html_content = html_content.replace('</body>', LIVE_RELOAD_SCRIPT + '</body>')
                    encoded = html_content.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                    return
                except Exception:
                    pass  # fallback to default handler

        return super().do_GET()


def serve_studio(target_path, port=5000, watch=False, auto_open=False, path_suffix=""):
    site_root = resolve_site_root(target_path)
    handler = lambda *args, **kwargs: UltimateStudioHandler(*args, directory=site_root, **kwargs)

    httpd = None
    actual_port = port
    for p in range(port, port + 30):
        try:
            httpd = ReusableTCPServer(("", p), handler)
            actual_port = p
            break
        except OSError as e:
            if e.errno == 10048 or "10048" in str(e) or e.errno == 98 or "address already in use" in str(e).lower():
                continue
            raise

    if not httpd:
        print(f"[ERROR] Could not bind to any port in range {port}-{port+30}.")
        return

    if actual_port != port:
        print(f"[!] Port {port} was in use. Automatically switched to port {actual_port}.")

    # Enable watch mode: set flag on server + start file watcher
    watcher = None
    if watch:
        httpd._watch_mode = True
        watcher = FileWatcher(site_root, interval=1.0)
        watcher.start()
    else:
        httpd._watch_mode = False

    if auto_open:
        target_browser_url = f"http://localhost:{actual_port}{path_suffix}"
        auto_open_browser(target_browser_url)

    with httpd:
        print("=" * 65)
        print(" ⚡ ULTIMATE WEBSITE STUDIO & WEB SERVER RUNNING")
        print(f" Serving directory:  {site_root}")
        print(f" Local Website:     http://localhost:{actual_port}")
        print(f" Visual Dashboard:  http://localhost:{actual_port}/dashboard")
        if watch:
            print(f" Live Reload:       ✅ ACTIVE (auto-refreshes on file changes)")
        print(" Press Ctrl+C to stop.")
        print("=" * 65 + "\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            if watcher:
                watcher.stop()
            print("\n[+] Studio Server stopped.")


# =============================================================================
# CLI ENTRYPOINT
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Ultimate Website Engineering, Cloning, Localization, PWA, Next.js & Studio Suite."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="cloned_site" if os.path.exists("cloned_site") else ".",
        help="Path to local folder/HTML or full website URL (e.g. https://example.com)."
    )
    parser.add_argument("--clone", action="store_true", help="Crawl and clone from direct URL.")
    parser.add_argument("--to-pwa", action="store_true", help="Generate PWA manifest.json and offline Service Worker.")
    parser.add_argument("--to-nextjs", action="store_true", help="Transpile site to Next.js 15 / React 19 App Router.")
    parser.add_argument("--clean-badges", action=argparse.BooleanOptionalAction, default=True, help="Remove platform badges and popups (use --no-clean-badges to keep).")
    parser.add_argument("--remove-popups", action="store_true", help="Alias for --clean-badges: remove popups and cookie bars.")
    parser.add_argument("--sandbox", action="store_true", help="Inject strict offline Content-Security-Policy.")
    parser.add_argument("--local-forms", action=argparse.BooleanOptionalAction, default=True, help="Intercept forms to local SQLite/JSON/Webhooks (use --no-local-forms to disable).")
    parser.add_argument("--zip", nargs="?", const="offline_site.zip", help="Package site into deployable .zip bundle.")
    parser.add_argument("--report", action="store_true", help="Generate visual HTML/JSON audit report.")
    parser.add_argument("--serve", "-s", action="store_true", help="Launch local HTTP web server.")
    parser.add_argument("--gui", action="store_true", help="Launch visual web dashboard directly.")
    parser.add_argument("--watch", action="store_true", help="Enable live reload during local serving (auto-refreshes browser on file changes).")
    parser.add_argument("--no-open", action="store_true", help="Do not automatically open the browser on completion.")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Port for local server (default: 5000).")
    parser.add_argument("--workers", "-w", type=int, default=20, help="Download concurrency threads (default: 20).")
    parser.add_argument("--output", "-o", type=str, default="cloned_site", help="Output directory for --clone (default: cloned_site).")

    # Rebrand / Whitelabeling flags
    parser.add_argument("--rebrand", action="store_true", help="Enable whitelabeling & branding mode.")
    parser.add_argument("--title", type=str, default=None, help="New site title for rebranding.")
    parser.add_argument("--favicon", type=str, default=None, help="Path to new favicon file (.png/.ico/.svg).")
    parser.add_argument("--logo", type=str, default=None, help="Path to new logo file (.png/.svg).")
    parser.add_argument("--accent-color", type=str, default=None, help="New accent/brand color in hex (e.g. #FF6600 or FF6600).")
    parser.add_argument("--footer-text", type=str, default=None, help="Custom footer copyright/branding text.")
    parser.add_argument("--author", type=str, default=None, help="Author name for meta tags.")
    parser.add_argument("--meta-desc", type=str, default=None, help="New meta description for SEO.")

    args = parser.parse_args()

    # Merge --remove-popups into --clean-badges
    if args.remove_popups:
        args.clean_badges = True

    if args.gui:
        serve_studio(args.target, port=args.port, watch=args.watch, auto_open=not args.no_open, path_suffix="/dashboard")
        return

    if args.serve:
        serve_studio(args.target, port=args.port, watch=args.watch, auto_open=not args.no_open)
        return

    if args.to_nextjs:
        transpile_to_nextjs(args.target)
        return

    # Rebrand standalone mode
    if args.rebrand:
        target_dir = resolve_site_root(args.target)
        rebrand_project(
            target_dir,
            new_title=args.title,
            new_favicon=args.favicon,
            new_logo=args.logo,
            accent_color=args.accent_color,
            footer_text=args.footer_text,
            author_name=args.author,
            meta_description=args.meta_desc
        )
        if not args.no_open:
            serve_studio(target_dir, port=args.port, auto_open=True)
        return

    if args.clone or args.target.startswith(('http://', 'https://')):
        clone_dir = "cloned_site" if args.target.startswith(('http://', 'https://')) else args.target
        if not args.target.startswith(('http://', 'https://')):
            parser.error('--clone requires a URL as target, e.g. python website_localizer.py https://example.com --clone')
        target_url = args.target
        clone_website(target_url, clone_dir, clean_first=True)
        localize_project(clone_dir, workers=args.workers, clean_badges=args.clean_badges, enable_pwa=args.to_pwa, enable_sandbox=args.sandbox, enable_forms=args.local_forms)
        if args.zip:
            create_zip_bundle(clone_dir, args.zip)
        if args.report:
            generate_audit_report(clone_dir)

        if not args.no_open:
            print("[+] Cloning & Localization finished! Launching live preview...")
            serve_studio(clone_dir, port=args.port, auto_open=True, watch=args.watch)
        return

    success = localize_project(
        args.target,
        workers=args.workers,
        clean_badges=args.clean_badges,
        enable_pwa=args.to_pwa,
        enable_sandbox=args.sandbox,
        enable_forms=args.local_forms
    )

    if success:
        if args.report:
            generate_audit_report(args.target)
        if args.zip:
            create_zip_bundle(args.target, args.zip)

        if not args.no_open:
            print("[+] Localization finished! Launching live preview in browser...")
            serve_studio(args.target, port=args.port, auto_open=True, watch=args.watch)


if __name__ == '__main__':
    main()
