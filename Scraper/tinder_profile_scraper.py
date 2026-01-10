#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tinder Profile Scraper
Extracts data from the first visible Tinder profile without swiping
"""

import sys
import json
import csv
import argparse
import os
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import tinderbotz
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from tinderbotz.session import Session
except ImportError as e:
    print(f"[X] Error: Missing required package: {e}")
    print("[+] Please install requirements: cd .. && uv pip install -e .")
    sys.exit(1)

# Color output (simple ASCII for cross-platform compatibility)
GREEN = "[OK]"
RED = "[X]"
YELLOW = "[!]"
CYAN = "[*]"


def load_cookies_from_file(cookie_file):
    """Load cookies from JSON file extracted by extract_tinder_cookies.py"""
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        if not isinstance(cookies, list):
            print(f"{RED} Error: Invalid cookie file format. Expected a JSON array")
            return None
        
        if not cookies:
            print(f"{YELLOW} Warning: Cookie file is empty")
            return None
        
        print(f"{GREEN} Loaded {len(cookies)} cookies from {cookie_file}")
        return cookies
    except FileNotFoundError:
        print(f"{RED} Error: Cookie file not found: {cookie_file}")
        return None
    except json.JSONDecodeError as e:
        print(f"{RED} Error: Invalid JSON in cookie file: {e}")
        return None
    except Exception as e:
        print(f"{RED} Error: Failed to load cookies: {e}")
        return None


def inject_cookies_to_session(session, cookies):
    """Inject cookies into the browser session"""
    try:
        browser = session.browser
        
        # Navigate to Tinder first (required for Selenium cookie injection)
        print(f"{CYAN} Navigating to Tinder to inject cookies...")
        browser.get("https://www.tinder.com/?lang=en")
        time.sleep(3)
        
        # Debug: Check current URL and page title
        print(f"{CYAN} Current URL: {browser.current_url}")
        print(f"{CYAN} Page title: {browser.title[:100] if browser.title else 'None'}")
        
        # Inject each cookie
        injected_count = 0
        failed_cookies = []
        for cookie in cookies:
            try:
                # Selenium requires 'sameSite' field, set it if missing
                if 'sameSite' not in cookie:
                    cookie['sameSite'] = 'None'
                elif cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = 'None'
                
                # Remove 'expiry' if it's None or invalid (Selenium doesn't like None expiry)
                if 'expiry' in cookie and cookie['expiry'] is None:
                    del cookie['expiry']
                
                # Ensure domain starts with a dot for cross-subdomain cookies
                if 'domain' in cookie and not cookie['domain'].startswith('.'):
                    if '.' in cookie['domain']:
                        cookie['domain'] = f".{cookie['domain']}"
                
                browser.add_cookie(cookie)
                injected_count += 1
            except Exception as e:
                # Some cookies might fail (e.g., secure cookies on non-HTTPS, expired, etc.)
                # Continue with other cookies
                if 'sameSite' not in str(e).lower():
                    failed_cookies.append((cookie.get('name', 'unknown'), str(e)))
        
        if failed_cookies:
            print(f"{YELLOW} Warning: Failed to inject {len(failed_cookies)} cookie(s):")
            for name, error in failed_cookies:
                print(f"{YELLOW}   - {name}: {error[:100]}")
        
        print(f"{GREEN} Injected {injected_count} cookies")
        
        # Refresh page to apply cookies
        print(f"{CYAN} Refreshing page to apply cookies...")
        browser.refresh()
        time.sleep(3)
        
        # Debug: Check URL after refresh
        print(f"{CYAN} URL after refresh: {browser.current_url}")
        
        # Wait a bit more for any redirects or page loads
        time.sleep(2)
        
        # Check final URL
        final_url = browser.current_url
        print(f"{CYAN} Final URL after waiting: {final_url}")
        
        # Check if we're seeing a verification challenge or login page
        page_source = browser.page_source[:1000].lower()
        page_title = browser.title
        
        print(f"{CYAN} Page title: {page_title}")
        
        # Check for various Tinder page indicators
        if 'verify' in page_source or 'verification' in page_source or 'puzzle' in page_source or 'captcha' in page_source:
            print(f"{YELLOW} Warning: Page content suggests verification challenge may be present")
            print(f"{YELLOW} Please complete verification manually in your browser first")
            print(f"{CYAN} Browser window should be visible - you can manually complete verification there")
        
        if 'log in' in page_source or 'login' in page_source or 'sign in' in page_source:
            print(f"{YELLOW} Warning: Still on login page - cookies are not authentication cookies")
            print(f"{YELLOW} You need to be fully logged into Tinder in Firefox first")
            print(f"{YELLOW} Steps to fix:")
            print(f"{YELLOW}  1. Open Firefox Developer Edition manually")
            print(f"{YELLOW}  2. Navigate to https://www.tinder.com")
            print(f"{YELLOW}  3. Complete login and any verification (CAPTCHA/puzzle/video selfie)")
            print(f"{YELLOW}  4. Make sure you're fully logged in (URL should be tinder.com/app/...)")
            print(f"{YELLOW}  5. Then run: pnpm scrape:tinder --auto-session")
        
        # Verify login status
        if session._is_logged_in():
            print(f"{GREEN} Successfully logged in via cookies!")
            return True
        else:
            print(f"{YELLOW} Cookies injected but login verification failed")
            print(f"{CYAN} Current URL: {final_url}")
            print(f"{CYAN} Expected URL to contain 'tinder.com/app/' for successful login")
            
            # If not in headless mode, keep browser open longer so user can see what's happening
            if not session.browser.capabilities.get('goog:chromeOptions', {}).get('args', []):
                print(f"{CYAN} Browser window is open - checking page content...")
                print(f"{CYAN} If you see a login/verification page, complete it manually")
            
            return False
            
    except Exception as e:
        print(f"{RED} Error injecting cookies: {e}")
        import traceback
        traceback.print_exc()
        return False


def scrape_profile(email: str = None, password: str = None, login_method: str = 'facebook', 
                   cookie_file: str = None, output_format: str = 'json', output_file: str = None, 
                   headless: bool = True):
    """
    Scrape the first visible Tinder profile without swiping
    
    Args:
        email: Email for login (optional if using existing session or cookies)
        password: Password for login (optional if using existing session or cookies)
        login_method: Login method ('facebook' or 'google', default: 'facebook')
        cookie_file: Path to cookie file extracted by extract_tinder_cookies.py (recommended)
        output_format: Output format ('json' or 'csv')
        output_file: Output file path (optional, auto-generated if not provided)
        headless: Run browser in headless mode (default: True - recommended for automation)
    """
    try:
        print(f"{CYAN} Initializing Tinder session...")
        
        # Create session (headless mode if requested)
        session = Session(headless=headless, store_session=True)
        
        # Try cookie-based authentication first (recommended)
        logged_in = False
        if cookie_file:
            print(f"{CYAN} Attempting cookie-based authentication...")
            cookies = load_cookies_from_file(cookie_file)
            if cookies:
                logged_in = inject_cookies_to_session(session, cookies)
                if logged_in:
                    print(f"{GREEN} Authentication successful via cookies")
        
        # Fall back to email/password login if cookies failed or not provided
        if not logged_in:
            if email and password:
                print(f"{CYAN} Using email/password authentication...")
                if login_method.lower() == 'facebook':
                    session.login_using_facebook(email, password)
                elif login_method.lower() == 'google':
                    session.login_using_google(email, password)
                else:
                    print(f"{RED} Error: Invalid login method. Use 'facebook' or 'google'")
                    sys.exit(1)
                print(f"{GREEN} Login successful")
            else:
                # Check if already logged in (existing session)
                print(f"{CYAN} Checking existing session...")
                if session._is_logged_in():
                    print(f"{GREEN} Using existing session")
                    logged_in = True
                else:
                    print(f"{RED} Error: Not logged in and no authentication method provided")
                    print(f"{YELLOW} Please provide one of the following:")
                    print(f"{YELLOW}  1. --cookies <file> (recommended) - Extract cookies automatically with --auto-session")
                    print(f"{YELLOW}  2. --email <email> --password <password> --login-method <facebook|google>")
                    print(f"{YELLOW}  3. Ensure you have an active TinderBotz session")
                    sys.exit(1)
        
        # Get the first visible profile (without swiping)
        print(f"{CYAN} Extracting first visible profile...")
        print(f"{YELLOW} Note: This will NOT swipe - only view the current profile")
        
        geomatch = session.get_geomatch(quickload=False)
        
        if not geomatch or not geomatch.get_name():
            print(f"{RED} Error: Could not extract profile data")
            print(f"{YELLOW} Make sure you are logged in and there is a profile visible")
            sys.exit(1)
        
        # Extract profile data
        profile_data = {
            "id": geomatch.get_id(),
            "name": geomatch.get_name(),
            "age": geomatch.get_age(),
            "bio": geomatch.get_bio(),
            "work": geomatch.get_work(),
            "study": geomatch.get_study(),
            "home": geomatch.get_home(),
            "gender": geomatch.get_gender(),
            "distance": geomatch.get_distance(),
            "passions": geomatch.get_passions(),
            "lifestyle": geomatch.get_lifestyle(),
            "basics": geomatch.get_basics(),
            "anthem": geomatch.get_anthem(),
            "looking_for": geomatch.get_looking_for(),
            "instagram": geomatch.get_instagram(),
            "image_urls": geomatch.get_image_urls(),
            "extracted_at": datetime.now().isoformat(),
        }
        
        print(f"{GREEN} Profile extracted: {profile_data['name']} ({profile_data['age']})")
        print(f"{CYAN} Bio: {profile_data['bio'][:100] if profile_data['bio'] else 'N/A'}...")
        print(f"{CYAN} Images: {len(profile_data['image_urls'])}")
        
        # Save output
        if not output_file:
            output_file = f"tinder_profile_{profile_data['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
        
        if output_format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
        else:  # CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Field', 'Value'])
                writer.writerow(['ID', profile_data.get('id', '')])
                writer.writerow(['Name', profile_data.get('name', '')])
                writer.writerow(['Age', profile_data.get('age', '')])
                writer.writerow(['Bio', profile_data.get('bio', '')])
                writer.writerow(['Work', profile_data.get('work', '')])
                writer.writerow(['Study', profile_data.get('study', '')])
                writer.writerow(['Home', profile_data.get('home', '')])
                writer.writerow(['Gender', profile_data.get('gender', '')])
                writer.writerow(['Distance', profile_data.get('distance', '')])
                writer.writerow(['Instagram', profile_data.get('instagram', '')])
                writer.writerow(['Passions', ', '.join(profile_data.get('passions', [])) if profile_data.get('passions') else ''])
                writer.writerow(['Lifestyle', ', '.join(profile_data.get('lifestyle', [])) if profile_data.get('lifestyle') else ''])
                writer.writerow(['Basics', ', '.join(profile_data.get('basics', [])) if profile_data.get('basics') else ''])
                writer.writerow(['Anthem', profile_data.get('anthem', '')])
                writer.writerow(['Looking For', profile_data.get('looking_for', '')])
                writer.writerow(['Image URLs', '; '.join(profile_data.get('image_urls', []))])
                writer.writerow(['Extracted At', profile_data.get('extracted_at', '')])
        
        print(f"{GREEN} Data saved to: {output_file}")
        print(f"{YELLOW} Note: Profile was viewed but NOT swiped (left or right)")
        
        # Close browser
        session.browser.quit()
        
    except KeyboardInterrupt:
        print(f"\n{YELLOW} Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"{RED} Error scraping profile: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Tinder Profile Scraper - Extract first visible profile without swiping')
    parser.add_argument('--cookies', '--session-file', dest='cookie_file',
                        help='Path to cookie file extracted by extract_tinder_cookies.py (recommended)')
    parser.add_argument('--email', help='Email for login (fallback if cookies fail)')
    parser.add_argument('--password', help='Password for login (fallback if cookies fail)')
    parser.add_argument('--login-method', choices=['facebook', 'google'], default='facebook',
                        help='Login method (default: facebook, only used if cookies fail)')
    parser.add_argument('-f', '--format', choices=['json', 'csv'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('-o', '--output', help='Output file path (optional, auto-generated if not provided)')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode (default: True - recommended for automation)')
    parser.add_argument('--no-headless', action='store_true', dest='no_headless',
                        help='Disable headless mode (show browser window) - overrides --headless')
    
    args = parser.parse_args()
    
    # Determine headless mode: default True (for automation), but can be disabled with --no-headless
    # If --no-headless is specified, disable headless mode
    # If --headless is specified, enable headless mode
    # Default (neither specified): headless = True
    if args.no_headless:
        headless_mode = False
    elif args.headless:
        headless_mode = True
    else:
        headless_mode = True  # Default to headless for automation
    
    scrape_profile(
        email=args.email,
        password=args.password,
        login_method=args.login_method,
        cookie_file=args.cookie_file,
        output_format=args.format,
        output_file=args.output,
        headless=headless_mode
    )


if __name__ == '__main__':
    main()

