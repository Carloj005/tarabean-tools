import logging
import time
from .config import Config

class GlobalLogger:
    _instance = None

    @staticmethod
    def setup():
        # Clean/Overwrite log file on startup
        with open(Config.LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"=== TARABEAN SOLVER SESSION LOG {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    @staticmethod
    def log(component, message):
        timestamp = time.strftime('%H:%M:%S')
        line = f"[{timestamp}] [{component}] {message}\n"
        try:
            with open(Config.LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except:
            pass # Don't crash on log error
