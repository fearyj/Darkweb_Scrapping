import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time

# Configuration
PLAY_MAIN_URL = "http://k7kg3jqxang3wh7hnmaiokchk7qoebupfgoik6rha6mjpzwupwtj25yd.onion"

PROXIES = {
    'http': 'socks5h://127.0.0.1:9150',
    'https': 'socks5h://127.0.0.1:9150'
}

OUTPUT_FILE = f"play_victims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

def test_connection():
    """Test if Tor connection is working"""
    try:
        print("Testing Tor connection...")
        response = requests.get(
            "https://check.torproject.org/api/ip",
            proxies=PROXIES,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('IsTor'):
                print("✓ Tor connection successful!")
                return True
        print("✗ Not connected through Tor")
        return False
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

def scrape_play_main_page(base_url):
    """Scrape the main Play ransomware leak site"""
    print(f"\nConnecting to: {base_url}")
    
    try:
        response = requests.get(
            base_url,
            proxies=PROXIES,
            timeout=90
        )
        
        if response.status_code != 200:
            print(f"✗ Failed to connect (Status: {response.status_code})")
            return []
        
        print("✓ Connected successfully!")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all victim entries
        victim_entries = soup.find_all('th', {'class': 'News'})
        
        if not victim_entries:
            print("✗ No victim entries found on the page")
            return []
        
        print(f"✓ Found {len(victim_entries)} victim entries\n")
        
        all_victims = []
        
        for idx, entry in enumerate(victim_entries, 1):
            try:
                # Extract victim name/title
                title = ""
                if entry.next_element:
                    title = entry.next_element.strip()
                
                # Extract description (location)
                description = ""
                location_elem = entry.find('i', {'class': 'location'})
                if location_elem and location_elem.next_sibling:
                    description = location_elem.next_sibling.strip()
                
                # Extract website
                website = ""
                link_elem = entry.find('i', {'class': 'link'})
                if link_elem and link_elem.next_sibling:
                    website = link_elem.next_sibling.strip()
                
                # Extract post URL from onclick attribute
                post_url = ""
                onclick_value = entry.get('onclick', '')
                if onclick_value and "'" in onclick_value:
                    try:
                        topic_id = onclick_value.split("'")[1]
                        post_url = f"{base_url}/topic.php?id={topic_id}"
                        # Fix double slashes
                        post_url = post_url.replace('//', '/').replace('http:/', 'http://')
                    except:
                        pass
                
                # Extract dates
                added_date = ""
                published_date = ""
                
                date_div = entry.find_next('div', {'style': 'line-height: 1.70;'})
                if date_div:
                    div_text = date_div.get_text()
                    
                    if 'added:' in div_text:
                        try:
                            added_date = div_text.split('added:')[1].split('publication date:')[0].strip()
                        except:
                            pass
                    
                    if 'publication date:' in div_text:
                        try:
                            published_date = div_text.split('publication date:')[1].strip()
                        except:
                            pass
                
                victim_data = {
                    'Victim Name': title,
                    'Description': description,
                    'Website': website,
                    'Added Date': added_date,
                    'Publication Date': published_date,
                    'Post URL': post_url,
                    'Group': 'play',
                    'Scraped Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                all_victims.append(victim_data)
                
                print(f"[{idx}/{len(victim_entries)}] ✓ {title}")
                
            except Exception as e:
                print(f"[{idx}/{len(victim_entries)}] ✗ Error: {str(e)}")
                continue
        
        return all_victims
        
    except requests.exceptions.Timeout:
        print("✗ Connection timeout")
        return []
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - check Tor is running")
        return []
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return []

def try_multiple_urls(urls):
    """Try multiple mirror URLs until one works"""
    for url in urls:
        print(f"\nAttempting: {url}")
        victims = scrape_play_main_page(url)
        if victims:
            return victims
        print("Trying next URL...\n")
        time.sleep(3)
    return []

def save_to_excel(data, filename):
    """Save data to Excel"""
    if not data:
        print("\n✗ No data to save!")
        return
    
    df = pd.DataFrame(data)
    
    # Remove duplicates based on victim name
    df = df.drop_duplicates(subset=['Victim Name'], keep='first')
    
    # Sort by added date if available
    if 'Added Date' in df.columns:
        df = df.sort_values('Added Date', ascending=False)
    
    df.to_excel(filename, index=False, engine='openpyxl')
    
    print(f"\n{'='*60}")
    print(f"✓ SUCCESS!")
    print(f"{'='*60}")
    print(f"Total victims collected: {len(df)}")
    print(f"File saved: {filename}")
    print(f"{'='*60}\n")

def main():
    print("=" * 60)
    print("Play Ransomware Direct Site Scraper")
    print("=" * 60)
    
    # Test Tor connection
    if not test_connection():
        print("\n⚠ Warning: Tor connection test failed")
        print("Make sure Tor is running on port 9150")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # List of known Play mirrors
    mirror_urls = [
        "http://k7kg3jqxang3wh7hnmaiokchk7qoebupfgoik6rha6mjpzwupwtj25yd.onion",
        "http://mbrlkbtq5jonaqkurjwmxftytyn2ethqvbxfu4rgjbkkknndqwae6byd.onion",
        "http://j75o7xvvsm4lpsjhkjvb4wl2q6ajegvabe6oswthuaubbykk4xkzgpid.onion"
    ]
    
    # Try scraping from available mirrors
    print("\nStarting scrape...")
    victims = try_multiple_urls(mirror_urls)
    
    # Save results
    if victims:
        save_to_excel(victims, OUTPUT_FILE)
    else:
        print("\n✗ Failed to collect any data")
        print("Possible issues:")
        print("  - Tor is not running")
        print("  - Site is down")
        print("  - HTML structure has changed")
        print("  - Connection blocked")

if __name__ == "__main__":
    main()