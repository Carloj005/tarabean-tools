import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from .logger import GlobalLogger

class MemorySolver:
    def __init__(self, browser_manager):
        self.browser = browser_manager

    def scan_board(self):
        try:
            # 1. Find all potential grid containers
            driver = self.browser.driver
            grids = driver.find_elements(By.XPATH, "//div[contains(@class, 'MemoryGame-module__k2AJWG__grid')]")
            GlobalLogger.log("Memory", f"Found {len(grids)} potential grids.")
            
            best_grid = None
            max_z = -1
            
            # 2. Select the "best" grid (Highest Z-Index/DOM order + Visible)
            for grid in grids:
                if not grid.is_displayed(): continue
                
                # Check Opacity
                op = grid.value_of_css_property("opacity") or "1"
                if float(op) < 0.5: continue
                
                # Z-Index check
                try: z = int(grid.value_of_css_property("z-index"))
                except: z = 0
                
                if z >= max_z:
                    max_z = z
                    best_grid = grid

            if not best_grid:
                GlobalLogger.log("Memory", "No valid best_grid found.")
                return None

            # 3. Find cards with STABILITY CHECK
            cards = []
            for _ in range(3):
                raw_cards = best_grid.find_elements(By.XPATH, ".//div[contains(@class, 'MemoryGame-module__k2AJWG__card')]")
                
                # Filter strict
                cards = []
                for c in raw_cards:
                    try:
                        cls = c.get_attribute("class")
                        if "Inner" not in cls and "Front" not in cls and "Back" not in cls:
                            cards.append(c)
                    except: pass
                    
                count = len(cards)
                GlobalLogger.log("Memory", f"Scan Attempt: Raw={len(raw_cards)}, Filtered={count}")
                if count > 10: 
                    GlobalLogger.log("Memory", f"Stability check pass: {count} cards (Filtered).")
                    break 
                GlobalLogger.log("Memory", f"Stability check wait... ({count} cards)")
                time.sleep(0.5)
            
            if not cards: 
                GlobalLogger.log("Memory", "Scan failed: No cards found after stability check.")
                return None

            # --- CHEAT LOGIC: COORDINATE DEDUPLICATION ---
            slots = {} # "x,y" -> list of elements
            
            for card in cards:
                if not card.is_displayed(): continue
                rect = card.rect
                x, y = int(rect['x']), int(rect['y'])
                key = f"{x},{y}"
                if key not in slots: slots[key] = []
                slots[key].append(card)
                
            GlobalLogger.log("Memory", f"Coordinate Dedup: Found {len(slots)} unique slots from {len(cards)} elements.")
            
            card_data = [] 
            all_src_counts = {}
            
            for key, slot_cards in slots.items():
                active_card = slot_cards[-1]
                srcs = set()
                
                # Image Tags
                imgs = active_card.find_elements(By.TAG_NAME, "img")
                for img in imgs:
                    s = img.get_attribute("src")
                    if s: 
                        srcs.add(s)
                        all_src_counts[s] = all_src_counts.get(s, 0) + 1
                
                # Background Images
                divs = active_card.find_elements(By.TAG_NAME, "div")
                for div in divs:
                    bg = div.value_of_css_property("background-image")
                    if bg and "url" in bg:
                        s = bg
                        srcs.add(s)
                        all_src_counts[s] = all_src_counts.get(s, 0) + 1
                
                card_data.append({"element": active_card, "srcs": srcs})

            # Identify Back Image
            threshold = len(card_data) * 0.4 
            back_srcs = {s for s, count in all_src_counts.items() if count > threshold}
            if back_srcs:
                GlobalLogger.log("Memory", f"Identified Back Image patterns: {len(back_srcs)}")
            
            # Group Pairs
            pairs = {}
            for item in card_data:
                unique_faces = item["srcs"] - back_srcs
                if len(unique_faces) >= 1:
                    face = list(unique_faces)[0]
                    if face not in pairs: pairs[face] = []
                    pairs[face].append(item["element"])

            GlobalLogger.log("Memory", f"Pairs Analysis: Found {len(pairs)} unique faces.")
            return pairs

        except Exception as e:
            GlobalLogger.log("Memory", f"CRASH in scan_board: {e}")
            return None

    def solve_level(self):
        GlobalLogger.log("Memory", "Starting solve_level()...")
        pairs = self.scan_board()
        
        if not pairs:
            GlobalLogger.log("Memory", "Abort: No pairs returned from scan.")
            return False

        active_pairs = {}
        for src, cards in pairs.items():
            valid_cards = [c for c in cards if c.is_displayed()] 
            if len(valid_cards) >= 2:
                active_pairs[src] = valid_cards[:2]
        
        if not active_pairs:
            GlobalLogger.log("Memory", "Abort: No active pairs found (all filtered or single).")
            return False

        GlobalLogger.log("Memory", f"Action: Matching {len(active_pairs)} pairs.")
        from selenium.common.exceptions import ElementClickInterceptedException

        for i, (src, cards) in enumerate(active_pairs.items()):
            try:
                card1, card2 = cards
                GlobalLogger.log("Memory", f"Clicking Pair {i+1}: {card1.location} & {card2.location}")
                
                self.browser.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card1)
                card1.click()
                time.sleep(0.4) 
                
                self.browser.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card2)
                card2.click()
                time.sleep(0.6) 
                
            except ElementClickInterceptedException:
                GlobalLogger.log("Memory", "Click Intercepted! Dialog might be open.")
                if self.wait_for_next_level(): return True
                return False
            except Exception as e:
                GlobalLogger.log("Memory", f"Match Error: {e}")
                return True 
        
        return True

    def wait_for_next_level(self):
        try:
            xpath = "//div[@role='dialog']//button"
            GlobalLogger.log("Memory", "Checking for Next Level dialog...")
            
            # Short wait check
            try:
                WebDriverWait(self.browser.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
            except:
                pass # Just continue to check elements
            
            btns = self.browser.driver.find_elements(By.XPATH, xpath)
            for btn in btns:
                txt = btn.text.lower()
                GlobalLogger.log("Memory", f"Dialog Button found: '{btn.text}'")
                if "next" in txt or "play again" in txt or "ready" in txt or "close" in txt or "try again" in txt:
                    GlobalLogger.log("Memory", f"CLICKING NEXT LEVEL: {btn.text}")
                    btn.click()
                    return True
            
            return False
        except Exception as e:
            GlobalLogger.log("Memory", f"NextLevel Error: {e}")
            return False

    def is_game_over(self):
        try:
            over = "TIME'S UP" in self.browser.driver.page_source
            if over: GlobalLogger.log("Memory", "GAME OVER detected.")
            return over
        except:
            return False
