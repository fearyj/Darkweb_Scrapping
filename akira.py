import datetime
import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import urllib3
import time

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Tor Browser proxy configuration (port 9150)
proxies = {
    'http': 'socks5h://localhost:9150',
    'https': 'socks5h://localhost:9150'
}

# Headers for requests
headers = {}

# Configuration
TARGET_YEAR = 2025
MAX_PAGES = 41  # Stop at page 41
OUTPUT_FILE = f"akira_victims_2025_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

def stdlog(message):
    """Simple logging function"""
    print(f"[INFO] {message}")

def errlog(message):
    """Simple error logging function"""
    print(f"[ERROR] {message}")

def is_date_in_2025(date_string):
    """Check if a date string is from 2025"""
    if not date_string:
        return False
    try:
        if '2025' in date_string:
            return True
        return False
    except:
        return False

def fetch_json_from_onion_url(onion_url, cookies, params=None):
    """
    Fetch JSON data from the given onion URL with optional parameters for pagination.
    """
    try:
        headers.update({
            "Referer": "https://akiral2iz6a7qgd3ayp3l6yub7xx2uep76idk3u2kollpj5z3z636bad.onion/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Priority": "u=0",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "X-Requested-With": "XMLHttpRequest"
        })

        response = requests.get(
            onion_url, 
            headers=headers, 
            cookies=cookies, 
            proxies=proxies, 
            params=params,
            verify=False, 
            timeout=(60, 60)
        )
        response.raise_for_status()

        json_data = response.json()
        return json_data
    except requests.exceptions.RequestException as e:
        errlog(f"Error fetching JSON: {e}")
        return None
    except json.JSONDecodeError as e:
        errlog(f"Error parsing JSON: {e}")
        return None

def get_csrf_token(onion_url):
    """
    Fetch the CSRF token and cookies from the onion site.
    """
    try:
        stdlog(f"Connecting to: {onion_url}")
        
        response = requests.get(onion_url, proxies=proxies, verify=False, timeout=(60, 60))
        response.raise_for_status()
        
        stdlog(f"Connection successful")

        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_element = soup.find('meta', {'name': 'csrf-token'})
        csrf_token = csrf_element['content'] if csrf_element and 'content' in csrf_element.attrs else None

        cookies = response.cookies
        
        if csrf_token:
            stdlog(f"CSRF Token obtained")

        return csrf_token, cookies
    except Exception as e:
        errlog(f"Error: {e}")
        return None, None

def fetch_all_pages(base_url, cookies, data_type="news", sort_by="name:desc", max_pages=MAX_PAGES):
    """
    Fetch pages up to max_pages limit
    """
    all_entries = []
    page = 1
    consecutive_empty = 0
    max_consecutive_empty = 3
    
    stdlog(f"Fetching {data_type} data (max {max_pages} pages)...")
    
    while page <= max_pages:
        params = {
            'page': page,
            'sort': sort_by
        }
        
        print(f"[INFO]   Page {page}/{max_pages}...", end=' ')
        
        json_data = fetch_json_from_onion_url(base_url, cookies, params)
        
        if not json_data:
            print("Failed")
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                stdlog(f"  Stopping after {consecutive_empty} failed attempts")
                break
            page += 1
            time.sleep(1)
            continue
        
        if 'objects' in json_data and json_data['objects']:
            entries = json_data['objects']
            all_entries.extend(entries)
            print(f"{len(entries)} entries")
            consecutive_empty = 0
        else:
            print("Empty")
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                stdlog(f"  No more data found")
                break
        
        page += 1
        time.sleep(1)
    
    stdlog(f"Completed {data_type}: {len(all_entries)} total entries from {page - 1} pages")
    return all_entries

def save_to_excel(data, filename):
    """Save collected data to Excel"""
    if not data:
        stdlog("No data to save")
        return
    
    df = pd.DataFrame(data)
    
    initial_count = len(df)
    df = df.drop_duplicates(subset=['Victim Name'], keep='first')
    
    if 'Date' in df.columns:
        df = df.sort_values('Date', ascending=False)
    
    df.to_excel(filename, index=False, engine='openpyxl')
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print("="*60)
    print(f"Total entries: {len(df)}")
    if initial_count > len(df):
        print(f"Duplicates removed: {initial_count - len(df)}")
    print(f"File saved: {filename}")
    print("="*60 + "\n")

def main():
    print("="*60)
    print("Akira Ransomware Scraper - 2025 Data")
    print(f"Max pages per endpoint: {MAX_PAGES}")
    print("Using Tor Browser on port 9150")
    print("="*60)
    print()
    
    news_url = 'https://akiral2iz6a7qgd3ayp3l6yub7xx2uep76idk3u2kollpj5z3z636bad.onion/n'
    leak_url = 'https://akiral2iz6a7qgd3ayp3l6yub7xx2uep76idk3u2kollpj5z3z636bad.onion/l'
    site_onion_url = 'https://akiral2iz6a7qgd3ayp3l6yub7xx2uep76idk3u2kollpj5z3z636bad.onion/'

    all_data = []

    csrf_token, cookies = get_csrf_token(site_onion_url)

    if csrf_token and cookies:
        headers["X-CSRF-Token"] = csrf_token

        # Fetch NEWS pages (max 41)
        news_entries = fetch_all_pages(news_url, cookies, "news", "date:desc", MAX_PAGES)
        
        if news_entries:
            news_2025_count = 0
            for entry in news_entries:
                title = entry.get('title', '').replace('\n', '')
                description = entry.get('content', '')
                date = entry.get('date', '')
                
                if is_date_in_2025(date):
                    all_data.append({
                        'Victim Name': title,
                        'Description': description,
                        'Type': 'News',
                        'Date': date,
                        'Published': date + " 00:00:00.000000",
                        'Group': 'akira',
                        'Scraped Date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    news_2025_count += 1
            
            stdlog(f"Filtered: {news_2025_count} news entries from 2025 (out of {len(news_entries)} total)")
        
        # Fetch LEAK pages (max 41)
        leak_entries = fetch_all_pages(leak_url, cookies, "leaks", "name:desc", MAX_PAGES)
        
        if leak_entries:
            leak_count = 0
            for entry in leak_entries:
                title = entry.get('name', '').replace('\n', '')
                description = entry.get('desc', '')
                date = entry.get('date', '')
                
                # Include all leaks or filter by date if available
                if date:
                    if not is_date_in_2025(date):
                        continue
                
                all_data.append({
                    'Victim Name': title,
                    'Description': description,
                    'Type': 'Leak',
                    'Date': date if date else '',
                    'Published': '',
                    'Group': 'akira',
                    'Scraped Date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                leak_count += 1
            
            stdlog(f"Collected: {leak_count} leak entries")
        
        if all_data:
            save_to_excel(all_data, OUTPUT_FILE)
        else:
            errlog("No data collected")
        
    else:
        errlog("Failed to fetch CSRF token or cookies")

if __name__ == "__main__":
    main()