import re
import time
import random
from dataclasses import dataclass
from typing import List, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from src.config import Config

@dataclass
class PuzzlePiece:
    id: str  # DOM Element ID or reference wrapper
    element: object
    current_index: int
    target_pos_x: float # background-position percentage x
    target_pos_y: float # background-position percentage y
    
    # Grid coordinates derived from background-position
    target_col: int = -1
    target_row: int = -1
    
    # For debugging
    def __repr__(self):
        return f"Piece(idx={self.current_index}, target=({self.target_col}, {self.target_row}))"

class PuzzleSolver:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        
    def _parse_percentage(self, val_str: str) -> float:
        if not val_str: return 0.0
        # Remove % using regex or string replace
        clean = val_str.replace('%', '').strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0

    def scan_board(self) -> List[PuzzlePiece]:
        """
        Scans the DOM to find puzzle pieces using a single JS call for maximum speed.
        """
        # Optimized JS payload to extract all piece data in one round-trip
        # We look for divs with inline background-position which implies they are puzzle pieces
        script = """
        const pieces = [];
        const allDivs = document.querySelectorAll('div[style*="background-position"]');
        
        for (let div of allDivs) {
            // Must be visible
            if (div.offsetParent === null) continue;
            
            const rect = div.getBoundingClientRect();
            const style = div.style; // Read inline style directly for target pos
            
            // Only consider meaningful pieces
            if (rect.width < 10 || rect.height < 10) continue;
            
            pieces.push({
                // We can't pass the element reference back easily in a clean list without ID, 
                // but we can query it later or just pass the list of elements if needed.
                // Actually for perform_swap we need the WebElement.
                // Selenium execute_script can return a list of objects containing WebElements!
                element: div,
                rect_x: rect.x + window.scrollX,
                rect_y: rect.y + window.scrollY,
                style_bg: style.backgroundPosition
            });
        }
        return pieces;
        """
        
        try:
            raw_data = self.driver.execute_script(script)
        except Exception as e:
            print(f"Error in JS scan: {e}")
            return []

        if not raw_data:
            return []

        pieces = []
        for i, data in enumerate(raw_data):
            el = data['element']
            bg_pos = data['style_bg'] # e.g. "50% 20%"
            
            if not bg_pos: continue
            
            parts = bg_pos.split(' ')
            if len(parts) >= 2:
                x_pct = self._parse_percentage(parts[0])
                y_pct = self._parse_percentage(parts[1])
            else:
                x_pct = self._parse_percentage(parts[0])
                y_pct = 0.0

            pieces.append(PuzzlePiece(
                id=f"piece_{i}",
                element=el,
                current_index=-1, 
                target_pos_x=x_pct,
                target_pos_y=y_pct
            ))
            
            # Inject cached rect data to avoid wire call if we needed to sort
            # But the sorting logic below accesses .element.rect which calls wire.
            # We should attach the rect data to the object to sort in Python without wire calls
            pieces[-1]._cached_x = data['rect_x']
            pieces[-1]._cached_y = data['rect_y']

        # Sort pieces by current visual position (Top-Left to Bottom-Right)
        # Using CACHED coordinates to avoid wire calls
        if not pieces: return []
            
        # Determine rows
        pieces.sort(key=lambda p: p._cached_y)
        
        rows = []
        if pieces:
            current_row = [pieces[0]]
            current_y = pieces[0]._cached_y
            
            for p in pieces[1:]:
                # 15px tolerance
                if abs(p._cached_y - current_y) < 15: 
                    current_row.append(p)
                else:
                    rows.append(current_row)
                    current_row = [p]
                    current_y = p._cached_y
            rows.append(current_row)
            
        final_list = []
        current_idx = 0
        for r in rows:
            r.sort(key=lambda p: p._cached_x)
            for p in r:
                p.current_index = current_idx
                current_idx += 1
            final_list.extend(r)
            
        self._calculate_grid_targets(final_list)
        return final_list

    def _calculate_grid_targets(self, pieces: List[PuzzlePiece]):
        if not pieces: return
        
        # Collect all unique target X and Y percentages to detect grid size
        xs = sorted(list(set(p.target_pos_x for p in pieces)))
        ys = sorted(list(set(p.target_pos_y for p in pieces)))
        
        # Simple mapping
        x_map = {val: i for i, val in enumerate(xs)}
        y_map = {val: i for i, val in enumerate(ys)}
        
        for p in pieces:
            p.target_col = x_map.get(p.target_pos_x, 0)
            p.target_row = y_map.get(p.target_pos_y, 0)

    def solve(self):
        """
        Main execution method.
        """
        pieces = self.scan_board()
        if not pieces:
            return False

        # Re-derive cols count from pieces data
        if not pieces: return False
        max_col = max(p.target_col for p in pieces)
        cols = max_col + 1
        
        current_layout = list(pieces) 
        
        swaps_performed = 0
        # ROCKET MODE: 25 moves per batch. 
        # JS Scanning is fast, but we want to flow as much as possible.
        BATCH_SIZE = 25 
        
        for i in range(len(current_layout)):
            if swaps_performed >= BATCH_SIZE:
                # print(f"  -> Batch limit {BATCH_SIZE}. Rescanning...")
                return True

            target_r = i // cols
            target_c = i % cols
            
            current_p = current_layout[i]
            
            if current_p.target_row == target_r and current_p.target_col == target_c:
                continue 
                
            # Find the correct piece
            candidate_idx = -1
            for j in range(i + 1, len(current_layout)):
                p = current_layout[j]
                if p.target_row == target_r and p.target_col == target_c:
                    candidate_idx = j
                    break
            
            if candidate_idx != -1:
                # print(f"AZIONE: Sposto pezzo da {candidate_idx} a {i}")
                success = self.perform_swap(current_layout[i], current_layout[candidate_idx])
                
                if not success:
                    print("  -> Errore scambio (Stale). Riscansione.")
                    return True 
                
                current_layout[i], current_layout[candidate_idx] = current_layout[candidate_idx], current_layout[i]
                swaps_performed += 1
                
                # NO SLEEP - Full speed ahead
                # time.sleep(0.01)
        
        if swaps_performed == 0:
            return False
            
        return True

    def perform_swap(self, piece_a: PuzzlePiece, piece_b: PuzzlePiece) -> bool:
        """
        Executes Drag and Drop from A to B using ActionChains.
        Returns True if successful, False if error.
        ROCKET MODE: 10ms pauses. Just enough to register.
        """
        from selenium.webdriver.common.action_chains import ActionChains
        
        try:
            actions = ActionChains(self.driver)
            # Click & Hold -> Pause -> Move -> Pause -> Release
            # 0.01s (10ms) is the bare minimum for stability
            actions.click_and_hold(piece_b.element)\
                   .pause(0.01)\
                   .move_to_element(piece_a.element)\
                   .pause(0.01)\
                   .release().perform()
            return True
        except Exception as e:
            return False
