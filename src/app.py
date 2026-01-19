import time
import random
import traceback
import sys
import select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from .config import Config
from .browser import BrowserManager
from .puzzle import PuzzleSolver
from .memory import MemorySolver

class App:
    def __init__(self):
        self.browser = BrowserManager()
        self.is_running = False
        self.puzzles_solved = 0
        self.last_refresh = time.time()
        self.last_activity_time = time.time()
        
        # Mode settings
        self.difficulty_mode = "RANDOM" 
        self.target_difficulty = None
        self.memory_solver = None # Lazy init or init here? Init in run_memory to be safe or here.

        
    def clear_screen(self):
        print("\033[H\033[J", end="") # ANSI clear screen

    def home_menu(self):
        while True:
            self.clear_screen()
            print("\n" + "="*50)
            print("""
  _______                   __                     
 |__   __|                 |  |                    
    | | __ _ _ __ __ _     |  |__   ___  __ _ _ __ 
    | |/ _` | '__/ _` |    | '_ \ / _ \/ _` | '_ \\
    | | (_| | | | (_| |    | |_) |  __/ (_| | | | |
    |_|\__,_|_|  \__,_|    |_.__/ \___|\__,_|_| |_|
            """)
            print("       AUTOMATION SUITE v2.0 - OPTIMIZED")
            print("="*50)
            print(" 1. 🧩 [XP FARM] Puzzle Game Solver")
            print(" 2. 🧠 [XP FARM] Memory Game Solver")
            print(" 3. ❌ Exit")
            print("="*50)
            
            choice = input("Select Option: ").strip()
            if choice == '1':
                self.run_puzzle_setup()
            elif choice == '2':
                self.run_memory_game()
            elif choice == '3':
                print("Goodbye!")
                sys.exit(0)
                
    def run_puzzle_setup(self):
        """
        Sub-menu for Puzzle Solver configuration
        """
        while True:
            self.clear_screen()
            print("\n" + "="*40)
            print(" 🧩 PUZZLE SOLVER CONFIGURATION")
            print("="*40)
            print(f"Current Mode: {self.difficulty_mode} " + (f"({self.target_difficulty})" if self.target_difficulty else ""))
            print("-" * 40)
            print("1. ▶ START GAME (Random Mode - Default)")
            print("2. ⚙ Select Fixed Difficulty")
            print("3. ↩ Back to Home")
            print("="*40)
            
            choice = input("Select Option: ").strip()
            if choice == '1':
                self.difficulty_mode = "RANDOM"
                self.target_difficulty = None
                self.start_puzzle_session()
            elif choice == '2':
                self.fixed_difficulty_menu()
            elif choice == '3':
                return
                
    def fixed_difficulty_menu(self):
        while True:
            self.clear_screen()
            print("\n" + "="*40)
            print(" ⚙ FIXED DIFFICULTY SELECTION")
            print("="*40)
            print("Bot will strictly play ONLY this difficulty.")
            print("-" * 40)
            print("1. Easy")
            print("2. Normal / Medium")
            print("3. Hard")
            print("4. ↩ Back")
            print("="*40)
            
            choice = input("Select Difficulty: ").strip()
            if choice == '1':
                self.difficulty_mode = "FIXED"
                self.target_difficulty = "Easy"
                self.start_puzzle_session()
                return # Return after session ends
            elif choice == '2':
                self.difficulty_mode = "FIXED"
                self.target_difficulty = "Normal"
                self.start_puzzle_session()
                return
            elif choice == '3':
                self.difficulty_mode = "FIXED"
                self.target_difficulty = "Hard"
                self.start_puzzle_session()
                return
            elif choice == '4':
                return

    def run(self):
        try:
            Config.validate()
            self.home_menu() # Start the main event loop
        except KeyboardInterrupt:
            self.clean_up()
        finally:
            self.clean_up()

    def start_puzzle_session(self):
        """
        Launches browser and runs the game loop with PAUSE support.
        """
        print("\nStarting Browser...")
        if not self.browser.start():
            print("Failed to start browser.")
            time.sleep(2)
            return

        try:
            print(f"Navigating to {Config.PUZZLE_URL}...")
            self.browser.navigate_to(Config.PUZZLE_URL)
            self.solver = PuzzleSolver(self.browser.driver)
            self.is_running = True
            
            print("Game started... (Press ENTER to PAUSE)")
            time.sleep(2)
            
            while self.is_running:
                try:
                    self.game_loop()
                # Still catch Ctrl+C as fallback/safety, but main interaction is Enter
                except KeyboardInterrupt:
                    self.handle_pause_menu()
                    if not self.is_running:
                        break
                        
        except Exception as e:
            print(f"Critical Runtime Error: {e}")
            traceback.print_exc()
            input("Press Enter to continue...")
        finally:
            self.browser.stop()
            
    def handle_pause_menu(self):
        """
        Called when ENTER is pressed during game loop.
        """
        while True:
            self.clear_screen()
            print("\n" + "!"*40)
            print(" ⏸  GAME PAUSED")
            print("!"*40)
            print("1. ▶ Resume")
            print("2. 🏠 Return to Main Menu (Closes Browser)")
            print("3. ❌ Exit Desktop App")
            print("!"*40)
            
            choice = input("Selection: ").strip()
            if choice == '1':
                print("Resuming...")
                return # Go back to loop
            elif choice == '2':
                self.is_running = False # Break loop
                return
            elif choice == '3':
                print("Bye!")
                self.clean_up()
                sys.exit(0)

    def game_loop(self):
        """
        One iteration of the game checking logic.
        """
        driver = self.browser.driver
        
        # 0. Check for Pause (Non-blocking Enter key)
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            self.handle_pause_menu()
            if not self.is_running:
                return
        
        # Check if it's time to queue a refresh
        if time.time() - self.last_refresh > Config.REFRESH_INTERVAL:
             # Just print once or set a flag? 
             # We can just check this condition when we are at a safe point.
             pass

        # 1. Check Safe Points
        
        # A. Puzzle Solved Screen (Best time to refresh)
        if self.is_next_button_visible():
            print("Puzzle Solved!")
            self.last_activity_time = time.time() # Activity confirmed
            
            # Check if we should Refresh (Time elapsed) INSTEAD of clicking Next
            if time.time() - self.last_refresh > Config.REFRESH_INTERVAL:
                print(f"⏰ Timer expired ({Config.REFRESH_INTERVAL}s). Refreshing page to switch difficulty...")
                try:
                    driver.refresh()
                    self.last_refresh = time.time()
                    self.last_activity_time = time.time()
                    time.sleep(3)
                    return
                except:
                    pass
            
            # Normal Flow
            self.click_next()
            self.puzzles_solved += 1
            print(f"Total Solved: {self.puzzles_solved}")
            time.sleep(Config.MIN_JITTER)
            return

        # B. Check for Menu (Difficulty Selection)
        # If we are in the menu, we can also refresh if needed (to re-roll RNG or clean state)
        # But usually we just select.
        
        # 2. Difficulty Selection
        # If manual selection needed
        if self.select_difficulty():
            self.last_activity_time = time.time() # Activity confirmed
            time.sleep(0.5)
            # Check refresh here too if just selected difficulty to avoid stale random?
            return

        # 3. Solving
        try:
            # If we are here, we might be solving.
            # We do NOT refresh here unless we decide to implement a "stuck" watchdog.
            solved_something = self.solver.solve()
            if solved_something:
                self.last_activity_time = time.time() # Reset stuck timer if we did some moves
        except:
            pass
        
        # 0. Periodic Refresh Check
        # ... (Existing refresh logic) ...
        # Also check for STUCK state (watchdog)
        if time.time() - self.last_activity_time > Config.STUCK_TIMEOUT:
             print(f"⚠️ STUCK DETECTED (No activity for {Config.STUCK_TIMEOUT}s). Force Reloading...")
             try:
                driver.refresh()
                self.last_refresh = time.time()
                self.last_activity_time = time.time()
                time.sleep(2)
                return
             except:
                pass
        
        # throttle loop
        time.sleep(0.1)

    def is_next_button_visible(self):
        try:
             # PROACTIVE: Move mouse to center of screen to trigger hover events
             # This fixes the issue where "Go next" is hidden because mouse is "out"
             try:
                 # Find a puzzle piece or container to hover over specifically
                 container = self.browser.driver.find_element(By.XPATH, "//div[contains(@style, 'background-position')]")
                 
                 actions = ActionChains(self.browser.driver)
                 actions.move_to_element(container).perform()
                 # Wiggle slightly
                 actions.move_by_offset(10, 0).perform()
                 actions.move_by_offset(-10, 0).perform()
             except:
                 pass 

             # Look for "Go next" button or text
             # User reported "Nice~! Go next~" text which might not be a <button> tag
             xpath = "//*[contains(text(), 'Go next')]"
             btns = self.browser.driver.find_elements(By.XPATH, xpath)
             for btn in btns:
                 if btn.is_displayed():
                     return True
             return False
        except:
             return False

    def click_next(self):
        try:
             xpath = "//*[contains(text(), 'Go next')]"
             btns = self.browser.driver.find_elements(By.XPATH, xpath)
             for btn in btns:
                 if btn.is_displayed():
                     # Try regular click first, then JS
                     try:
                        btn.click()
                     except:
                        self.browser.driver.execute_script("arguments[0].click();", btn)
                     return
        except:
             pass

    def select_difficulty(self):
        """
        Detects if difficulty buttons are present and selects one.
        Returns:
            True if a selection was made
            False if no selection was made (or buttons not found)
        """
        # Buttons usually have text "Easy", "Normal", "Hard"
        # We need to be careful not to click them if we are already playing?
        # Assuming this method is called when we suspect we are on the menu.
        
        difficulty_keywords = {
            "Easy": ["easy"],
            "Normal": ["normal", "medium", "regular"], 
            "Hard": ["hard", "expert"]
        }
        
        target_list = []
        
        if self.difficulty_mode == "FIXED":
            # Just try to find THE specific one we want
            if self.target_difficulty:
                target_list = [self.target_difficulty]
        else:
            # Random Mode: Shuffle the options
            opts = ["Easy", "Normal", "Hard"]
            random.shuffle(opts)
            target_list = opts
            
        for diff_name in target_list:
            keywords = difficulty_keywords.get(diff_name, [diff_name.lower()])
            
            for kw in keywords:
                try:
                    # Case insensitive search
                    xpath = f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')]"
                    btns = self.browser.driver.find_elements(By.XPATH, xpath)
                    for btn in btns:
                        if btn.is_displayed():
                            print(f"Auto-selecting difficulty: {diff_name} (found '{kw}')")
                            self.browser.driver.execute_script("arguments[0].click();", btn)
                            return True
                except:
                    pass
        return False

    def run_memory_game(self):
        """
        Runs the Memory Game Solver loop.
        """
        print("\nStarting Browser for Memory Game...")
        if not self.browser.start():
            print("Failed to start browser.")
            time.sleep(2)
            return

        try:
            url = "https://tarabean.com/memory"
            print(f"Navigating to {url}...")
            self.browser.navigate_to(url)
            self.memory_solver = MemorySolver(self.browser)
            
            self.is_running = True
            self.last_activity_time = time.time()
            
            print("\n=== 🧠 MEMORY SOLVER RUNNING ===")
            print("Info: Solver automatically handles levels and shuffles.")
            print("Press [ENTER] to Pause/Exit at any time.")
            
            while self.is_running:
                # 0. Check for Pause (Non-blocking Enter key)
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.readline()
                    self.handle_pause_menu()
                    if not self.is_running:
                        break

                # 1. Check for Stuck (Watchdog)
                if time.time() - self.last_activity_time > Config.STUCK_TIMEOUT:
                    print(f"⚠️ STUCK DETECTED ({Config.STUCK_TIMEOUT}s). refreshing...")
                    try:
                        self.browser.driver.refresh()
                        time.sleep(3)
                        self.last_activity_time = time.time()
                    except:
                        pass
                    continue
                
                # 2. Main Solver Logic
                try:
                    # A. Try to Solve Level
                    moves_made = self.memory_solver.solve_level()
                    if moves_made:
                        self.last_activity_time = time.time()
                    
                    # B. Check for Level Complete / Transitions
                    if self.memory_solver.wait_for_next_level():
                        print("Level Complete! Moving to next...")
                        self.last_activity_time = time.time()
                        time.sleep(2) # Wait for transition
                    
                    # C. Check for Game Over / Restart
                    if self.memory_solver.is_game_over():
                        print(" >> Game Over detected. Auto-restarting loop...")
                        # Try to find "Play Again" or "Try Again" button in dialog
                        btns = self.browser.driver.find_elements(By.XPATH, "//div[@role='dialog']//button")
                        if btns:
                            for btn in btns:
                                if "play" in btn.text.lower() or "try" in btn.text.lower():
                                    btn.click()
                                    break
                            else:
                                if btns: btns[0].click()
                        else:
                            self.browser.driver.refresh()
                        self.last_activity_time = time.time()
                        time.sleep(2)
                        
                except Exception as e:
                    pass
                
                time.sleep(0.5)

        except KeyboardInterrupt:
            self.clean_up()
        except Exception as e:
            print(f"Error in Memory Game: {e}")
            traceback.print_exc()
            input("Press Enter...")
        finally:
            self.browser.stop()

    def clean_up(self):
        if self.browser:
            self.browser.stop()
        print("\nSession ended.")
