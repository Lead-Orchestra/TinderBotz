from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import re
from tinderbotz.helpers.xpaths import content
from datetime import datetime

class GeomatchHelper:

    delay = 5

    HOME_URL = "https://www.tinder.com/app/recs"

    def __init__(self, browser):
        self.browser = browser
        if "/app/recs" not in self.browser.current_url:
            self._get_home_page()

    def like(self)->bool:
        try:
            if self._click_action_button("like"):
                return True

            action = ActionChains(self.browser)
            action.send_keys(Keys.ARROW_RIGHT).perform()
            return True

        except (TimeoutException, ElementClickInterceptedException):
            self._get_home_page()

        return False

    def dislike(self):
        try:
            if self._click_action_button("dislike"):
                return

            action = ActionChains(self.browser)
            action.send_keys(Keys.ARROW_LEFT).perform()
        except (TimeoutException, ElementClickInterceptedException):
            self._get_home_page()

    def superlike(self):
        try:
            if self._click_action_button("superlike"):
                time.sleep(1)
                return

            if 'profile' in self.browser.current_url:
                xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div[1]/div[2]/div/div/div[3]/div/div/div/button'
                WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
                    (By.XPATH, xpath)))
                superlike_button = self.browser.find_element(By.XPATH, xpath)
                superlike_button.click()
            else:
                xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div[1]'
                WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
                    (By.XPATH, xpath)))
                card = self.browser.find_element(By.XPATH, xpath)
                action = ActionChains(self.browser)
                action.drag_and_drop_by_offset(card, 0, -200).perform()

            time.sleep(1)

        except (TimeoutException, ElementClickInterceptedException):
            self._get_home_page()

    def _click_action_button(self, action):
        labels = {
            "like": ["Like"],
            "dislike": ["Nope", "Dislike"],
            "superlike": ["Super Like", "Superlike"]
        }.get(action, [])

        testids = {
            "like": ["like", "gamepadLike", "recLike"],
            "dislike": ["nope", "gamepadDislike", "recNope"],
            "superlike": ["superlike", "gamepadSuperlike", "recSuperLike"]
        }.get(action, [])

        selectors = []
        for label in labels:
            selectors.extend([
                f"button[aria-label='{label}']",
                f"div[role='button'][aria-label='{label}']"
            ])
        for tid in testids:
            selectors.extend([
                f"button[data-testid='{tid}']",
                f"div[role='button'][data-testid='{tid}']"
            ])

        for selector in selectors:
            try:
                button = WebDriverWait(self.browser, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                button.click()
                return True
            except Exception:
                continue

        return False

    def _open_profile(self, second_try=False):
        if self._is_profile_opened(): return;
        try:
            #xpath = '//button'
            #WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
            #    (By.XPATH, xpath)))
            #buttons = self.browser.find_elements(By.XPATH, xpath)

            #for button in buttons:
            #    # some buttons might not have a span as subelement
            #    try:
            #        text_span = button.find_element(By.XPATH, './/span').text
            #        if 'open profile' in text_span.lower():
            #            button.click()
            #            break
            #    except:
            #        continue

            # Prefer clicking the "Open profile" button within the active card
            try:
                card = self._get_active_card()
                if card:
                    buttons = card.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        try:
                            span = btn.find_element(By.XPATH, ".//span[contains(., 'Open profile')]")
                            if span:
                                btn.click()
                                return
                        except Exception:
                            continue
            except Exception:
                pass

            # Try explicit open-profile selectors (Sparks layout)
            try:
                for selector in [
                    "button[aria-label*='Open profile' i]",
                    "button[data-testid*='profileOpen' i]",
                    "button[data-testid*='openProfile' i]",
                    "div[role='button'][aria-label*='Open profile' i]",
                ]:
                    try:
                        btn = WebDriverWait(self.browser, 1).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        btn.click()
                        time.sleep(0.6)
                        if self._is_profile_opened():
                            return
                    except Exception:
                        continue
            except Exception:
                pass

            # Fallback: keyboard shortcut
            action = ActionChains(self.browser)
            action.send_keys(Keys.ARROW_UP).perform()
            time.sleep(0.6)

            #time.sleep(1)

        except (ElementClickInterceptedException, TimeoutException):
            if not second_try:
                print("Trying again to locate the profile info button in a few seconds")
                time.sleep(2)
                self._open_profile(second_try=True)
            else:
                self.browser.refresh()
        except:
            self.browser.get(self.HOME_URL)
            if not second_try:
                self._open_profile(second_try=True)

    def _get_active_card(self):
        try:
            # Prefer the currently visible card
            elements = self.browser.find_elements(By.CSS_SELECTOR, "div[data-keyboard-gamepad='true'][aria-hidden='false']")
            if elements:
                return elements[0]
            # Fallback: card without aria-hidden (some layouts)
            elements = self.browser.find_elements(By.CSS_SELECTOR, "div[data-keyboard-gamepad='true']:not([aria-hidden])")
            if elements:
                return elements[0]
            # Last resort: any card in the stack
            elements = self.browser.find_elements(By.CSS_SELECTOR, "div[data-keyboard-gamepad='true']")
            if elements:
                return elements[0]
        except Exception:
            return None
        return None

    def _is_valid_name(self, name):
        if not name:
            return False
        value = name.strip()
        if len(value) < 2:
            return False
        lower = value.lower()
        if any(bad in lower for bad in [
            "rewind", "super like", "superlike", "boost", "upgrade",
            "passport", "tinder", "like", "nope", "report", "block"
        ]):
            return False
        if any(char.isdigit() for char in value):
            return False
        return True

    def _expand_profile_sections(self, scope=None):
        try:
            clicked = self.browser.execute_script(
                """
                const root = arguments[0] || document;
                const buttons = Array.from(root.querySelectorAll('button,[role="button"]'))
                    .filter(el => /view all/i.test(el.textContent || ''));
                const expanders = Array.from(root.querySelectorAll('[role="button"][aria-expanded="false"]'));
                const toClick = [...new Set([...buttons, ...expanders])];
                toClick.forEach(el => {
                    try { el.click(); } catch (e) {}
                });
                return toClick.length;
                """,
                scope
            )
            if clicked:
                time.sleep(0.3)
        except Exception:
            pass

    def wait_for_profile_ready(self, timeout=12):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if not self._is_profile_opened():
                    self._open_profile()
                name = self.get_name()
                if self._is_valid_name(name):
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def wait_for_profile_content(self, timeout=12):
        end = time.time() + timeout
        while time.time() < end:
            try:
                scope, _ = self._get_profile_scope(open_if_needed=True)
                if scope:
                    data = self.browser.execute_script(
                        """
                        const root = arguments[0];
                        if (!root) return {count: 0, ready: false};
                        const h2s = Array.from(root.querySelectorAll('h2'));
                        const norm = (s)=> (s||'').toLowerCase().replace(/\\s+/g,' ').trim();
                        const hasLooking = h2s.some(h=> norm(h.textContent).includes('looking for'));
                        const hasEssentials = h2s.some(h=> norm(h.textContent)==='essentials');
                        return {count: h2s.length, ready: (h2s.length>0) && (hasLooking || hasEssentials)};
                        """,
                        scope
                    )
                    if data and isinstance(data, dict) and data.get("ready"):
                        return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _get_profile_scope(self, open_if_needed=False):
        active_name = None
        # Prefer the expanded profile content container when available
        try:
            content = self.browser.find_elements(By.CSS_SELECTOR, "div.profileContent")
            if content:
                return content[0], active_name
        except Exception:
            pass
        try:
            card = self._get_active_card()
            if card:
                name_el = card.find_elements(By.CSS_SELECTOR, "[itemprop='name']")
                if name_el and name_el[0].text:
                    active_name = name_el[0].text.strip()
        except Exception:
            active_name = None

        if open_if_needed and not self._is_profile_opened():
            self._open_profile()
            try:
                WebDriverWait(self.browser, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog'], div[aria-modal='true']"))
                )
            except Exception:
                pass

        # Try to locate a modal/dialog that contains the active name
        try:
            dialogs = self.browser.find_elements(By.CSS_SELECTOR, "div[role='dialog'], div[aria-modal='true']")
            for dlg in dialogs:
                try:
                    if active_name and active_name in (dlg.text or ""):
                        return dlg, active_name
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback: scope to the active card's ancestor container
        if active_name:
            try:
                name_candidates = self.browser.find_elements(By.CSS_SELECTOR, "[itemprop='name']")
                for cand in name_candidates:
                    if (cand.text or "").strip() == active_name:
                        try:
                            return cand.find_element(By.XPATH, "./ancestor::button[1]"), active_name
                        except Exception:
                            try:
                                return cand.find_element(By.XPATH, "./ancestor::div[1]"), active_name
                            except Exception:
                                return self.browser, active_name
            except Exception:
                pass

        return self.browser, active_name

    def get_socials(self, bio=None):
        if not self._is_profile_opened():
            self._open_profile()

        socials = {
            "instagram": None,
            "tiktok": None,
            "snapchat": None,
            "twitter": None,
            "onlyfans": None,
            "spotify": None,
            "links": []
        }

        # From bio text
        if bio:
            handle_match = re.findall(r'@([A-Za-z0-9_\\.]{3,})', bio)
            if handle_match and not socials["instagram"]:
                socials["instagram"] = handle_match[0]

        # From modal/card links/text
        try:
            data = self.browser.execute_script(
                """
                const root = document.querySelector("div[role='dialog'], div[aria-modal='true']") 
                    || document.querySelector("div[data-keyboard-gamepad='true'][aria-hidden='false']");
                if (!root) return null;
                const links = Array.from(root.querySelectorAll('a[href]')).map(a => a.href);
                const text = root.innerText || '';
                return { links, text };
                """
            )
            if data and isinstance(data, dict):
                links = data.get("links") or []
                text = data.get("text") or ""
                for link in links:
                    if link and link not in socials["links"]:
                        socials["links"].append(link)
                    lower = (link or "").lower()
                    if "instagram.com" in lower and not socials["instagram"]:
                        socials["instagram"] = link.rstrip('/').split('/')[-1]
                    if "tiktok.com" in lower and not socials["tiktok"]:
                        socials["tiktok"] = link.rstrip('/').split('/')[-1].lstrip('@')
                    if "snapchat.com" in lower and not socials["snapchat"]:
                        socials["snapchat"] = link.rstrip('/').split('/')[-1]
                    if ("twitter.com" in lower or "x.com" in lower) and not socials["twitter"]:
                        socials["twitter"] = link.rstrip('/').split('/')[-1]
                    if "onlyfans.com" in lower and not socials["onlyfans"]:
                        socials["onlyfans"] = link.rstrip('/').split('/')[-1]
                    if "spotify.com" in lower and not socials["spotify"]:
                        socials["spotify"] = link

                # Text-based hints (e.g., "Instagram" section)
                if text:
                    if not socials["instagram"]:
                        m = re.search(r'instagram\\s*@?([A-Za-z0-9_\\.]{3,})', text, re.I)
                        if m:
                            socials["instagram"] = m.group(1)
                    if not socials["tiktok"]:
                        m = re.search(r'tiktok\\s*@?([A-Za-z0-9_\\.]{3,})', text, re.I)
                        if m:
                            socials["tiktok"] = m.group(1)
                    if not socials["snapchat"]:
                        m = re.search(r'snap(chat)?\\s*@?([A-Za-z0-9_\\.]{3,})', text, re.I)
                        if m:
                            socials["snapchat"] = m.group(2)
        except Exception:
            pass

        return socials

    def get_name(self):
        if self._is_profile_opened():
            try:
                scope, _ = self._get_profile_scope(open_if_needed=True)
                if scope:
                    name_text = self.browser.execute_script(
                        """
                        const root = arguments[0];
                        const span = root.querySelector('h1 span[class*="Pend"]');
                        if (span && span.textContent) return span.textContent.trim();
                        const h1 = root.querySelector('h1[aria-label]');
                        if (h1) {
                            const label = h1.getAttribute('aria-label') || '';
                            const match = label.match(/^([^0-9]+?)\\s*(\\d|years|year)/i);
                            if (match && match[1]) return match[1].trim();
                        }
                        const h1b = root.querySelector('h1');
                        if (h1b && h1b.textContent) return h1b.textContent.trim().split('\\n')[0];
                        return null;
                        """,
                        scope
                    )
                    if name_text and self._is_valid_name(name_text):
                        return name_text
            except Exception:
                pass

        if not self._is_profile_opened():
            self._open_profile()

        try:
            xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/h1'
            # wait for element to appear
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
                (By.XPATH, xpath)))

            element = self.browser.find_element(By.XPATH, xpath)

            name = element.text
            if not name:
                xpath2 = f'{content}/div/div[1]/div/main/div[1]/div/div/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div/h1'
                element2 = self.browser.find_element(By.XPATH, xpath2)
                name = element2.text

            if self._is_valid_name(name):
                return name
        except Exception as e:
            pass

        # Fallback: active card name (only if modal lookup failed)
        try:
            card = self._get_active_card()
            if card:
                name_el = card.find_elements(By.CSS_SELECTOR, "[itemprop='name']")
                if name_el and name_el[0].text:
                    candidate = name_el[0].text.strip()
                    if self._is_valid_name(candidate):
                        return candidate
        except Exception:
            pass

        # Fallback: parse from aria-label on carousel
        try:
            sections = self.browser.find_elements(By.CSS_SELECTOR, "section[aria-label*='photos']")
            for section in sections:
                label = section.get_attribute("aria-label") or ""
                if label:
                    normalized = label.replace("’", "'")
                    if "'s photos" in normalized:
                        candidate = normalized.split("'s photos")[0].strip()
                        if self._is_valid_name(candidate):
                            return candidate
        except Exception:
            pass

        # Fallback: parse from card text
        try:
            text = self.browser.execute_script(
                "const card=document.querySelector('.recsCardboard__cards'); return card?card.innerText:'';"
            )
            if text:
                # Try to find a name at the start of the text
                first_line = text.strip().split("\n")[0]
                if first_line:
                    candidate = first_line.split(",")[0].strip()
                    if self._is_valid_name(candidate):
                        return candidate
        except Exception:
            pass

    def get_age(self):
        try:
            card = self._get_active_card()
            if card:
                age_el = card.find_elements(By.CSS_SELECTOR, "[itemprop='age']")
                if age_el and age_el[0].text:
                    return age_el[0].text.strip()
        except Exception:
            pass

        if not self._is_profile_opened():
            self._open_profile()

        age = None

        try:
            xpath = f'{content}/div/div[1]/div/main/div[1]/div/div/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/span'

            # wait for element to appear
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(
                (By.XPATH, xpath)))

            element = self.browser.find_element(By.XPATH, xpath)
            try:
                age = int(element.text)
            except ValueError:
                age = None

        except:
            pass

        # Fallback: parse age from card text
        try:
            name = self.get_name()
            text = self.browser.execute_script(
                "const card=document.querySelector('.recsCardboard__cards'); return card?card.innerText:'';"
            )
            if text:
                if name:
                    pattern = re.compile(rf"{re.escape(name)}\\s*,?\\s*(\\d{{2}})")
                    match = pattern.search(text)
                    if match:
                        return int(match.group(1))
                # Generic age fallback (first 2-digit number)
                match = re.search(r"\\b(1[8-9]|[2-5]\\d)\\b", text)
                if match:
                    return int(match.group(1))
        except Exception:
            pass

        # Sparks layout: read aria-label on h1 when present
        try:
            scope, _ = self._get_profile_scope(open_if_needed=True)
            js_age = self.browser.execute_script(
                """
                const root = arguments[0] || document;
                const h1 = root.querySelector('h1[aria-label]');
                if (!h1) return null;
                const label = h1.getAttribute('aria-label') || '';
                const match = label.match(/\\b(1[8-9]|[2-5]\\d)\\b/);
                return match ? parseInt(match[1], 10) : null;
                """,
                scope
            )
            if js_age:
                return int(js_age)
        except Exception:
            pass

        return age

    def is_verified(self):
        if not self._is_profile_opened():
            self._open_profile()

        xpath_badge = f'{content}/div/div[1]/div/main/div[1]/div/div/div[1]/div[1]/div/div[2]/div[1]/div/div[1]/div[2]'
        try:
            self.browser.find_element(By.XPATH, xpath_badge)
            return True
        except Exception:
            pass

        # Sparks layout: check for "Photo verified" text in profile scope
        try:
            scope, _ = self._get_profile_scope(open_if_needed=True)
            verified = self.browser.execute_script(
                """
                const root = arguments[0] || document;
                return (root.textContent || '').toLowerCase().includes('photo verified');
                """,
                scope
            )
            return bool(verified)
        except Exception:
            return False

    _WORK_SVG_PATH = "M7.15 3.434h5.7V1.452a.728.728 0 0 0-.724-.732H7.874a.737.737 0 0 0-.725.732v1.982z"
    _STUDYING_SVG_PATH = "M11.87 5.026L2.186 9.242c-.25.116-.25.589 0 .705l.474.204v2.622a.78.78 0 0 0-.344.657c0 .42.313.767.69.767.378 0 .692-.348.692-.767a.78.78 0 0 0-.345-.657v-2.322l2.097.921a.42.42 0 0 0-.022.144v3.83c0 .45.27.801.626 1.101.358.302.842.572 1.428.804 1.172.46 2.755.776 4.516.776 1.763 0 3.346-.317 4.518-.777.586-.23 1.07-.501 1.428-.803.355-.3.626-.65.626-1.1v-3.83a.456.456 0 0 0-.022-.145l3.264-1.425c.25-.116.25-.59 0-.705L12.13 5.025c-.082-.046-.22-.017-.26 0v.001zm.13.767l8.743 3.804L12 13.392 3.257 9.599l8.742-3.806zm-5.88 5.865l5.75 2.502a.319.319 0 0 0 .26 0l5.75-2.502v3.687c0 .077-.087.262-.358.491-.372.29-.788.52-1.232.68-1.078.426-2.604.743-4.29.743s-3.212-.317-4.29-.742c-.444-.161-.86-.39-1.232-.68-.273-.23-.358-.415-.358-.492v-3.687z"
    _HOME_SVG_PATH = "M19.695 9.518H4.427V21.15h15.268V9.52zM3.109 9.482h17.933L12.06 3.709 3.11 9.482z"
    _LOCATION_SVG_PATH = "M11.436 21.17l-.185-.165a35.36 35.36 0 0 1-3.615-3.801C5.222 14.244 4 11.658 4 9.524 4 5.305 7.267 2 11.436 2c4.168 0 7.437 3.305 7.437 7.524 0 4.903-6.953 11.214-7.237 11.48l-.2.167zm0-18.683c-3.869 0-6.9 3.091-6.9 7.037 0 4.401 5.771 9.927 6.897 10.972 1.12-1.054 6.902-6.694 6.902-10.95.001-3.968-3.03-7.059-6.9-7.059h.001z"
    _LOCATION_SVG_PATH_2 = "M11.445 12.5a2.945 2.945 0 0 1-2.721-1.855 3.04 3.04 0 0 1 .641-3.269 2.905 2.905 0 0 1 3.213-.645 3.003 3.003 0 0 1 1.813 2.776c-.006 1.653-1.322 2.991-2.946 2.993zm0-5.544c-1.378 0-2.496 1.139-2.498 2.542 0 1.404 1.115 2.544 2.495 2.546a2.52 2.52 0 0 0 2.502-2.535 2.527 2.527 0 0 0-2.499-2.545v-.008z"
    _GENDER_SVG_PATH = "M15.507 13.032c1.14-.952 1.862-2.656 1.862-5.592C17.37 4.436 14.9 2 11.855 2 8.81 2 6.34 4.436 6.34 7.44c0 3.07.786 4.8 2.02 5.726-2.586 1.768-5.054 4.62-4.18 6.204 1.88 3.406 14.28 3.606 15.726 0 .686-1.71-1.828-4.608-4.4-6.338"

    def get_row_data(self):
        rowdata = {}

        # JS-based extraction from the active card (more reliable than XPath in dynamic layouts)
        try:
            data = self.browser.execute_script(
                """
                const card = document.querySelector("div[data-keyboard-gamepad='true'][aria-hidden='false']");
                if (!card) return null;
                const homeEl = card.querySelector("[itemprop='homeLocation']");
                const textNodes = Array.from(card.querySelectorAll("div, span")).map(e => (e.textContent || "").trim()).filter(Boolean);
                const distanceText = textNodes.find(t => /miles? away|kilometres? away|kilometers? away|km away/i.test(t));
                const recentlyActive = textNodes.some(t => /recently active/i.test(t));
                const verified = Array.from(card.querySelectorAll('title')).some(t => /photo verified/i.test(t.textContent || ''));
                const rowTexts = Array.from(card.querySelectorAll("div[class*='Row']")).map(e => (e.textContent || "").trim()).filter(Boolean);
                return {
                    home: homeEl ? homeEl.textContent : null,
                    distanceText: distanceText || null,
                    recentlyActive,
                    verified,
                    rowTexts: rowTexts
                };
                """
            )
            if data:
                home_text = (data.get("home") or "").strip() if isinstance(data, dict) else (data.get("home") if data else None)
                if home_text and home_text.lower().startswith("lives in "):
                    home_text = home_text[len("lives in "):].strip()
                if home_text:
                    rowdata['home'] = home_text
                dist_text = data.get("distanceText") if isinstance(data, dict) else None
                if dist_text:
                    m = re.search(r'(\d+)', dist_text)
                    if m:
                        try:
                            rowdata['distance'] = int(m.group(1))
                        except ValueError:
                            pass
                    elif "less than" in dist_text.lower():
                        rowdata['distance'] = 1
                row_texts = data.get("rowTexts") if isinstance(data, dict) else []
                if isinstance(data, dict):
                    if data.get("recentlyActive"):
                        rowdata["recently_active"] = True
                    if data.get("verified"):
                        rowdata["verified"] = True
                if row_texts:
                    for t in row_texts:
                        if not t:
                            continue
                        lower = t.lower()
                        if not rowdata.get('home') and lower.startswith("lives in "):
                            rowdata['home'] = t[len("lives in "):].strip()
                            continue
                        if not rowdata.get('distance') and ("mile" in lower or "kilometre" in lower or "kilometer" in lower or "km away" in lower):
                            m = re.search(r'(\d+)', t)
                            if m:
                                try:
                                    rowdata['distance'] = int(m.group(1))
                                except ValueError:
                                    pass
                            elif "less than" in lower:
                                rowdata['distance'] = 1
                            continue
                        if not rowdata.get('gender'):
                            if t in ["Woman", "Man", "Non-binary", "Nonbinary", "Transgender", "Agender", "Genderfluid", "Genderqueer"]:
                                rowdata['gender'] = t
                                continue
                        if not rowdata.get('study'):
                            if ("university" in lower) or ("college" in lower) or ("school" in lower) or ("studied" in lower):
                                rowdata['study'] = t
                                continue
                        if not rowdata.get('work'):
                            if (" at " in lower) and ("university" not in lower) and ("college" not in lower) and ("school" not in lower):
                                rowdata['work'] = t
                                continue
        except Exception:
            pass

        # Sparks essentials (profile modal) parsing
        try:
            scope, _ = self._get_profile_scope(open_if_needed=True)
            essentials = self.browser.execute_script(
                """
                const root = arguments[0];
                if (!root) return { items: [], verified: false };
                const h2s = Array.from(root.querySelectorAll('h2'));
                const norm = (s) => (s || '').toLowerCase().replace(/\\s+/g, ' ').trim();
                const textOf = (el) => (el && (el.textContent || '').trim()) || '';
                for (const h2 of h2s) {
                    if (norm(textOf(h2)) !== 'essentials') continue;
                    const section = h2.closest('section') || h2.closest('div');
                    if (!section) break;
                    const items = Array.from(section.querySelectorAll('li')).map((li) => {
                        const v = textOf(li.querySelector('div[class*=\"Typs(body-1-regular)\"]')) || textOf(li);
                        return v;
                    }).filter(Boolean);
                    const verified = Array.from(section.querySelectorAll('title')).some(t => /photo verified/i.test(t.textContent || ''))
                        || /photo verified/i.test(textOf(section));
                    return { items, verified };
                }
                return { items: [], verified: false };
                """,
                scope
            )
            if essentials and isinstance(essentials, dict):
                if essentials.get("verified"):
                    rowdata["verified"] = True
                items = essentials.get("items") or []
                for item in items:
                    if not item:
                        continue
                    lower = item.lower()
                    height_match = re.search(r'(\\d{2,3})\\s*cm', lower)
                    if height_match and not rowdata.get('height_cm'):
                        try:
                            rowdata['height_cm'] = int(height_match.group(1))
                        except ValueError:
                            pass
                    if not rowdata.get('study') and any(token in lower for token in ["student at", "university", "college", "school"]):
                        rowdata['study'] = item.strip()
                        continue
                    if not rowdata.get('home') and lower.startswith("lives in "):
                        rowdata['home'] = item[len("lives in "):].strip()
                        continue
                    if not rowdata.get('distance') and ("mile" in lower or "kilometre" in lower or "kilometer" in lower or "km away" in lower):
                        m = re.search(r'(\\d+)', item)
                        if m:
                            try:
                                rowdata['distance'] = int(m.group(1))
                            except ValueError:
                                pass
                        elif "less than" in lower:
                            rowdata['distance'] = 1
                        continue
                    if not rowdata.get('gender'):
                        if lower in [
                            "woman", "man", "non-binary", "nonbinary", "transgender", "agender",
                            "genderfluid", "genderqueer", "bisexual", "straight", "gay", "lesbian",
                            "pansexual", "queer", "asexual"
                        ]:
                            rowdata['gender'] = item
                            continue
                    if not rowdata.get('study'):
                        if ("student at " in lower) or ("at uni" in lower) or ("university" in lower) or ("college" in lower) or ("school" in lower):
                            rowdata['study'] = item
                            continue
                    if not rowdata.get('work'):
                        if not re.search(r'\\d', item) and len(item.split()) <= 4:
                            rowdata['work'] = item
        except Exception:
            pass

        if rowdata:
            return rowdata

        # Try to parse from the active card on the recs page
        try:
            card = self._get_active_card()
            if card:
                try:
                    home_el = card.find_element(By.CSS_SELECTOR, "[itemprop='homeLocation']")
                    home_text = home_el.text.strip()
                    if home_text.lower().startswith("lives in "):
                        home_text = home_text[len("lives in "):].strip()
                    if home_text:
                        rowdata['home'] = home_text
                except Exception:
                    pass

                try:
                    distance_els = card.find_elements(
                        By.XPATH,
                        ".//*[contains(text(), 'miles away') or contains(text(), 'kilometres away') or contains(text(), 'kilometers away') or contains(text(), 'km away') or contains(text(), 'mile away')]"
                    )
                    for el in distance_els:
                        value = (el.text or "").strip()
                        if value:
                            distance = None
                            # Extract first number from distance text
                            m = re.search(r'(\d+)', value)
                            if m:
                                try:
                                    distance = int(m.group(1))
                                except ValueError:
                                    distance = None
                            else:
                                if "less than" in value.lower():
                                    distance = 1
                            if distance is not None:
                                rowdata['distance'] = distance
                                break
                except Exception:
                    pass
        except Exception:
            pass

        if rowdata:
            return rowdata

        scope, _ = self._get_profile_scope(open_if_needed=True)
        self._expand_profile_sections(scope)
        self._expand_profile_sections(scope)
        self._expand_profile_sections(scope)

        xpath = './/div[contains(@class,"Row")]'
        rows = scope.find_elements(By.XPATH, xpath)

        for row in rows:
            value = None
            try:
                value = row.find_element(By.XPATH, ".//div[2]").text
            except Exception:
                try:
                    value = row.text
                except Exception:
                    value = None

            svg = None
            try:
                svg = row.find_element(By.XPATH, ".//*[starts-with(@d, 'M')]").get_attribute('d')
            except Exception:
                svg = None

            if svg:
                if svg == self._WORK_SVG_PATH:
                    rowdata['work'] = value
                if svg == self._STUDYING_SVG_PATH:
                    rowdata['study'] = value
                if svg == self._HOME_SVG_PATH:
                    home_value = value
                    if home_value and home_value.lower().startswith("lives in "):
                        home_value = home_value[len("lives in "):].strip()
                    rowdata['home'] = home_value
                if svg == self._GENDER_SVG_PATH:
                    rowdata['gender'] = value
                if svg == self._LOCATION_SVG_PATH or svg == self._LOCATION_SVG_PATH_2:
                    distance = value.split(' ')[0] if value else None
                    try:
                        distance = int(distance)
                    except TypeError:
                        distance = 1
                    except ValueError:
                        distance = 1 if value and "less than" in value.lower() else None
                    rowdata['distance'] = distance

            # Fallbacks based on text/attributes
            try:
                home_el = row.find_elements(By.CSS_SELECTOR, "[itemprop='homeLocation']")
                if home_el:
                    home_text = (home_el[0].text or "").strip()
                    if home_text.lower().startswith("lives in "):
                        home_text = home_text[len("lives in "):].strip()
                    if home_text:
                        rowdata['home'] = home_text
            except Exception:
                pass

            if value:
                lower = value.lower()
                if "mile" in lower or "kilometre" in lower or "kilometer" in lower or "km away" in lower:
                    m = re.search(r'(\d+)', value)
                    if m:
                        try:
                            rowdata['distance'] = int(m.group(1))
                        except ValueError:
                            pass
                    elif "less than" in lower:
                        rowdata['distance'] = 1

        return rowdata

    def get_bio_and_passions(self):
        bio = None
        looking_for = None
        prompts = []
        more_about = []
        looking_for_tags = []

        infoItems = {
            "passions": [],
            "lifestyle": [],
            "basics": []
        }

        anthem = None

        lifestyle = []

        # Try to parse from the active card on the recs page
        try:
            card = self._get_active_card()
            if card:
                try:
                    headings = card.find_elements(By.TAG_NAME, "h2")
                    for h in headings:
                        label = (h.text or "").strip().lower()
                        if not label:
                            continue
                        if label in ["about me", "bio"]:
                            try:
                                parent = h.find_element(By.XPATH, "./..")
                                content = parent.find_element(By.XPATH, "./following-sibling::*[1]")
                                text = content.text.strip()
                                if text:
                                    bio = text
                            except Exception:
                                pass
                        if label in ["interests", "passions", "lifestyle", "basics"]:
                            try:
                                parent = h.find_element(By.XPATH, "./..")
                                container = parent.find_element(By.XPATH, "./following-sibling::*[1]")
                                chips = []
                                for span in container.find_elements(By.TAG_NAME, "span"):
                                    text = (span.text or "").strip()
                                    if text:
                                        chips.append(text)
                                if chips:
                                    if label == "interests" or label == "passions":
                                        infoItems["passions"] = chips
                                    elif label == "lifestyle":
                                        infoItems["lifestyle"] = chips
                                    elif label == "basics":
                                        infoItems["basics"] = chips
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

        scope, _ = self._get_profile_scope(open_if_needed=True)

        # Sparks layout extraction (profile modal content)
        try:
            spark = self.browser.execute_script(
                """
                const root = arguments[0];
                const out = { about: null, looking_for: null, interests: [], lifestyle: [], more_about: [], essentials: [], looking_for_tags: [], prompts: [] };
                if (!root) return out;
                const norm = (s) => (s || '').toLowerCase().replace(/\\s+/g, ' ').trim();
                const textOf = (el) => (el && (el.textContent || '').trim()) || '';

                const headings = Array.from(root.querySelectorAll('h2'));
                for (const h2 of headings) {
                    const title = norm(textOf(h2));
                    if (!title) continue;
                    const section = h2.closest('section') || h2.closest('div');
                    if (!section) continue;
                    const container = section.closest('section') || section.parentElement || section;

                    if (title === 'about me') {
                        const aboutEl = container.querySelector('div[class*="Typs(body-1-regular)"]') || container;
                        const txt = textOf(aboutEl);
                        if (txt) out.about = txt;
                    } else if (title === 'looking for') {
                        const primary = container.querySelector('span[class*="Typs(display-3-strong)"], div[class*="Typs(display-3-strong)"]');
                        const primaryText = textOf(primary);
                        if (primaryText) out.looking_for = primaryText;

                        const chips = Array.from(container.querySelectorAll('div[class*="Bdrs(30px)"]'))
                            .map((el) => textOf(el))
                            .filter(Boolean);
                        for (const chip of chips) {
                            if (!out.looking_for_tags.includes(chip)) out.looking_for_tags.push(chip);
                        }
                    } else if (title === 'interests') {
                        const chips = Array.from(container.querySelectorAll('span[class*="C($c-ds-text-passions-shared)"]'))
                            .map((el) => textOf(el))
                            .filter((t) => t && t.length < 80);
                        for (const chip of chips) {
                            if (!out.interests.includes(chip)) out.interests.push(chip);
                        }
                    } else if (title === 'lifestyle') {
                        const items = Array.from(container.querySelectorAll('li'));
                        for (const li of items) {
                            const label = textOf(li.querySelector('h3'));
                            const value = textOf(li.querySelector('div[class*="Typs(body-1-regular)"]'));
                            if (label && value) {
                                out.lifestyle.push(`${label}: ${value}`);
                            } else {
                                const fallback = textOf(li);
                                if (fallback) out.lifestyle.push(fallback);
                            }
                        }
                    } else if (title === 'more about me') {
                        const items = Array.from(container.querySelectorAll('li'));
                        for (const li of items) {
                            const label = textOf(li.querySelector('h3'));
                            const value = textOf(li.querySelector('div[class*="Typs(body-1-regular)"]'));
                            if (label && value) {
                                out.more_about.push(`${label}: ${value}`);
                            } else {
                                const fallback = textOf(li);
                                if (fallback) out.more_about.push(fallback);
                            }
                        }
                    } else if (title === 'essentials') {
                        const items = Array.from(container.querySelectorAll('li'));
                        for (const li of items) {
                            const value = textOf(li.querySelector('div[class*="Typs(body-1-regular)"]')) || textOf(li);
                            if (value) out.essentials.push(value);
                        }
                    } else {
                        const answerEl = container.querySelector('div[class*="Typs(display-2-strong)"], span[class*="Typs(display-2-strong)"]');
                        const answer = textOf(answerEl);
                        if (answer) {
                            out.prompts.push({ question: textOf(h2), answer });
                        }
                    }
                }

                return out;
                """,
                scope
            )
            if spark and isinstance(spark, dict):
                about = spark.get("about")
                if about and not bio:
                    bio = about
                if spark.get("looking_for") and not looking_for:
                    looking_for = spark.get("looking_for")
                if spark.get("interests"):
                    infoItems["passions"] = spark.get("interests")
                if spark.get("lifestyle"):
                    infoItems["lifestyle"] = spark.get("lifestyle")
                if spark.get("more_about"):
                    more_about = spark.get("more_about") or []
                    for item in more_about:
                        if item and item not in infoItems["basics"]:
                            infoItems["basics"].append(item)
                if spark.get("looking_for_tags"):
                    looking_for_tags = spark.get("looking_for_tags") or []
                    for tag in spark.get("looking_for_tags") or []:
                        if tag and tag not in infoItems["basics"]:
                            infoItems["basics"].append(tag)
                if spark.get("essentials"):
                    for item in spark.get("essentials") or []:
                        if item and item not in infoItems["basics"]:
                            infoItems["basics"].append(item)
                if spark.get("prompts"):
                    prompts = spark.get("prompts") or []
        except Exception:
            pass

        # JS-based extraction for sections on active card/modal
        if not bio or not infoItems["passions"] or not infoItems["lifestyle"] or not infoItems["basics"] or not looking_for or not anthem:
            try:
                data = self.browser.execute_script(
                    """
                    const card = document.querySelector("div[data-keyboard-gamepad='true'][aria-hidden='false']") || document.querySelector("div[role='dialog'], div[aria-modal='true']");
                    if (!card) return null;
                    const sections = [];
                    const headings = Array.from(card.querySelectorAll('h2'));
                    for (const h of headings) {
                        const label = (h.textContent || '').trim();
                        if (!label) continue;
                        let container = h.parentElement ? h.parentElement.nextElementSibling : null;
                        if (!container && h.parentElement && h.parentElement.parentElement) {
                            container = h.parentElement.parentElement.nextElementSibling;
                        }
                        let chips = [];
                        if (container) {
                            chips = Array.from(container.querySelectorAll('span')).map(s => (s.textContent || '').trim()).filter(Boolean);
                        }
                        const text = container ? (container.textContent || '').trim() : '';
                        sections.push({label, text, chips});
                    }
                    return {sections};
                    """
                )
                if data and isinstance(data, dict):
                    for sec in data.get("sections", []):
                        label = (sec.get("label") or "").strip().lower()
                        text = (sec.get("text") or "").strip()
                        chips = [c for c in (sec.get("chips") or []) if c]
                        if label in ["about me", "bio"] and text and not bio:
                            bio = text
                        elif label in ["interests", "passions"] and chips and not infoItems["passions"]:
                            infoItems["passions"] = chips
                        elif label == "lifestyle" and chips and not infoItems["lifestyle"]:
                            infoItems["lifestyle"] = chips
                        elif label == "basics" and chips and not infoItems["basics"]:
                            infoItems["basics"] = chips
                        elif "looking for" in label and text and not looking_for:
                            looking_for = text
                        elif label == "my anthem" and text and not anthem:
                            anthem = text
            except Exception:
                pass


        # Bio
        try:
            bio = scope.find_element(By.CSS_SELECTOR, 'div[class*="Px(16px) Py(12px) Us(t)"').text

        except Exception as e:
            pass

        # Looking for
        try:
            looking_for_el = scope.find_element(By.CSS_SELECTOR, 'div[class="Px(16px) My(12px)"]>div[class="D(b)"]')
            looking_for = looking_for_el.find_element(By.CSS_SELECTOR, 'div[class="Typs(subheading-1) CenterAlign"]').text

        except Exception as e:
            pass

        # Basics, Lifestyle and Passions
        try:
            sections = scope.find_elements(By.CSS_SELECTOR, "div[class='Px(16px) Py(12px)']")
            for section in sections:
                headline = section.find_element(By.TAG_NAME, "h2").text.lower()
                
                if headline in infoItems.keys():
                    infoElements = section.find_elements(By.CSS_SELECTOR, "div[class^='Bdrs(100px)']")
                    for infoElement in infoElements:
                        infoItems[headline].append(infoElement.text)
                elif headline == 'my anthem':
                    song = section.find_element(By.CSS_SELECTOR, "div[class$='C($c-ds-text-primary)']").text
                    artist = section.find_element(By.CSS_SELECTOR, "div[class$='C($c-ds-text-secondary)']").text
                    anthem = {
                        "song": song,
                        "artist": artist
                    }
                else:
                    print("Unknown Sect Headline:", headline)


            #if ('Passions' in passions_el.find_element(By.TAG_NAME, "h2").text):
            #    #print("Passions Text", passions_el.text)
            #    elements = passions_el.find_element(By.TAG_NAME, 'div').find_element(By.TAG_NAME, 'div').find_elements(By.TAG_NAME, 'div')
            #    for el in elements:
            #        passions.append(el.text)
        except Exception as e:
            pass

        return bio, infoItems["passions"], infoItems["lifestyle"], infoItems["basics"], anthem, looking_for, prompts, more_about, looking_for_tags

    def get_image_urls(self, quickload=True):
        image_urls = []

        def add_url(url):
            if not url:
                return
            if 'static-assets' in url or '/icons/' in url:
                return
            # Only keep full-size profile images (avoid tiny avatars like 172x216)
            if '/172x216_' in url:
                return
            if 'images-ssl.gotinder.com/u/' in url or 'images.gotinder.com/u/' in url or 'gotinder.com/u/' in url:
                if url not in image_urls:
                    image_urls.append(url)

        # Prefer images from the active card on the recs page
        if not self._is_profile_opened():
            try:
                card = self._get_active_card()
                active_name = None
                try:
                    if card:
                        name_el = card.find_elements(By.CSS_SELECTOR, "[itemprop='name']")
                        if name_el and name_el[0].text:
                            active_name = name_el[0].text.strip()
                    if active_name:
                        name_candidates = self.browser.find_elements(By.CSS_SELECTOR, "[itemprop='name']")
                        for cand in name_candidates:
                            if (cand.text or "").strip() == active_name:
                                try:
                                    card = cand.find_element(By.XPATH, "./ancestor::div[@data-keyboard-gamepad='true'][1]")
                                except Exception:
                                    pass
                                break
                except Exception:
                    pass

                if card:
                    elements = card.find_elements(By.CSS_SELECTOR, "div[aria-label^='Profile photo'][style*='background-image']")
                    for element in elements:
                        style = element.value_of_css_property('background-image')
                        if style and 'url(' in style:
                            parts = style.split('\"')
                            if len(parts) > 1:
                                add_url(parts[1])
            except Exception:
                pass

        if image_urls:
            return image_urls

        if not self._is_profile_opened():
            self._open_profile()

        scope, _ = self._get_profile_scope(open_if_needed=True)

        # Click through photo tabs to load all images (Sparks carousel)
        try:
            buttons = scope.find_elements(By.CSS_SELECTOR, "[role='tablist'] button[aria-controls]")
            for btn in buttons:
                try:
                    btn.click()
                    time.sleep(0.2)
                    slides = scope.find_elements(By.CSS_SELECTOR, "[role='tabpanel'][aria-hidden='false'] div[style*='background-image']")
                    for slide in slides:
                        style = slide.value_of_css_property('background-image')
                        if style and 'url(' in style:
                            parts = style.split('\"')
                            if len(parts) > 1:
                                add_url(parts[1])
                except Exception:
                    continue
        except Exception:
            pass

        # Primary selector (legacy) scoped
        try:
            elements = scope.find_elements(By.XPATH, ".//div[@aria-label='Profile slider']")
            for element in elements:
                style = element.value_of_css_property('background-image')
                if style and 'url(' in style:
                    image_url = style.split('\"')[1]
                    add_url(image_url)
        except Exception:
            pass

        # Fallback: any element with background-image in style scoped
        try:
            elements = scope.find_elements(By.CSS_SELECTOR, "div[style*='background-image']")
            for element in elements:
                style = element.value_of_css_property('background-image')
                if style and 'url(' in style:
                    parts = style.split('\"')
                    if len(parts) > 1:
                        add_url(parts[1])
        except Exception:
            pass

        # Fallback: image tags scoped
        try:
            img_elements = scope.find_elements(By.CSS_SELECTOR, "img[src]")
            for img in img_elements:
                src = img.get_attribute("src")
                add_url(src)
        except Exception:
            pass

        if quickload or len(image_urls) > 0:
            return image_urls

        # Optional: click through bullets if present
        try:
            classname = 'bullet'
            WebDriverWait(self.browser, self.delay).until(
                EC.presence_of_element_located((By.CLASS_NAME, classname))
            )
            image_btns = self.browser.find_elements_by_class_name(classname)
            for btn in image_btns:
                btn.click()
                time.sleep(1)
                elements = self.browser.find_elements(By.CSS_SELECTOR, "div[style*='background-image']")
                for element in elements:
                    style = element.value_of_css_property('background-image')
                    if style and 'url(' in style:
                        parts = style.split('\"')
                        if len(parts) > 1:
                            add_url(parts[1])
        except Exception:
            pass

        return image_urls

    @staticmethod
    def de_emojify(text):
        """Remove emojis from a string
        Args:
            text (string): string with emojis or not
        Returns:
            string: recompile string without emojis
        """
        regrex_pattern = re.compile(
            pattern="["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    "]+",
            flags=re.UNICODE,
        )
        return regrex_pattern.sub(r'', text)

    def get_insta(self, text):
        """Take the bio and read line by line to match if the description
        contain an instagram user.
        Args:
            text (string): string with emojis or not
        Returns:
            ig (string): return valid instagram user.
        """
        if not text:
            return None
        valid_pattern = [
            "@",
            "ig-",
            "ig",
            "ig:",
            "ing",
            "ing:",
            "instag",
            "instag:",
            "insta:",
            "insta",
            "inst",
            "inst:",
            "instagram",
            "instagram:",
        ]
        description = text.rstrip().lower().strip()
        description = description.split()
        for x in range(len(description)):
            ig = self.de_emojify(description[x])
            if '@' in ig:
                return ig.replace('@', '')
            elif ig in valid_pattern:
                try:
                    if ':' in description[x + 1]:
                        return description[x + 2]
                    else:
                        return description[x + 1]
                except:
                    return None
            else:
                try:
                    ig = ig.split(':', 1)
                    if ig[0] in valid_pattern:
                        return ig[-1]
                except:
                    return None
        return None

    def _get_home_page(self):
        self.browser.get(self.HOME_URL)
        time.sleep(5)

    def _is_profile_opened(self):
        try:
            if '/profile' in self.browser.current_url:
                return True
            # Sparks layout keeps URL at /app/recs; detect profile back button/content
            if self.browser.find_elements(By.CSS_SELECTOR, "[data-testid='profileBackButton']"):
                return True
            if self.browser.find_elements(By.CSS_SELECTOR, ".profileContent"):
                return True
        except Exception:
            pass
        return False
