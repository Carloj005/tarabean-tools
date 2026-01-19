import os
from pathlib import Path

class Config:
    # Chrome Configuration
    CHROME_BINARY_PATH = "/usr/bin/google-chrome-stable"
    # Original Source Profile
    SOURCE_PROFILE_DIR = os.path.expanduser("~/.config/google-chrome/")
    # Where to copy it for the bot (avoids lock conflicts)
    CLONE_PROFILE_DIR = os.path.expanduser("~/tarabean_bot_profile")
    
    # Target URL
    PUZZLE_URL = "https://tarabean.com/puzzle"
    
    # Timing (Seconds) - ULTRA TURBO MODE
    MIN_JITTER = 0.005
    MAX_JITTER = 0.02
    PAGE_LOAD_TIMEOUT = 30
    REFRESH_INTERVAL = 1800 # 30 Minutes
    STUCK_TIMEOUT = 60 # 1 Minute (Reload if nothing happens)
    
    @staticmethod
    def get_chrome_path():
        if os.path.exists(Config.CHROME_BINARY_PATH):
            return Config.CHROME_BINARY_PATH
        return None

    @staticmethod
    def validate():
        if not os.path.exists(Config.CHROME_BINARY_PATH):
            print(f"WARNING: Chrome binary not found at {Config.CHROME_BINARY_PATH}")
        if not os.path.exists(Config.SOURCE_PROFILE_DIR):
            print(f"WARNING: Source profile dir not found at {Config.SOURCE_PROFILE_DIR}")
