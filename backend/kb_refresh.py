import re
import sqlite3
from typing import Optional

import requests
from bs4 import BeautifulSoup

JS_MARKERS = [
    "You need to enable JavaScript to run this app",
    "enable javascript",
]

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # remove junk
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def fetch_static(url: str, timeout: int = 20) -> Optional[str]:
    headers = {"User-Agent": "ai-mail-saas-kb-bot/1.0"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text

def looks_js_only(html: str) -> bool:
    h = (html or "").lower()
    return any(m.lower() in h for m in JS_MARKERS)

def fetch_rendered_playwright(url: str, timeout_ms: int = 25000) -> str:
    # Lazy import so script works even if playwright not installed
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        html = page.content()
        browser.close()
        return html

def truncate(text: str, max_chars: int = 20000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]\n"

def main():
    db = "ai_mail.db"
    con = sqlite3.connect(db)
    cur = con.cursor()

    rows = cur.execute(
        "SELECT id, name, COALESCE(NULLIF(website_url,''), website) FROM organizations "
        "WHERE COALESCE(NULLIF(website_url,''), website) <> ''"
    ).fetchall()

    if not rows:
        print("No orgs with website_url/website set.")
        return

    for org_id, name, url in rows:
        url = (url or "").strip()
        if not url:
            continue

        print(f"\n[KB] org={org_id} name={name} url={url}")

        html = None
        try:
            html = fetch_static(url)
            if looks_js_only(html):
                print("[KB] Detected JS-only site -> using Playwright render")
                html = fetch_rendered_playwright(url)
        except Exception as e:
            print("[KB] Static fetch failed -> trying Playwright:", repr(e))
            try:
                html = fetch_rendered_playwright(url)
            except Exception as e2:
                print("[KB] Playwright failed:", repr(e2))
                continue

        text = clean_text(html)
        text = truncate(text, max_chars=25000)

        # Store back to DB
        cur.execute(
            "UPDATE organizations SET kb_text=? WHERE id=?",
            (text, org_id),
        )
        con.commit()
        print(f"[KB] Saved kb_text chars={len(text)}")

    con.close()
    print("\nDone.")

if __name__ == "__main__":
    main()
