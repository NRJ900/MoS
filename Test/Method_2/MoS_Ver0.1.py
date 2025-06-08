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
                self.sequence.append(current_quadrant)
                
                if len(self.sequence) > 4:
                    self.sequence.pop(0)  # Keep only last 4 transitions
                
                if self.sequence == ["Top", "Right", "Bottom", "Left"]:
                    new_direction = "Clockwise"
                    if self.current_direction == "Counterclockwise":
                        self.rotation_score -= 0.25  # Reduce counterclockwise progress
                    else:
                        self.rotation_score += 0.25
                    self.sequence.clear()
                elif self.sequence == ["Top", "Left", "Bottom", "Right"]:
                    new_direction = "Counterclockwise"
                    if self.current_direction == "Clockwise":
                        self.rotation_score += 0.25  # Reduce clockwise progress
                    else:
                        self.rotation_score -= 0.25
                    self.sequence.clear()
                else:
                    new_direction = self.current_direction
                
                self.current_direction = new_direction
                print(f"Rotation Score: {self.rotation_score:.2f} ({self.current_direction})")
                
            self.prev_quadrant = current_quadrant
            time.sleep(0.05)

if __name__ == "__main__":
    MouseSteering()
