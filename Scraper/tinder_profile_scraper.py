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


def inject_cookies_to_session(session, cookies, debug_html_dir=None):
    """Inject cookies into the browser session"""
    try:
        browser = session.browser
        if debug_html_dir:
            os.makedirs(debug_html_dir, exist_ok=True)

        def save_html(label):
            if not debug_html_dir:
                return
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_label = "".join([c if c.isalnum() or c in ['-', '_'] else '_' for c in label])
            path = os.path.join(debug_html_dir, f"{ts}_{safe_label}.html")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(browser.page_source or "")
                print(f"{CYAN} Saved HTML: {path}")
            except Exception as e:
                print(f"{YELLOW} Failed to save HTML ({label}): {e}")
        
        # Navigate to Tinder first (required for Selenium cookie injection)
        print(f"{CYAN} Navigating to Tinder to inject cookies...")
        browser.get("https://www.tinder.com/?lang=en")
        time.sleep(3)
        
        # Debug: Check current URL and page title
        print(f"{CYAN} Current URL: {browser.current_url}")
        print(f"{CYAN} Page title: {browser.title[:100] if browser.title else 'None'}")
        save_html("before_cookie_injection")
        
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
        save_html("after_cookie_injection")
        
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
            save_html("login_verification_failed")
            
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


def inject_localstorage_to_session(session, localstorage_map, debug_html_dir=None):
    """Inject localStorage values for specified origins."""
    try:
        browser = session.browser
        for origin, items in (localstorage_map or {}).items():
            print(f"{CYAN} Injecting localStorage for {origin} ({len(items)} keys)...")
            browser.get(origin)
            time.sleep(2)
            for key, value in items.items():
                try:
                    browser.execute_script(
                        "window.localStorage.setItem(arguments[0], arguments[1]);", key, value
                    )
                except Exception:
                    continue

            if debug_html_dir:
                try:
                    os.makedirs(debug_html_dir, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_origin = "".join([c if c.isalnum() or c in ['-', '_'] else '_' for c in origin])
                    path = os.path.join(debug_html_dir, f"{ts}_localstorage_{safe_origin}.html")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(browser.page_source or "")
                    print(f"{CYAN} Saved HTML: {path}")
                except Exception as e:
                    print(f"{YELLOW} Failed to save HTML after localStorage inject: {e}")

        # Return to Tinder app
        browser.get("https://www.tinder.com/app/recs")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"{YELLOW} Failed to inject localStorage: {e}")
        return False


def inject_tokens_to_localstorage(session, tokens, debug_html_dir=None):
    """Inject token-like entries into localStorage and refresh."""
    try:
        if not tokens:
            return False

        browser = session.browser
        browser.get("https://tinder.com")
        time.sleep(2)

        for key, value in tokens.items():
            try:
                browser.execute_script(
                    "window.localStorage.setItem(arguments[0], arguments[1]);", key, value
                )
            except Exception:
                continue

        if debug_html_dir:
            try:
                os.makedirs(debug_html_dir, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(debug_html_dir, f"{ts}_tokens_localstorage.html")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(browser.page_source or "")
                print(f"{CYAN} Saved HTML: {path}")
            except Exception as e:
                print(f"{YELLOW} Failed to save HTML after token inject: {e}")

        browser.get("https://www.tinder.com/app/recs")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"{YELLOW} Failed to inject tokens into localStorage: {e}")
        return False


def save_session_artifacts(session, cookies_output=None, localstorage_output=None):
    """Save cookies and localStorage from current browser session."""
    try:
        if cookies_output:
            cookies = session.browser.get_cookies()
            with open(cookies_output, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            print(f"{GREEN} Saved session cookies to: {cookies_output}")

        if localstorage_output:
            try:
                session.browser.get("https://tinder.com")
                time.sleep(2)
                storage = session.browser.execute_script(
                    "var items = {}; "
                    "for (var i = 0; i < localStorage.length; i++) { "
                    "  var key = localStorage.key(i); "
                    "  items[key] = localStorage.getItem(key); "
                    "} "
                    "return items;"
                )
            except Exception:
                storage = {}

            with open(localstorage_output, 'w', encoding='utf-8') as f:
                json.dump({"https://tinder.com": storage}, f, indent=2, ensure_ascii=False)
            print(f"{GREEN} Saved session localStorage to: {localstorage_output}")
    except Exception as e:
        print(f"{YELLOW} Failed to save session artifacts: {e}")


def scrape_profile(email: str = None, password: str = None, login_method: str = 'facebook', 
                   cookie_file: str = None, output_format: str = 'json', output_file: str = None, 
                   headless: bool = True, limit: int = 1, delay: float = 1.5,
                   swipe: str = None, no_swipe: bool = False, allow_geolocation: bool = False,
                   location: str = None, distance_km: float = None, keep_browser_open: bool = False,
                   debug_html_dir: str = None, localstorage_file: str = None,
                   idb_file: str = None, manual_login: bool = False,
                   session_output: str = None, localstorage_output: str = None):
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
        
        # Enable geolocation only when explicitly requested
        allow_geolocation = bool(allow_geolocation or location or distance_km)

        # Create session (headless mode if requested)
        session = Session(headless=headless, store_session=True, allow_geolocation=allow_geolocation)
        
        logged_in = False

        # Manual login flow (one-time handoff)
        if manual_login:
            print(f"{CYAN} Manual login mode enabled.")
            print(f"{YELLOW} Please log into Tinder in the opened browser window.")
            print(f"{YELLOW} Waiting for login to complete (URL should be tinder.com/app/...)")
            max_wait_seconds = 300
            waited = 0
            while waited < max_wait_seconds:
                if session._is_logged_in():
                    print(f"{GREEN} Login detected!")
                    break
                time.sleep(2)
                waited += 2

            if not session._is_logged_in():
                print(f"{RED} Login not detected within {max_wait_seconds}s.")
                print(f"{YELLOW} Try again or use email/password fallback.")
                sys.exit(1)

            save_session_artifacts(
                session, cookies_output=session_output, localstorage_output=localstorage_output
            )
            logged_in = True

        # Try cookie-based authentication first (recommended)
        if cookie_file:
            print(f"{CYAN} Attempting cookie-based authentication...")
            cookies = load_cookies_from_file(cookie_file)
            if cookies:
                logged_in = inject_cookies_to_session(session, cookies, debug_html_dir=debug_html_dir)
                if logged_in:
                    print(f"{GREEN} Authentication successful via cookies")

        # Try localStorage injection if provided and not logged in
        if not logged_in and localstorage_file:
            try:
                with open(localstorage_file, 'r', encoding='utf-8') as f:
                    localstorage_map = json.load(f)
                if isinstance(localstorage_map, dict) and localstorage_map:
                    injected = inject_localstorage_to_session(
                        session, localstorage_map, debug_html_dir=debug_html_dir
                    )
                    if injected and session._is_logged_in():
                        logged_in = True
                        print(f"{GREEN} Authentication successful via localStorage!")
            except Exception as e:
                print(f"{YELLOW} Failed to load localStorage file: {e}")

        # Try IndexedDB token dump injection if provided
        if not logged_in and idb_file:
            try:
                with open(idb_file, 'r', encoding='utf-8') as f:
                    idb_map = json.load(f)
                tokens = idb_map.get('tokens') if isinstance(idb_map, dict) else None
                if isinstance(tokens, dict) and tokens:
                    print(f"{CYAN} Injecting {len(tokens)} token(s) from IndexedDB dump...")
                    injected = inject_tokens_to_localstorage(
                        session, tokens, debug_html_dir=debug_html_dir
                    )
                    if injected and session._is_logged_in():
                        logged_in = True
                        print(f"{GREEN} Authentication successful via IndexedDB tokens!")
            except Exception as e:
                print(f"{YELLOW} Failed to load IndexedDB file: {e}")
        
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
        
        # Optional location and distance settings
        if location:
            try:
                parts = [p.strip() for p in location.split(',')]
                if len(parts) == 2:
                    lat = float(parts[0])
                    lng = float(parts[1])
                    print(f"{CYAN} Setting custom location: {lat}, {lng}")
                    session.set_custom_location(lat, lng)
                else:
                    print(f"{YELLOW} Invalid --location format. Use \"lat,lng\" (e.g., 47.6062,-122.3321)")
            except Exception as e:
                print(f"{YELLOW} Failed to set custom location: {e}")

        if distance_km is not None:
            try:
                print(f"{CYAN} Setting distance range: {distance_km} km")
                session.set_distance_range(distance_km)
            except Exception as e:
                print(f"{YELLOW} Failed to set distance range: {e}")

        # Multi-profile loop
        profile_list = []
        total = max(1, int(limit))

        if total > 1 and no_swipe:
            print(f"{YELLOW} --no-swipe set with --limit > 1. Only the first profile will be captured.")
            total = 1

        if total == 1:
            print(f"{CYAN} Extracting first visible profile...")
            print(f"{YELLOW} Note: This will NOT swipe - only view the current profile")
        else:
            swipe_label = swipe or 'like'
            print(f"{CYAN} Extracting up to {total} profiles...")
            print(f"{YELLOW} Swipe mode: {swipe_label} (delay: {delay}s)")

        def wait_for_profile_dom(browser, timeout=12):
            end = time.time() + timeout
            while time.time() < end:
                try:
                    data = browser.execute_script(
                        "const root = document.querySelector('.profileContent') || "
                        "document.querySelector('div[role=\"dialog\"], div[aria-modal=\"true\"]') || "
                        "document.querySelector(\"div[data-keyboard-gamepad='true'][aria-hidden='false']\");"
                        "if (!root) return {ready:false,count:0};"
                        "const h2s = Array.from(root.querySelectorAll('h2'));"
                        "const norm = (s)=> (s||'').toLowerCase().replace(/\\s+/g,' ').trim();"
                        "const hasLooking = h2s.some(h=> norm(h.textContent).includes('looking for'));"
                        "const hasEssentials = h2s.some(h=> norm(h.textContent)==='essentials');"
                        "return {ready: (h2s.length>0) && (hasLooking || hasEssentials), count: h2s.length};"
                    )
                    if data and isinstance(data, dict) and data.get("ready"):
                        return True
                except Exception:
                    pass
                time.sleep(0.5)
            return False

        for i in range(total):
            geomatch = session.get_geomatch(quickload=False)
            if not geomatch or not geomatch.get_name():
                print(f"{YELLOW} No profile found or failed to extract profile data")
                break

            if debug_html_dir:
                try:
                    os.makedirs(debug_html_dir, exist_ok=True)
                    try:
                        session.browser.execute_script(
                            "const root = document.querySelector('.profileContent') || "
                            "document.querySelector('div[role=\"dialog\"], div[aria-modal=\"true\"]');"
                            "if (!root) return 0;"
                            "const buttons = Array.from(root.querySelectorAll('button,[role=\"button\"]'))"
                            ".filter(el => /view all/i.test(el.textContent||''));"
                            "const expanders = Array.from(root.querySelectorAll('[role=\"button\"][aria-expanded=\"false\"]'));"
                            "const toClick = [...new Set([...buttons, ...expanders])];"
                            "toClick.forEach(el => { try { el.click(); } catch (e) {} });"
                            "return toClick.length;"
                        )
                    except Exception:
                        pass
                    wait_for_profile_dom(session.browser, timeout=12)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = "".join([c if c.isalnum() or c in ['-', '_'] else '_' for c in (geomatch.get_name() or 'profile')])
                    path = os.path.join(debug_html_dir, f"{ts}_profile_loaded_{i+1}_{safe_name}.html")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(session.browser.page_source or "")
                    print(f"{CYAN} HTML snapshot saved: {path}")
                    try:
                        profile_html = session.browser.execute_script(
                            "const root = document.querySelector('.profileContent') || "
                            "document.querySelector('div[role=\"dialog\"], div[aria-modal=\"true\"]') || "
                            "document.querySelector(\"div[data-keyboard-gamepad='true'][aria-hidden='false']\");"
                            "return root ? root.outerHTML : '';"
                        )
                        if profile_html:
                            profile_path = os.path.join(debug_html_dir, f"{ts}_profile_dom_{i+1}_{safe_name}.html")
                            with open(profile_path, "w", encoding="utf-8") as f:
                                f.write(profile_html)
                            print(f"{CYAN} Profile DOM snapshot saved: {profile_path}")
                        else:
                            print(f"{YELLOW} Profile DOM snapshot not found for {safe_name}")
                    except Exception as e:
                        print(f"{YELLOW} Failed to save profile DOM snapshot: {e}")
                except Exception as e:
                    print(f"{YELLOW} Failed to save HTML snapshot: {e}")

            profile_data = geomatch.get_dictionary() or {}
            profile_data["id"] = geomatch.get_id()
            profile_data["extracted_at"] = datetime.now().isoformat()

            profile_list.append(profile_data)
            print(f"{GREEN} [{i+1}/{total}] Profile extracted: {profile_data['name']} ({profile_data['age']})")
            print(f"{CYAN} Bio: {profile_data['bio'][:100] if profile_data['bio'] else 'N/A'}...")
            print(f"{CYAN} Images: {len(profile_data['image_urls'])}")
            if debug_html_dir:
                try:
                    os.makedirs(debug_html_dir, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = "".join([c if c.isalnum() or c in ['-', '_'] else '_' for c in profile_data.get('name','profile')])
                    path = os.path.join(debug_html_dir, f"{ts}_profile_{i+1}_{safe_name}.html")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(session.browser.page_source or "")
                    print(f"{CYAN} Saved HTML: {path}")
                except Exception as e:
                    print(f"{YELLOW} Failed to save profile HTML: {e}")

            if i < total - 1:
                if no_swipe:
                    print(f"{YELLOW} No-swipe mode enabled. Stopping after first profile.")
                    break

                if swipe is None:
                    swipe = 'like'

                if swipe == 'like':
                    session.like(amount=1, sleep=delay, randomize_sleep=False)
                elif swipe == 'dislike':
                    session.dislike(amount=1)
                    time.sleep(delay)
                elif swipe == 'superlike':
                    session.superlike(amount=1)
                    time.sleep(delay)
                else:
                    print(f"{YELLOW} Unknown swipe mode: {swipe}. Stopping.")
                    break

        if len(profile_list) == 0:
            print(f"{RED} Error: Could not extract profile data")
            print(f"{YELLOW} Make sure you are logged in and there is a profile visible")
            sys.exit(1)

        # Save output
        if not output_file:
            if len(profile_list) == 1:
                profile_name = profile_list[0]['name'].replace(' ', '_') if profile_list[0].get('name') else 'profile'
                output_file = f"tinder_profile_{profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
            else:
                output_file = f"tinder_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"

        if output_format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                if len(profile_list) == 1:
                    json.dump(profile_list[0], f, indent=2, ensure_ascii=False)
                else:
                    json.dump(profile_list, f, indent=2, ensure_ascii=False)
        else:  # CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if len(profile_list) == 1:
                    profile_data = profile_list[0]
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
                else:
                    writer.writerow([
                        'id', 'name', 'age', 'bio', 'work', 'study', 'home', 'gender',
                        'distance', 'passions', 'lifestyle', 'basics', 'anthem', 'looking_for',
                        'instagram', 'image_urls', 'extracted_at'
                    ])
                    for profile_data in profile_list:
                        writer.writerow([
                            profile_data.get('id', ''),
                            profile_data.get('name', ''),
                            profile_data.get('age', ''),
                            profile_data.get('bio', ''),
                            profile_data.get('work', ''),
                            profile_data.get('study', ''),
                            profile_data.get('home', ''),
                            profile_data.get('gender', ''),
                            profile_data.get('distance', ''),
                            ', '.join(profile_data.get('passions', []) or []),
                            ', '.join(profile_data.get('lifestyle', []) or []),
                            ', '.join(profile_data.get('basics', []) or []),
                            profile_data.get('anthem', ''),
                            profile_data.get('looking_for', ''),
                            profile_data.get('instagram', ''),
                            '; '.join(profile_data.get('image_urls', []) or []),
                            profile_data.get('extracted_at', '')
                        ])

        print(f"{GREEN} Data saved to: {output_file}")
        if len(profile_list) == 1:
            print(f"{YELLOW} Note: Profile was viewed but NOT swiped (left or right)")

        # Close browser unless user wants it open
        if keep_browser_open:
            print(f"{YELLOW} Keeping browser open (debug mode). Press Ctrl+C to exit.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
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
    parser.add_argument('--limit', type=int, default=1,
                        help='Maximum number of profiles to extract (default: 1)')
    parser.add_argument('--delay', type=float, default=1.5,
                        help='Delay between swipes in seconds (default: 1.5)')
    parser.add_argument('--swipe', choices=['like', 'dislike', 'superlike'], default=None,
                        help='Swipe action between profiles (default: like when limit > 1)')
    parser.add_argument('--no-swipe', action='store_true',
                        help='Extract profile data without swiping (single profile only)')
    parser.add_argument('--allow-geolocation', action='store_true',
                        help='Allow geolocation permission for Tinder (required for location overrides)')
    parser.add_argument('--location',
                        help='Set custom location as "lat,lng" (e.g., 47.6062,-122.3321)')
    parser.add_argument('--distance-km', type=float,
                        help='Set distance range in kilometers (requires location permission)')
    parser.add_argument('--keep-browser-open', action='store_true',
                        help='Keep browser open after scraping completes')
    parser.add_argument('--debug-html-dir',
                        help='Save page HTML snapshots to this directory for debugging')
    parser.add_argument('--localstorage',
                        help='Path to localStorage JSON file to inject (optional)')
    parser.add_argument('--idb',
                        help='Path to IndexedDB token dump JSON file (optional)')
    parser.add_argument('--manual-login', action='store_true',
                        help='Open browser for manual login and save session artifacts')
    parser.add_argument('--session-output',
                        help='Output file path for session cookies (manual login)')
    parser.add_argument('--localstorage-output',
                        help='Output file path for localStorage JSON (manual login)')
    
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
        headless=headless_mode,
        limit=args.limit,
        delay=args.delay,
        swipe=args.swipe,
        no_swipe=args.no_swipe,
        allow_geolocation=args.allow_geolocation,
        location=args.location,
        distance_km=args.distance_km,
        keep_browser_open=args.keep_browser_open,
        debug_html_dir=args.debug_html_dir,
        localstorage_file=args.localstorage,
        idb_file=args.idb,
        manual_login=args.manual_login,
        session_output=args.session_output,
        localstorage_output=args.localstorage_output
    )


if __name__ == '__main__':
    main()
