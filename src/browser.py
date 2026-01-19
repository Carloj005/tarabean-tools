import shutil
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from .config import Config

class BrowserManager:
    def __init__(self):
        self.driver = None
        self.profile_prepared = False
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def prepare_profile(self):
        """
        Clones the user's Chrome profile to a working directory.
        This allows us to steal the session/cookies without conflict.
        """
        src = Config.SOURCE_PROFILE_DIR
        dst = Config.CLONE_PROFILE_DIR
        
        # PERSISTENCE CHECK:
        # If the bot profile already exists, we assume the user has logged in successfully in a previous run.
        # We DO NOT overwrite it, so cookies remain saved.
        if os.path.exists(dst):
            self.logger.info(f"Using EXISTING bot profile at {dst}")
            self.logger.info("If you are not logged in, please login manually once. It will be remembered next time.")
            self.profile_prepared = True
            return True
            
        # Only clone if it works (first run)
        try:
            self.logger.info(f"First Run: Cloning Chrome profile from {src} to {dst} ...")
            
            # We assume the main profile is 'Default'.
            # We need to copy 'Default' folder AND 'Local State' file (for encryption keys).
            
            # 1. Copy 'Default' -> 'Default'
            # To speed up, we can skip Cache and Code Cache?
            # For simplicity, we just copy 'Default/Network', 'Default/Local Storage', 'Cookies'
            # Actually, copying just the whole Default folder is safest for cookies, but heavy.
            # Let's try to copy everything BUT exclude heavy caches.
            
            ignore_func = shutil.ignore_patterns('Cache*', 'Code Cache*', 'Service Worker*', 'File System*')
            
            shutil.copytree(
                os.path.join(src, "Default"),
                os.path.join(dst, "Default"),
                ignore=ignore_func
            )
            
            # 2. Copy 'Local State' (Critical for Linux KeyRing/Cookies)
            src_ls = os.path.join(src, "Local State")
            if os.path.exists(src_ls):
                shutil.copy2(src_ls, os.path.join(dst, "Local State"))
                
            self.logger.info("Profile cloned successfully.")
            self.profile_prepared = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to clone profile: {e}")
            return False

    def get_options(self):
        options = Options()
        options.binary_location = Config.CHROME_BINARY_PATH
        
        # Use our CLONED profile
        options.add_argument(f"--user-data-dir={Config.CLONE_PROFILE_DIR}")
        options.add_argument("--profile-directory=Default")
        
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Stability and Connection fixes
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        
        # KEY LINUX FIXES
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu") 
        return options

    def start(self):
        try:
            self.logger.info("Configuring Browser...")
            self.prepare_profile()
            
            options = self.get_options()
            
            self.logger.info("Installing Driver Manager...")
            service = Service(ChromeDriverManager().install())
            
            self.logger.info(f"Launching Chrome from: {Config.CHROME_BINARY_PATH}")
            self.driver = webdriver.Chrome(service=service, options=options)
            
            print("--- Chrome Launched via Selenium ---")
            
            self.driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
            self.logger.info("Browser started successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            print(f"ERROR DETAIL: {e}")
            if "Chrome failed to start" in str(e) or "DevToolsActivePort" in str(e):
                print("\n[!] CRITICAL: Chrome likely failed to bind to the debug port.")
                print("1. Make sure ALL Chrome windows are closed (check system tray too).")
                print("2. Try running 'pkill chrome' or 'killall google-chrome-stable' in terminal.")
            return False

    def stop(self):
        if self.driver:
            # Suppress noisy shutdown errors
            logging.getLogger("urllib3").setLevel(logging.CRITICAL)
            logging.getLogger("selenium").setLevel(logging.CRITICAL)
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.logger.info("Browser closed.")

    def navigate_to(self, url):
        self.driver.get(url)
        self.logger.info(f"Navigated to {url}")
