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
        Scans the DOM to find puzzle pieces and determines their correct positions.
        Proprietary logic for tarabean: 
        Usually pieces are <div>s with a background-image and background-position.
        Return: List of PuzzlePiece sorted by their CURRENT visual position (top-left to bottom-right).
        """
        # Note: Selectors depend on the actual site structure. 
        # Since I cannot browse, I will assume a standard list of div elements container.
        # Based on prompt hints: "Riferimento all'elemento DOM", "rect (x, y)", "background-position"
        
        # We need to find the container. Let's assume there is a main puzzle container.
        # We'll use a generic approach to find pieces. Often they share a class.
        # Let's try to get all children of the grid container.
        
        # JS script to get all necessary data in one go for speed
        script = """
        const pieces = [];
        // Heuristic: Find all elements that look like puzzle tiles.
        // Often they have background-image set.
        // We look for a container... let's try to identify all divs that have background-position
        // Inside the game container. 
        
        // Let's assume the user starts the level and pieces appear.
        // We select via class. If unknown, we might need manual adjustment.
        // Prompt says: "https://tarabean.com/puzzle"
        // Let's assume a common class name or just select all likely children.
        
        // For the sake of this code, I'll search for elements with 'background-position' style inline
        // or effectively applied.
        
        const allDivs = document.querySelectorAll('div');
        const tileCandidates = [];
        
        for (let div of allDivs) {
            // Filter: Must have background-image and be visible
            const style = window.getComputedStyle(div);
            if (style.backgroundImage !== 'none' && style.backgroundPosition !== '0% 0%' && div.offsetWidth > 0) {
                 // Check if it's a tile part of a grid (siblings check?) 
                 // Let's assume the puzzle pieces are siblings in a specific container.
                 // This is a heuristic.
            }
        }
        
        // BETTER APPROACH based on prompt "Automation Controller".
        // Let's assume we pass a CSS selector or we find the grid container first.
        // Let's assume the pieces are '.puzzle-piece' or similar.
        // If not, we take ALL elements in the main game area.
        
        // Let's try to return data for a known selector, or 'div[style*="background-position"]'
        
        const nodes = document.querySelectorAll('div[data-v-app] .puzzle-piece, .tile, div[style*="background-position"]'); 
        // We iterate and return properties
        
        // Note: The Prompt says "Estrazione Dati: execute_script per estrarre ... background-position"
        // Let's return just the minimal needed and do logic in Python.
        
        const results = [];
        // We need to order them by visual position (DOM order might not be visual order if absolute pos?)
        // If absolute pos, use getBoundingClientRect. If flex/grid, DOM order is *usually* visual order? 
        // Not necessarily. 
        
        // Let's rely on getBoundingClientRect to sort them visually.
        
        const elements = Array.from(document.querySelectorAll('.piece, .tile, div[class*="piece"], div[class*="tile"]'));
        // Fallback if class names don't match, try to find by structure
        
        for (let i = 0; i < elements.length; i++) {
            const el = elements[i];
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            
            // Filter out non-puzzle elements (too small, no bg)
            if (rect.width < 20 || style.backgroundImage === 'none') continue;
            
            results.push({
                index: i, // DOM index reference (we can use this to grab it back)
                x: rect.x,
                y: rect.y,
                bgPos: style.backgroundPosition
            });
        }
        return results;
        """
        
        # NOTE: Since I don't know the exact class name, I will start with a broad selector
        # and rely on the Python side to filter/structure.
        # But wait, the user instructions implied I should write a "Vision/Logic Module".
        
        # Let's refine the script to be cleaner.
        
        pieces_data = self.driver.execute_script("""
            // Helper to get BG pos
            function getBgPos(el) {
                return window.getComputedStyle(el).backgroundPosition;
            }
            
            // Heuristic to identify the board container
            // We look for a container with many children of same size
            // This is a common pattern.
            
            // For now, let's grab all divs that look like pieces.
            // We assume pieces have a background image.
            
            let candidates = Array.from(document.querySelectorAll('div'));
            candidates = candidates.filter(el => {
                const s = window.getComputedStyle(el);
                return s.backgroundImage.includes('url') && s.position !== 'static'; 
                // Usually absolute or relative?
            });
            
            // If too many, filter by a common parent? 
            // Let's just return rects and filter in Python.
            
            return candidates.map((el, idx) => {
                const r = el.getBoundingClientRect();
                return {
                   'rect_x': r.x,
                   'rect_y': r.y,
                   'bg_pos': getBgPos(el),
                   'dom_ref_idx': idx // this won't work well over JSON, we can't pass DOM element refs back easily in bulk
                                      // Actually we can pass WebElements in list
                };
            });
        """)
        
        # Actually, Selenium execute_script CAN return WebElements.
        # Let's do that.
        
        raw_pieces = self.driver.find_elements(By.XPATH, "//div[contains(@style, 'background-position')]")
        # Retry with a different strategy if empty? 
        # For this code I'll assume we can use a CSS selector. 
        # I'll use a generic one that matches typical draggable tiles.
        if not raw_pieces:
            raw_pieces = self.driver.find_elements(By.CSS_SELECTOR, ".puzzle-piece, .tile")

        pieces = []
        for i, el in enumerate(raw_pieces):
            if not el.is_displayed(): continue
            
            # Get data
            pos = el.value_of_css_property("background-position") # e.g. "50% 20%"
            rect = el.rect # {'x': ..., 'y': ...}
            
            # Skip if no background position
            if not pos or pos == 'initial': continue
            
            parts = pos.split(' ')
            if len(parts) >= 2:
                x_pct = self._parse_percentage(parts[0])
                y_pct = self._parse_percentage(parts[1])
            else:
                x_pct = self._parse_percentage(parts[0])
                y_pct = 0.0 # Default
            
            pieces.append(PuzzlePiece(
                id=f"piece_{i}",
                element=el,
                current_index=-1, # To be determined by sort
                target_pos_x=x_pct,
                target_pos_y=y_pct
            ))
            
        # Sort pieces by current visual position (Top-Left to Bottom-Right)
        # Sort by Y first, then X (with some tolerance for row alignment)
        # Simple clustering for rows:
        if not pieces:
            return []
            
        # Determine rows
        # Sort by Y
        pieces.sort(key=lambda p: p.element.rect['y'])
        
        # Group by row (within 10px tolerance)
        rows = []
        if pieces:
            current_row = [pieces[0]]
            current_y = pieces[0].element.rect['y']
            
            for p in pieces[1:]:
                if abs(p.element.rect['y'] - current_y) < 15: # 15px tolerance
                    current_row.append(p)
                else:
                    rows.append(current_row)
                    current_row = [p]
                    current_y = p.element.rect['y']
            rows.append(current_row)
            
        # Sort each row by X
        final_list = []
        current_idx = 0
        for r in rows:
            r.sort(key=lambda p: p.element.rect['x'])
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
        
        cols = len(xs)
        rows_count = len(ys)
        
        for p in pieces:
            p.target_col = x_map.get(p.target_pos_x, 0)
            p.target_row = y_map.get(p.target_pos_y, 0)

    def solve(self):
        """
        Main execution method.
        """
        pieces = self.scan_board()
        if not pieces:
            return

        # print(f"DEBUG: Found {len(pieces)} pieces. Targets: {[(p.target_col, p.target_row) for p in pieces]}")
        
        # Re-derive cols count from pieces data
        max_col = max(p.target_col for p in pieces)
        cols = max_col + 1
        
        current_layout = list(pieces) 
        
        swaps_performed = 0
        for i in range(len(current_layout)):
            target_r = i // cols
            target_c = i % cols
            
            current_p = current_layout[i]
            
            # Check if current piece at i is the correct one
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
                print(f"SWAP ACTION: Move piece from visual idx {candidate_idx} to {i}")
                self.perform_swap(current_layout[i], current_layout[candidate_idx])
                
                # Update internal model
                current_layout[i], current_layout[candidate_idx] = current_layout[candidate_idx], current_layout[i]
                swaps_performed += 1
                
                # Jitter
                time.sleep(random.uniform(Config.MIN_JITTER, Config.MAX_JITTER))
        
        if swaps_performed == 0:
            # print("No moves needed or puzzle already solved.")
            return False
            
        return True

    def perform_swap(self, piece_a: PuzzlePiece, piece_b: PuzzlePiece):
        """
        Executes Drag and Drop from A to B using ActionChains (more robust).
        """
        from selenium.webdriver.common.action_chains import ActionChains
        
        try:
            # ActionChains
            actions = ActionChains(self.driver)
            # Click & Hold Source -> Move to Target -> Release
            # FASTEST POSSIBLE
            actions.click_and_hold(piece_b.element)\
                   .move_to_element(piece_a.element)\
                   .release().perform()
        except Exception as e:
            print(f"  -> Swap error (ActionChains): {e}")


