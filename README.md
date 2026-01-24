# 🌾 Tarabean Solver & Automation Tool

A high-performance, resilient automation bot for **Tarabean.com**, designed to solve **Memory** and **Puzzle** games automatically to maximize XP gain.

Built with **Python**, **Selenium**, and **Chrome WebDriver**. Optimized for background execution on Linux/Windows without resource throttling.

---

## ✨ Features

### 🚀 Core Capabilities
- **Multi-Threaded Workers**: Run multiple browser instances simultaneously.
- **Background Optimized**: Runs effectively in minimized or background windows (occluded) without pausing.
- **Silent Operation**: Zero console spam. all output is directed to `loginfo.txt`.

### 🧠 Smart Memory Solver
- **Coordinate Deduplication**: Uses a smart 80% zoom strategy to perfectly identify unique card slots, preventing "double counting" of DOM elements.
- **Visual Memory**: Memorizes card faces continuously.
- **Auto-Recovery**: Automatically detects and clicks "Try Again", "Close", and "Next Level" dialogs.
- **Stability Checks**: Waits for stable card counts before scanning to prevent misclicks during animations.

### 🛡️ Anti-Throttling & "God Mode"
Chrome normally throttles background tabs. This tool bypasses that using:
- **KeepAlive Extension**: A custom local extension that plays silent audio to trick Chrome's activity monitor.
- **Flag Overrides**: Disables `CalculateNativeWinOcclusion`, `background-timer-throttling`, and more.
- **Silent Zoom**: Forces `0.80` device scale factor natively to ensure game elements fit and don't overlap, without `send_keys` focus stealing.

---

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- Google Chrome installed

### Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Carloj005/tarabean-tools.git
    cd tarabean-tools
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(If requirements.txt is missing, install: `selenium`, `webdriver-manager`, `colorama`)*

---

## 🎮 Usage

Start the application:
```bash
python3 main.py
```

### Dashboard Controls
The CLI dashboard provides real-time status:

- **`1`**: Add a Memory Game Worker.
- **`2`**: Add a Puzzle Game Worker (Experimental).
- **`3`**: Stop all workers.
- **`Q`**: Quit the application.
- **`ENTER`**: Refresh the status view (Auto-refreshes every 10s).

---

## 📂 Project Structure

- **`main.py`**: Entry point. Handles global logger setup and app launch.
- **`src/`**:
    - **`app.py`**: CLI Dashboard and Worker Manager.
    - **`browser.py`**: Chrome configuration, flags, and extension loading.
    - **`worker.py`**: Threading logic for individual game instances.
    - **`memory.py`**: The logic brain for solving the Memory game.
    - **`puzzle.py`**: The logic brain for the Puzzle game.
    - **`config.py`**: Global settings (URLs, Timeouts).
    - **`logger.py`**: Centralized file-based logging system.
- **`extension/`**: Contains the `manifest.json` and `keepalive.js` for the anti-throttling extension.

---

## 🔍 Troubleshooting

**Q: The bot freezes at Level 2?**
A: This usually means the zoom level caused coordinate overlaps. The current version enforces `0.80` zoom which fixes this.

**Q: It says "Stuck Refresh"?**
A: If a worker detects no activity for 60 seconds (Config.STUCK_TIMEOUT), it auto-reloads the page to keep things moving.

**Q: Where are the logs?**
A: Check `loginfo.txt` in the root directory. It contains detailed execution steps for debugging.

---

**Disclaimer:** This tool is for educational purposes only. Use responsibly.
