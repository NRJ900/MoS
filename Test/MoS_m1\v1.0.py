import pyvjoy
import tkinter as tk
from pynput import mouse as pynput_mouse
import ctypes
import time

class MouseSteeringApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mouse Steering Control")
        
        self.vjoy_device = None
        try:
            self.vjoy_device = pyvjoy.VJoyDevice(1)
        except pyvjoy.exceptions.vJoyFailedToAcquireException as e:
            print(f"Error acquiring vJoy device: {e}")
        
        self.sensitivity = 1.0
        self.is_steering = False

        self.update_center_position()  # Initialize center position
        self.create_widgets()
        self.center_mouse()            # Center mouse cursor at start
        self.mouse_listener = pynput_mouse.Listener(on_move=self.on_move)

    def create_widgets(self):
        self.start_button = tk.Button(self.root, text="Start", command=self.start_steering)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(self.root, text="Stop", command=self.stop_steering)
        self.stop_button.pack(pady=5)

        self.sensitivity_slider = tk.Scale(self.root, from_=0.1, to=10, orient=tk.HORIZONTAL, resolution=0.1, command=self.update_sensitivity)
        self.sensitivity_slider.set(self.sensitivity)
        self.sensitivity_slider.pack(pady=5)

        self.sensitivity_label = tk.Label(self.root, text=f"Sensitivity: {self.sensitivity}")
        self.sensitivity_label.pack(pady=5)

        self.indicator_frame = tk.Frame(self.root)
        self.indicator_frame.pack(pady=20)

        self.left_indicator = tk.Label(self.indicator_frame, text="Left", bg="white", width=10)
        self.left_indicator.grid(row=0, column=0, padx=5)

        self.center_indicator = tk.Label(self.indicator_frame, text="Center", bg="white", width=10)
        self.center_indicator.grid(row=0, column=1, padx=5)

        self.right_indicator = tk.Label(self.indicator_frame, text="Right", bg="white", width=10)
        self.right_indicator.grid(row=0, column=2, padx=5)

        self.angle_label = tk.Label(self.root, text="Turn Angle: 0%")
        self.angle_label.pack(pady=5)

        self.offset_label = tk.Label(self.root, text="Offset: 0%")
        self.offset_label.pack(pady=5)

    def update_center_position(self):
        # Fetch screen dimensions using ctypes for better accuracy
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()  # Ensures correct values in case of display scaling
        self.screen_width = user32.GetSystemMetrics(0)  # Primary screen width
        self.screen_height = user32.GetSystemMetrics(1)  # Primary screen height
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2
        
        # Debug print to verify correct screen size
        print(f"Screen width: {self.screen_width}, Screen height: {self.screen_height}")
        print(f"Calculated Center: ({self.center_x}, {self.center_y})")

    def start_steering(self):
        if not self.is_steering and self.vjoy_device:
            self.is_steering = True
            self.center_mouse()
            time.sleep(0.1)  # Small delay to ensure the mouse position stabilizes
            self.mouse_listener.start()

    def stop_steering(self):
        if self.is_steering:
            self.is_steering = False
            self.mouse_listener.stop()

    def on_move(self, x, y):
        if self.is_steering and self.vjoy_device:
            delta_x = x - self.center_x

            # Calculate turn angle considering sensitivity
            turn_angle = (delta_x / (self.screen_width // 2)) * self.sensitivity
            
            # Ensure turn_angle is within the range [-1, 1]
            turn_angle = max(min(turn_angle, 1), -1)
            axis_value = int((turn_angle + 1) * 16383)  # Map turn_angle [-1, 1] to axis_value [0, 32767]
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, axis_value)

            # Calculate offset percentage with proper bounds
            offset_percentage = (delta_x / (self.screen_width // 2)) * 100
            offset_percentage = max(min(offset_percentage, 100), -100)
            
            # Ensure proper display format for direction
            direction = 'Left' if offset_percentage < 0 else 'Right'
            
            self.update_indicator(turn_angle)
            self.angle_label.config(text=f"Turn Angle: {round(turn_angle * 100, 2)}%")
            self.offset_label.config(text=f"Offset: {round(offset_percentage, 2)}% {direction}")

    def update_indicator(self, angle):
        if angle < -0.1:
            self.left_indicator.config(bg="red")
            self.center_indicator.config(bg="white")
            self.right_indicator.config(bg="white")
        elif angle > 0.1:
            self.left_indicator.config(bg="white")
            self.center_indicator.config(bg="white")
            self.right_indicator.config(bg="red")
        else:
            self.left_indicator.config(bg="white")
            self.center_indicator.config(bg="green")
            self.right_indicator.config(bg="white")

    def update_sensitivity(self, value):
        self.sensitivity = float(value)
        self.sensitivity_label.config(text=f"Sensitivity: {self.sensitivity}")

    def center_mouse(self):
        # Center the mouse cursor on the screen (Windows-specific)
        ctypes.windll.user32.SetCursorPos(self.center_x, self.center_y)
        time.sleep(0.1)  # Ensure stability after centering

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseSteeringApp(root)
    root.mainloop()
