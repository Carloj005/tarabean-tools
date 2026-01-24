#!/usr/bin/env python3
import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.app import App
from src.logger import GlobalLogger

def main():
    GlobalLogger.setup()
    app = App()
    app.run()

if __name__ == "__main__":
    main()
