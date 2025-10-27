#!/usr/bin/env python3
"""
onion_bulk_scraper.py
Scrape .onion pages to extract the information paragraph from the item_box div.
Outputs CSV with columns: url, description. Saves all data at once after scraping.

Usage:
    python onion_bulk_scraper.py urls.txt results.csv
"""

import sys
import time
import csv
import os
import argparse
from typing import Optional, List, Dict
import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller

def clean(s: Optional[str]) -> str:
    """Clean text by removing extra whitespace and ensuring it's a string."""
    if not s:
        return ""
    return ' '.join(s.split()).strip()

def renew_tor_ip(port: int = 9051) -> bool:
    """Renew Tor circuit to get a new IP address."""
    try:
        with Controller.from_port(port=port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            print("Tor IP renewed.")
            time.sleep(3)  # Increased wait for circuit stabilization
            return True
    except Exception as e:
        print(f"Error renewing Tor IP: {e}")
        return False

def extract_information(soup: BeautifulSoup) -> str:
    """Extract the information paragraph from the item_box div's col-md-8 col-xl-6 section."""
    try:
        item_box = soup.find('div', class_='item_box')
        if item_box:
            content_div = item_box.find('div', class_='col-md-8 col-xl-6')
            if content_div:
                paragraphs = content_div.find_all(text=True, recursive=False)
                content = ' '.join(p.strip() for p in paragraphs if p.strip())
                return clean(content)
        return ""
    except Exception as e:
        print(f"Error extracting information: {e}")
        return ""

def extract_csrf_token(html: str) -> Optional[str]:
    """Extract CSRF token from HTML meta tag."""
    try:
        soup = BeautifulSoup(html, "lxml")
        meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
        if meta_tag and meta_tag.get('content'):
            return meta_tag.get('content')
        return None
    except Exception as e:
        print(f"Error extracting CSRF token: {e}")
        return None

def make_session(socks_host: str, socks_port: int) -> requests.Session:
    """Create a requests session configured to use Tor's SOCKS5 proxy."""
    session = requests.Session()
    proxy = f"socks5h://{socks_host}:{socks_port}"
    session.proxies.update({"http": proxy, "https": proxy})
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
        "Referer": "http://ijzn3sicrcy7guixkzjkib4ukbiilwc3xhnmby4mcbccnsd7j2rekvqd.onion/"
    })
    return session

def fetch(session: requests.Session, url: str, retries: int = 3, control_port: int = 9051) -> Optional[str]:
    """Fetch HTML content from a URL with retries and Tor IP renewal."""
    for attempt in range(1, retries + 1):
        try:
            if hasattr(session, 'csrf_token') and session.csrf_token:
                session.headers.update({"X-CSRF-Token": session.csrf_token})

            r = session.get(url, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or r.encoding

            csrf_token = extract_csrf_token(r.text)
            if csrf_token:
                session.csrf_token = csrf_token
                print(f"Extracted CSRF token: {csrf_token[:20]}...")

            return r.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"[{attempt}/{retries}] 400 Bad Request for {url}: {e.response.text[:200]}...")
                print(f"Response headers: {e.response.headers}")
                if "captcha" in e.response.text.lower():
                    print("CAPTCHA detected. Manual intervention may be required.")
                if attempt < retries:
                    print("Attempting to renew Tor IP...")
                    renew_tor_ip(control_port)
            else:
                print(f"[{attempt}/{retries}] Failed {url}: {e}")
            time.sleep(attempt * 3)
        except Exception as e:
            print(f"[{attempt}/{retries}] Failed {url}: {e}")
            time.sleep(attempt * 3)
    return None

def save_to_csv(rows: List[Dict[str, str]], out_csv: str, append: bool = True):
    """Save rows to CSV file."""
    try:
        mode = 'a' if append and os.path.exists(out_csv) else 'w'
        with open(out_csv, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "description"])
            if mode == 'w':
                writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {len(rows)} rows to {out_csv}")
    except Exception as e:
        print(f"Error writing to {out_csv}: {e}")

def main():
    """Main function to scrape .onion URLs and save all results to CSV in one shot."""
    ap = argparse.ArgumentParser(description="Scrape .onion pages for information paragraph and output to CSV.")
    ap.add_argument("urls_file", help="Text file containing .onion URLs (one per line)")
    ap.add_argument("out_csv", help="Output CSV file")
    ap.add_argument("--socks-host", default="127.0.0.1", help="Tor SOCKS host")
    ap.add_argument("--socks-port", type=int, default=9150, help="Tor SOCKS port (9050 for system Tor, 9150 for Tor Browser)")
    ap.add_argument("--control-port", type=int, default=9051, help="Tor control port for IP renewal")
    ap.add_argument("--delay", type=float, default=3.0, help="Delay between requests in seconds")
    ap.add_argument("--batch-size", type=int, default=20, help="Number of URLs per session batch")
    args = ap.parse_args()

    try:
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {args.urls_file} not found.")
        sys.exit(1)

    all_rows = []

    for batch_start in range(0, len(urls), args.batch_size):
        batch_urls = urls[batch_start:batch_start + args.batch_size]
        print(f"\nProcessing batch {batch_start // args.batch_size + 1} ({len(batch_urls)} URLs)")

        session = make_session(args.socks_host, args.socks_port)
        renew_tor_ip(args.control_port)

        for i, url in enumerate(batch_urls, batch_start + 1):
            print(f"[{i}/{len(urls)}] {url}")
            html = fetch(session, url, retries=3, control_port=args.control_port)
            if not html:
                all_rows.append({"url": url, "description": ""})
                print("  -> No content fetched")
            else:
                soup = BeautifulSoup(html, "lxml")
                description = extract_information(soup)
                all_rows.append({"url": url, "description": description})
                print(f"  -> description: {description[:50]}... (len={len(description)})")
            time.sleep(args.delay)

    # Save all results in one shot
    save_to_csv(all_rows, args.out_csv, append=False)

    print(f"Done. {len(all_rows)} rows written to {args.out_csv}")

if __name__ == "__main__":
    main()