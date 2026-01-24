import threading
import time
import queue
import random
from selenium.webdriver.common.by import By
from .browser import BrowserManager
from .config import Config
from .puzzle import PuzzleSolver
from .memory import MemorySolver
from .logger import GlobalLogger

class GameWorker:
    """
    Represents a single independent browser instance running a specific game task.
    Runs in its own thread.
    """
    def __init__(self, worker_id, game_type="PUZZLE", difficulty="RANDOM"):
        self.worker_id = worker_id
        self.game_type = game_type # PUZZLE or MEMORY
        self.difficulty = difficulty
        
        self.browser = BrowserManager(worker_id=worker_id)
        self.solver = None
        self.thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        self.status = "IDLE"
        
        # Stats
        self.items_solved = 0
        self.last_activity = time.time()
        
    def start(self):
        """Spawns the worker thread"""
        if self.is_running: return
        
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, name=f"Worker-{self.worker_id}")
        self.thread.daemon = True
        self.thread.start()
        self.is_running = True
        self.status = "STARTING"
        
    def stop(self):
        """Signals the thread to stop and waits"""
        if not self.is_running: return
        
        self.status = "STOPPING"
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        self.browser.stop()
        self.is_running = False
        self.status = "STOPPED"

    def _run_loop(self):
        """Main Thread Entrypoint"""
        try:
            if not self.browser.start():
                self.status = "BROWSER FAILED"
                GlobalLogger.log(f"Worker-{self.worker_id}", "Browser failed to start.")
                return

            GlobalLogger.log(f"Worker-{self.worker_id}", f"Started {self.game_type} routine.")

            # Navigate based on game type
            if self.game_type == "PUZZLE":
                self._puzzle_routine()
            elif self.game_type == "MEMORY":
                self._memory_routine()
                
        except Exception as e:
            self.status = f"ERROR: {str(e)[:20]}"
            GlobalLogger.log(f"Worker-{self.worker_id}", f"CRASH: {e}")
        finally:
            self.browser.stop()
            self.is_running = False
            GlobalLogger.log(f"Worker-{self.worker_id}", "Stopped.")

    def _puzzle_routine(self):
        self.status = "NAVIGATING"
        self.browser.navigate_to(Config.PUZZLE_URL)
        
        self.solver = PuzzleSolver(self.browser.driver)
        self.status = "RUNNING"
        
        while not self.stop_event.is_set():
            # 1. Watchdog
            if time.time() - self.last_activity > Config.STUCK_TIMEOUT:
                self.status = "STUCK REFRESH"
                try:
                    self.browser.driver.execute_script("location.reload()")
                    time.sleep(3)
                    self.last_activity = time.time()
                except:
                    pass
                self.status = "RUNNING"

            # 2. Logic Step
            try:
                # Check "Next"
                if self._check_puzzle_next():
                    self.items_solved += 1
                    self.last_activity = time.time()
                    continue
                
                # Check Difficulty
                if self._select_difficulty():
                    self.last_activity = time.time()
                    time.sleep(1)
                    continue

                # Solve
                if self.solver.solve():
                    self.last_activity = time.time()
                    
            except Exception as e:
                pass
                
            time.sleep(0.1)

    def _memory_routine(self):
        self.status = "NAVIGATING"
        self.browser.navigate_to("https://tarabean.com/memory")
        
        self.solver = MemorySolver(self.browser)
        self.status = "RUNNING"
        
        while not self.stop_event.is_set():
            if time.time() - self.last_activity > Config.STUCK_TIMEOUT:
                self.browser.driver.execute_script("location.reload()")
                self.last_activity = time.time()
                time.sleep(3)
                continue
                
            try:
                # A. Move
                self.status = "SCANNING"
                if self.solver.solve_level():
                    self.status = "MATCHING"
                    self.last_activity = time.time()
                    
                # B. Next Level
                self.status = "WAITING"
                if self.solver.wait_for_next_level():
                    self.items_solved += 1 
                    self.last_activity = time.time()
                    time.sleep(2)
                    
                # C. Game Over
                if self.solver.is_game_over():
                    self.status = "RESTARTING"
                    try:
                         # Try to find replay button first
                         btns = self.browser.driver.find_elements(By.XPATH, "//div[@role='dialog']//button")
                         if btns: btns[0].click()
                         else: self.browser.driver.refresh()
                    except: 
                        self.browser.driver.refresh()
                    self.last_activity = time.time()
                    time.sleep(2)
                    
            except:
                pass
            time.sleep(0.5)

    def _check_puzzle_next(self):
        try:
             # Hover trick
             try:
                 container = self.browser.driver.find_element(By.XPATH, "//div[contains(@style, 'background-position')]")
                 actions = ActionChains(self.browser.driver)
                 actions.move_to_element(container).perform()
                 actions.move_by_offset(10, 0).perform()
                 actions.move_by_offset(-10, 0).perform()
             except: pass

             xpath = "//*[contains(text(), 'Go next')]"
             btns = self.browser.driver.find_elements(By.XPATH, xpath)
             for btn in btns:
                 if btn.is_displayed():
                     self.browser.driver.execute_script("arguments[0].click();", btn)
                     return True
        except: pass
        return False
        
    def _select_difficulty(self):
        difficulty_keywords = {
            "Easy": ["easy"],
            "Normal": ["normal", "medium", "regular"], 
            "Hard": ["hard", "expert"]
        }
        
        target_list = []
        if self.difficulty == "RANDOM":
            opts = ["Easy", "Normal", "Hard"]
            random.shuffle(opts)
            target_list = opts
        elif self.difficulty in ["Easy", "Normal", "Hard"]:
            target_list = [self.difficulty]
        else:
            return False

        for diff_name in target_list:
            keywords = difficulty_keywords.get(diff_name, [diff_name.lower()])
            for kw in keywords:
                try:
                    xpath = f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')]"
                    btns = self.browser.driver.find_elements(By.XPATH, xpath)
                    for btn in btns:
                        if btn.is_displayed():
                            self.browser.driver.execute_script("arguments[0].click();", btn)
                            return True
                except: pass
        return False
