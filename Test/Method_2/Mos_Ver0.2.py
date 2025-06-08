import pyautogui
import time

class MouseSteering:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2
        self.prev_quadrant = None
        self.rotation_score = 0.0  # Tracks rotation progress
        self.current_direction = None  # "Clockwise" or "Counterclockwise"
        self.sequence = []  # Stores quadrant transition history
        self.valid_sequences = {
            "Clockwise": ["Top", "Right", "Bottom", "Left"],
            "Counterclockwise": ["Top", "Left", "Bottom", "Right"]
        }
        self.full_cycle = False  # Track if full cycle completed before reaching top
        
        pyautogui.moveTo(self.center_x, 0)  # Start at top-center
        self.track_mouse()
    
    def get_quadrant(self, x, y):
        if y < self.center_y and x >= self.center_x:
            return "Top"
        elif x >= self.center_x and y >= self.center_y:
            return "Right"
        elif y >= self.center_y and x < self.center_x:
            return "Bottom"
        elif x < self.center_x and y < self.center_y:
            return "Left"
    
    def track_mouse(self):
        while True:
            x, y = pyautogui.position()
            current_quadrant = self.get_quadrant(x, y)
            
            if current_quadrant and current_quadrant != self.prev_quadrant:
                if not self.sequence or current_quadrant != self.sequence[-1]:
                    self.sequence.append(current_quadrant)
                
                if len(self.sequence) > 4:
                    self.sequence.pop(0)  # Keep only last 4 transitions
                
                # Check if a full cycle was completed before reaching the top
                if self.sequence == self.valid_sequences["Clockwise"]:
                    self.full_cycle = "Clockwise"
                elif self.sequence == self.valid_sequences["Counterclockwise"]:
                    self.full_cycle = "Counterclockwise"
                
                # Only count a full rotation when reaching the exact top boundary
                if y == 0 and self.full_cycle:
                    if self.full_cycle == "Clockwise":
                        self.rotation_score += 1.0
                        self.current_direction = "Clockwise"
                    elif self.full_cycle == "Counterclockwise":
                        self.rotation_score -= 1.0
                        self.current_direction = "Counterclockwise"
                    
                    self.full_cycle = False  # Reset cycle tracking
                    self.sequence.clear()
                
                print(f"Rotation Score: {self.rotation_score:.2f} ({self.current_direction})")
                
            self.prev_quadrant = current_quadrant
            time.sleep(0.05)

if __name__ == "__main__":
    MouseSteering()
