import shutil
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from .config import Config

class BrowserManager:
    def __init__(self, worker_id=1):
        self.worker_id = worker_id
        self.driver = None
        self.profile_prepared = False
        self.setup_logging()

    def setup_logging(self):
        # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(f"Worker_{self.worker_id}")
        # Ensure we don't spam root logger if configured elsewhere
        if not self.logger.handlers:
             ch = logging.StreamHandler()
             ch.setFormatter(logging.Formatter(f'[Worker {self.worker_id}] %(message)s'))
             self.logger.addHandler(ch)
             self.logger.setLevel(logging.INFO)

    def prepare_profile(self):
        """
        Clones the user's Chrome profile to a unique working directory for this worker.
        """
        src = Config.SOURCE_PROFILE_DIR
        dst = f"{Config.CLONE_PROFILE_DIR}_{self.worker_id}"

        # PERSISTENCE / SYNC LOGIC:
        # If this is Worker 2+, try to clone from Worker 1's profile (Master) 
        # instead of the system default. This syncs the login state.
        if self.worker_id > 1:
            master_profile = f"{Config.CLONE_PROFILE_DIR}_1"
            if os.path.exists(master_profile) and os.path.exists(os.path.join(master_profile, "Default")):
                self.logger.info(f"Syncing profile from Worker 1 (Master) -> Worker {self.worker_id}...")
                src = master_profile
        
        # Check if destination exists
        if os.path.exists(dst):
            self.logger.info(f"Using existing profile at {dst}")
            self.profile_prepared = True
            return True
            
        try:
            self.logger.info(f"Cloning profile from {src} to {dst}...")
            # Ignore heavy caches
            ignore_func = shutil.ignore_patterns('Cache*', 'Code Cache*', 'Service Worker*', 'File System*')
            
            # 1. Copy Default folder
            shutil.copytree(
                os.path.join(src, "Default"),
                os.path.join(dst, "Default"),
                ignore=ignore_func
            )
            
            # 2. Copy Local State (Only needed if cloning from system source)
            # If cloning from Master, Master already has it?
            # Actually, Local State is outside Default.
            # If src is Master, we should copy Local State from Master too.
            src_ls = os.path.join(src, "Local State")
            # If src is System (Config.SOURCE_PROFILE_DIR), it's just inside src.
            # wait, master_profile path points to .../antigravity/scratch/tarabean-tools/chrome_data_1
            # which structure is: /Default, /Local State
            
            if os.path.exists(src_ls):
                 shutil.copy2(src_ls, os.path.join(dst, "Local State"))
            elif self.worker_id > 1:
                 # Fallback: Copy Local State from SYSTEM source if Master doesn't have it (weird)
                 sys_ls = os.path.join(Config.SOURCE_PROFILE_DIR, "Local State")
                 if os.path.exists(sys_ls):
                    shutil.copy2(sys_ls, os.path.join(dst, "Local State"))

            self.logger.info("Profile cloned.")
            self.profile_prepared = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to clone profile: {e}")
            return False

    def get_options(self):
        options = Options()
        options.binary_location = Config.CHROME_BINARY_PATH
        
        # Use UNIQUE CLONED profile
        options.add_argument(f"--user-data-dir={Config.CLONE_PROFILE_DIR}_{self.worker_id}")
        options.add_argument("--profile-directory=Default")
        
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        
        # KEY LINUX FIXES
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu") 
        
        # PERFORMANCE & BACKGROUND FIXES (Aggressive)
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        # New "God Mode" Background Flags
        options.add_argument("--disable-features=CalculateNativeWinOcclusion,IsolateOrigins,site-per-process")
        options.add_argument("--disable-visibility-tracking")
        options.add_argument("--window-position=0,0") # Ensure not off-screen considered hidden
        
        # SILENT ZOOM (Fixes Focus Stealing)
        # Forces the browser to render at 80% scale natively.
        # No need to send_keys or usage of CSS hacks.
        options.add_argument("--force-device-scale-factor=0.80")
        options.add_argument("--high-dpi-support=1")
        
        # KEEPALIVE EXTENSION (The Nuclear Option)
        ext_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "extension"))
        if os.path.exists(ext_path):
            options.add_argument(f"--load-extension={ext_path}")
            
        return options

    def start(self):
        try:
            self.logger.info("Initializing Browser...")
            self.prepare_profile()
            options = self.get_options()
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
            
            # Position windows nicely?
            # x_offset = (self.worker_id - 1) * 100
            # self.driver.set_window_position(x_offset, 0)
            
            self.logger.info("Browser Started.")
            return True
        except Exception as e:
            self.logger.error(f"Failed start: {e}")
            return False

    def stop(self):
        if self.driver:
            logging.getLogger("urllib3").setLevel(logging.CRITICAL)
            logging.getLogger("selenium").setLevel(logging.CRITICAL)
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.logger.info("Browser Closed.")

    def navigate_to(self, url):
        if self.driver:
            self.driver.get(url)

