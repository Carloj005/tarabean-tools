import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

class MemorySolver:
    def __init__(self, browser_manager):
        self.browser = browser_manager
        self.logger = lambda x: print(f"[Memory] {x}")

    def scan_board(self):
        try:
            # 1. Find all potential grid containers
            grids = self.browser.driver.find_elements(By.XPATH, "//div[contains(@class, 'MemoryGame-module__k2AJWG__grid')]")
            
            best_grid = None
            max_z = -1
            
            # 2. Select the "best" grid (Highest Z-Index/DOM order + Visible)
            for grid in grids:
                if not grid.is_displayed():
                    continue
                
                # Check Opacity
                opacity = grid.value_of_css_property("opacity")
                if opacity and float(opacity) < 0.5:
                    continue
                
                # Check Dimensions
                rect = grid.rect
                if rect['width'] < 100 or rect['height'] < 100:
                    continue

                # Z-Index check
                z_index = grid.value_of_css_property("z-index")
                try:
                    z = int(z_index)
                except:
                    z = 0
                
                # If multiple valid grids, prefer the one with higher Z or later in DOM (loop order)
                if z >= max_z:
                    max_z = z
                    best_grid = grid

            if not best_grid:
                # self.logger("No active grid found.")
                return None

            # 3. Find cards STRICTLY within this best grid
            cards = best_grid.find_elements(By.XPATH, ".//div[contains(@class, 'MemoryGame-module__k2AJWG__card')]")
            
            pairs = {}
            valid_cards = []

            for card in cards:
                if not card.is_displayed():
                    continue
                
                # Double check: Is card actually visible?
                if card.size['width'] == 0:
                    continue

                try:
                    img = card.find_element(By.CSS_SELECTOR, "img")
                    src = img.get_attribute("src")
                    
                    if src not in pairs:
                        pairs[src] = []
                    pairs[src].append(card)
                    valid_cards.append(card)
                except:
                    continue
            
            # self.logger(f"Scan summary: Active Grid (Z={max_z}) has {len(valid_cards)} cards.")
            
            # Basic sanity check: Standard levels have 16, 20, 24 cards etc.
            # If we found e.g. 80, something is still wrong. 
            # But filtering by best_grid *should* fix it if structure allows.
            
            return pairs

        except Exception as e:
            self.logger(f"Error scanning board: {e}")
            return None

    def solve_level(self):
        """
        Executes the solving strategy for the current level.
        """
        self.logger("Scanning board for pairs...")
        pairs = self.scan_board()
        
        if not pairs:
            self.logger("No cards found. Level might not be started or already matched.")
            return False

        # Filter out pairs that are already matched (if the game removes them or adds a class)
        # The class 'MemoryGame-module__k2AJWG__matched' indicates a match.
        # We should skip those.
        
        active_pairs = {}
        for src, cards in pairs.items():
            valid_cards = []
            for card in cards:
                try:
                    cls = card.get_attribute("class")
                    if "matched" not in cls and "flipped" not in cls:
                        valid_cards.append(card)
                except StaleElementReferenceException:
                    pass # Element gone
            
            if len(valid_cards) == 2:
                active_pairs[src] = valid_cards
        
        if not active_pairs:
            self.logger("No active pairs found to match.")
            return False

        self.logger(f"Found {len(active_pairs)} pairs to match.")
        
        for i, (src, cards) in enumerate(active_pairs.items()):
            self.logger(f"Matching pair {i+1}/{len(active_pairs)}")
            try:
                card1, card2 = cards
                
                # Check for shuffle or other interruptions?
                # For now, just click.
                
                # Click first
                card1.click()
                time.sleep(0.2) # Short delay for animation
                
                # Click second
                card2.click()
                
                # Wait for match animation or logic to process
                time.sleep(0.5) 
                
            except (StaleElementReferenceException, Exception) as e:
                self.logger(f"Failed to match a pair (Stale/Error). Retrying scan. {e}")
                return True # Return true to trigger a re-scan loop in the main loop
        
        return True

    def wait_for_next_level(self):
        """
        Detects 'Level Complete' dialog and clicks 'Next Level' or 'Play Again'.
        Returns True if advanced, False if timed out.
        """
        try:
            # Look for dialog with "Level X Complete" or "All Levels Complete"
            # Button usually says "Next Level" or "Play Again"
            # We can look for buttons in a dialog.
            
            # Using a generic wait for a button in a dialog
            # Selector guess based on Radix UI dialog usage seen in code
            xpath = "//div[@role='dialog']//button"
            
            WebDriverWait(self.browser.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            
            btns = self.browser.driver.find_elements(By.XPATH, xpath)
            for btn in btns:
                txt = btn.text.lower()
                if "next" in txt or "play again" in txt or "ready" in txt:
                    self.logger(f"Clicking button: {btn.text}")
                    btn.click()
                    return True
            
            return False
        except TimeoutException:
            return False
        except Exception as e:
            self.logger(f"Error waiting for next level: {e}")
            return False

    def is_game_over(self):
        # Implementation for checking if time ran out
        # "LMAOOO TIME'S UP!" in dialog title
        try:
            return "TIME'S UP" in self.browser.driver.page_source
        except:
            return False
