import pyvjoy
import math
from pynput import mouse as pynput_mouse
from collections import deque

class MouseSteering:
    def __init__(self, app):
        self.app = app
        self.sensitivity = 1.0
        self.offset = 0.0
        self.angle = 0.0
        self.previous_angle = 0.0  # Keep track of the last angle
        self.rotation_direction = "None"  # Track rotation direction
        self.clockwise_degrees = 0  # Track clockwise rotation
        self.counterclockwise_degrees = 0  # Track counterclockwise rotation
        self.device = pyvjoy.VJoyDevice(1)  # Assume vJoy device 1
        self.mouse_listener = None
        self.direction_change_threshold = 10  # Set a threshold to prevent flickering
        self.max_degrees = 1080  # 3 full rotations (360° * 3)
        self.center_x = None  # Store center position for the mouse
        self.center_y = None  # Store center position for the mouse
        self.angle_history = deque(maxlen=5)  # Store recent angle changes for smoothing

    def start_steering(self):
        """Start the mouse listener for steering"""
        self.mouse_listener = pynput_mouse.Listener(on_move=self.on_move)
        self.mouse_listener.start()

    def stop_steering(self):
        """Stop the mouse listener"""
        if self.mouse_listener:
            self.mouse_listener.stop()

    def on_move(self, x, y):
        """Handle mouse move event and calculate steering angle"""
        # Get the center of the screen
        if self.center_x is None or self.center_y is None:
            screen_width = self.app.root.winfo_screenwidth()
            screen_height = self.app.root.winfo_screenheight()
            self.center_x, self.center_y = screen_width // 2, screen_height // 2

        # Calculate the offset (distance from center)
        self.offset = math.sqrt((x - self.center_x) ** 2 + (y - self.center_y) ** 2)

        # Calculate the angle
        self.angle = math.degrees(math.atan2(y - self.center_y, x - self.center_x))

        # Add the angle to the history for smoothing
        self.angle_history.append(self.angle)

        # Get the smoothed angle using the moving average of recent values
        smoothed_angle = sum(self.angle_history) / len(self.angle_history)

        # Check if mouse is at the center
        if self.offset < 10:  # Consider it centered if offset is less than 10 pixels
            self.reset_degrees()

        # Calculate the degrees and update direction
        self.calculate_rotation(smoothed_angle)

        # Update the app's display
        self.app.update_offset_and_angle(self.offset, smoothed_angle, self.rotation_direction,
                                          self.clockwise_degrees, self.counterclockwise_degrees)

        # Map the calculated angle to vJoy input
        self.device.set_axis(pyvjoy.HID_USAGE_X, int(smoothed_angle * self.sensitivity))
        self.app.root.after(0, self.app.update_offset_and_angle, self.offset, smoothed_angle, self.rotation_direction,
                        self.clockwise_degrees, self.counterclockwise_degrees)
    def calculate_rotation(self, smoothed_angle):
        """Calculate rotation direction and track degrees turned"""
        # Calculate delta angle (difference from previous angle)
        delta_angle = smoothed_angle - self.previous_angle
        
        # Normalize the delta to handle wrapping around at 360/0 degrees
        if delta_angle > 180:
            delta_angle -= 360
        elif delta_angle < -180:
            delta_angle += 360

        # Update previous angle to the current smoothed angle for next calculation
        self.previous_angle = smoothed_angle

        # Track the direction and accumulate degrees
        if delta_angle > self.direction_change_threshold:  # Clockwise movement
            if self.rotation_direction != "Clockwise":
                # Reset counterclockwise degrees when direction changes
                self.counterclockwise_degrees = 0
                self.rotation_direction = "Clockwise"
            if self.clockwise_degrees < self.max_degrees:
                self.clockwise_degrees += abs(delta_angle)  # Add degrees for clockwise rotation
            else:
                self.rotation_direction = "None"  # Stop further clockwise movement

        elif delta_angle < -self.direction_change_threshold:  # Counterclockwise movement
            if self.rotation_direction != "Counterclockwise":
                # Reset clockwise degrees when direction changes
                self.clockwise_degrees = 0
                self.rotation_direction = "Counterclockwise"
            if self.counterclockwise_degrees < self.max_degrees:
                self.counterclockwise_degrees += abs(delta_angle)  # Add degrees for counterclockwise rotation
            else:
                self.rotation_direction = "None"  # Stop further counterclockwise movement

        # Ensure that after 3 full rotations (1080 degrees), the direction stops
        if self.clockwise_degrees >= self.max_degrees:
            self.clockwise_degrees = self.max_degrees  # Cap at 1080 degrees

        if self.counterclockwise_degrees >= self.max_degrees:
            self.counterclockwise_degrees = self.max_degrees  # Cap at 1080 degrees

    def reset_degrees(self):
        """Reset all rotation degree counters if the mouse is centered"""
        self.clockwise_degrees = 0
        self.counterclockwise_degrees = 0
        self.rotation_direction = "None"
        self.previous_angle = self.angle  # Reset previous angle to avoid sudden jumps
