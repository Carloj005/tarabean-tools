import sys
import threading
import select
import time
from .config import Config
from .worker import GameWorker

class App:
    def __init__(self):
        self.workers = []
        self.next_worker_id = 1
        
    def clear_screen(self):
        print("\033[H\033[J", end="") 

    def home_menu(self):
        while True:
            # 1. Print Status Dashboard
            self.clear_screen()
            print("\n" + "="*50)
            print("       COMMAND CENTER v3.3 - AUTO DASHBOARD (10s)")
            print("="*50)
            print(f" ACTIVE WORKERS: {len(self.workers)}")
            print("-" * 50)
            
            if not self.workers:
                print(" [No active workers]")
            else:
                for w in self.workers:
                    status_str = w.status
                    if "RUNNING" in status_str: status_str = f"\033[92m{status_str}\033[0m"
                    elif "ERROR" in status_str: status_str = f"\033[91m{status_str}\033[0m"
                    
                    print(f" [ID: {w.worker_id}] {w.game_type:<8} | {w.difficulty:<8} | Solved: {w.items_solved:<3} | {status_str}")
            
            print("-" * 50)
            print(" [A] Add Puzzle Worker")
            print(" [M] Add Memory Worker")
            print(" [S] Stop Specific Worker")
            print(" [Q] Quit / Kill All")
            print(" [ENTER] Refresh Status Now")
            print("="*50)
            print(" (Auto-refreshing in 10s...)")
            print(" Command: ", end='', flush=True)

            # 2. Non-blocking Input Check (Timeout 10s)
            # If user types nothing, it refreshes. If user types, we read it.
            rlist, _, _ = select.select([sys.stdin], [], [], 10.0)
            if rlist:
                line = sys.stdin.readline().strip().lower()
                
                if line == 'a':
                    self.spawn_puzzle_menu()
                elif line == 'm':
                    self.spawn_worker(game_type="MEMORY", difficulty="N/A")
                elif line == 's':
                    self.stop_worker_menu()
                elif line == 'q':
                    print("Shutting down all workers...")
                    self.clean_up()
                    sys.exit(0)
            else:
                # Timeout reached -> Refresh loop
                pass
                
    def spawn_puzzle_menu(self):
        self.clear_screen()
        print("\n" + "="*40)
        print(" ➕ CONFIGURE NEW PUZZLE WORKER")
        print("="*40)
        print("1. Random Difficulty (Default)")
        print("2. Fixed Easy")
        print("3. Fixed Normal")
        print("4. Fixed Hard")
        print("5. Cancel")
        
        c = input("Choice: ").strip()
        diff = "RANDOM"
        if c == '2': diff = "Easy"
        elif c == '3': diff = "Normal"
        elif c == '4': diff = "Hard"
        elif c == '5': return
        
        self.spawn_worker(game_type="PUZZLE", difficulty=diff)

    def spawn_worker(self, game_type, difficulty):
        print(f"Launching Worker {self.next_worker_id} ({game_type} - {difficulty})...")
        
        worker = GameWorker(worker_id=self.next_worker_id, game_type=game_type, difficulty=difficulty)
        worker.start()
        
        self.workers.append(worker)
        self.next_worker_id += 1
        time.sleep(1) # Visual feedback

    def stop_worker_menu(self):
        if not self.workers:
            print("No workers needed.")
            time.sleep(1)
            return

        wd = input("Enter Worker ID to Stop: ").strip()
        try:
            wid = int(wd)
            target = next((w for w in self.workers if w.worker_id == wid), None)
            if target:
                print(f"Stopping Worker {wid}...")
                target.stop()
                self.workers.remove(target)
                print("Worker removed.")
                time.sleep(1)
            else:
                print("Worker ID not found.")
                time.sleep(1)
        except:
            print("Invalid input.")
            time.sleep(1)

    def run(self):
        try:
            Config.validate()
            self.home_menu()
        except KeyboardInterrupt:
            self.clean_up()
        finally:
            self.clean_up()

    def clean_up(self):
        print("\nStopping all workers...")
        for w in self.workers:
            w.stop()
        self.workers.clear()
        print("Clean up complete.")
