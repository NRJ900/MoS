import math
import time # For performance measurement if needed
from collections import deque
import pyvjoy
from pynput import mouse as pynput_mouse

from constants import MAX_VJOY_AXIS, MIN_VJOY_AXIS, CENTER_VJOY_AXIS

class SteeringLogic:
    """
    Handles the core logic for mouse steering, including mouse input processing,
    angle calculations, vJoy output, and communication with the GUI.
    """
    def __init__(self, app_callback=None):
        self.app_callback = app_callback  # Callback function to send data/status to the GUI

        # Steering parameters
        self.sensitivity = 1.0  # Multiplier for steering responsiveness (currently not deeply integrated for 1:1 mapping)
        self.max_degrees = 1080  # Max steering lock: 3 full rotations (3 * 360°)
        self.direction_change_threshold = 1.0  # Degrees: Min change to detect rotation; adjusted from 10
        self.mouse_center_threshold = 15  # Pixels: Radius to consider mouse as centered

        # State variables
        self.current_raw_angle = 0.0  # Current angle from atan2
        self.previous_smoothed_angle = 0.0 # Previous smoothed angle for delta calculation

        self.total_accumulated_degrees = 0.0 # Net rotation: positive for clockwise, negative for counter-clockwise

        self.rotation_direction = "None"  # "Clockwise", "Counterclockwise", or "None"

        self.current_offset = 0.0 # Distance of mouse from center

        self.angular_velocity = 0.0 # Degrees per event
        self.previous_angular_velocity = 0.0
        self.angular_acceleration = 0.0 # Change in velocity

        # Screen and mouse position
        self.screen_center_x = None
        self.screen_center_y = None

        # Smoothing
        self.angle_history = deque(maxlen=5) # For smoothing raw angle
        self.last_event_time = None

        # vJoy and mouse listener
        self.vjoy_device = None
        self.mouse_listener = None
        self.is_steering = False

        self._initialize_vjoy()

    def _initialize_vjoy(self):
        """
        Initializes the vJoy device.
        Attempts to acquire vJoy device 1 and sets its X-axis to center.
        Notifies the GUI about the connection status.
        """
        try:
            self.vjoy_device = pyvjoy.VJoyDevice(1)
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, CENTER_VJOY_AXIS) # Center on init
            print("vJoy device initialized and centered.")
            if self.app_callback:
                self.app_callback("vjoy_status", "vJoy Connected")
        except pyvjoy.exceptions.vJoyFailedToAcquireException as e:
            print(f"Error acquiring vJoy device: {e}")
            self.vjoy_device = None
            if self.app_callback:
                self.app_callback("vjoy_status", f"vJoy Error: {e}")
        except Exception as e: # Catch other potential errors like vJoy not installed
            print(f"General vJoy Error: {e}")
            self.vjoy_device = None
            if self.app_callback:
                self.app_callback("vjoy_status", "vJoy Not Found or Error")


    def set_screen_center(self, center_x, center_y):
        """
        Sets the screen center coordinates, used as the reference point for angle calculations.
        This should be called by the GUI after obtaining screen dimensions.
        """
        self.screen_center_x = center_x
        self.screen_center_y = center_y
        # Reset angles when screen center is defined/redefined to prevent jumps
        # Initialize with current mouse pos relative to new center
        current_mouse_pos = pyvjoy.utils.get_mouse_position() # pynput might be better if listener can be temporarily used
        self.previous_smoothed_angle = self._calculate_raw_angle(current_mouse_pos['x'], current_mouse_pos['y'])
        self.angle_history.clear()
        for _ in range(self.angle_history.maxlen): # Fill history to avoid jerky start
            self.angle_history.append(self.previous_smoothed_angle)


    def _calculate_raw_angle(self, x, y):
        """Calculates the raw angle of the mouse position (x, y) relative to the screen center."""
        if self.screen_center_x is None or self.screen_center_y is None:
            # This should ideally not happen if set_screen_center is called at GUI init.
            print("Error: Screen center not defined for angle calculation.")
            return 0.0
        return math.degrees(math.atan2(y - self.screen_center_y, x - self.screen_center_x))

    def start_steering(self):
        """
        Starts the mouse steering process.
        Initializes state variables and starts the pynput mouse listener.
        """
        if self.is_steering:
            print("Steering already active.")
            return

        if not self.vjoy_device:
            print("Cannot start steering: vJoy device not available.")
            if self.app_callback:
                self.app_callback("error", "vJoy device not available. Cannot start.")
            return

        if self.screen_center_x is None or self.screen_center_y is None:
            # This should be set by the GUI before starting
            print("Error: Screen center not set before starting steering.")
            if self.app_callback:
                self.app_callback("error", "Screen center not set. Please ensure GUI initializes it.")
            return

        self.is_steering = True
        # Reset state variables
        # Keep total_accumulated_degrees unless explicitly reset by user
        self.previous_smoothed_angle = self._calculate_raw_angle(pyvjoy.utils.get_mouse_position()['x'], pyvjoy.utils.get_mouse_position()['y'])
        self.angle_history.clear()
        for _ in range(self.angle_history.maxlen):
             self.angle_history.append(self.previous_smoothed_angle)
        self.angular_velocity = 0.0
        self.previous_angular_velocity = 0.0
        self.angular_acceleration = 0.0
        self.rotation_direction = "None"
        self.last_event_time = time.perf_counter()

        self.mouse_listener = pynput_mouse.Listener(on_move=self.on_move)
        self.mouse_listener.start()
        print("Steering started.")
        if self.app_callback:
            self.app_callback("status", "Steering Active")


    def stop_steering(self):
        """
        Stops the mouse steering process.
        Stops the mouse listener and centers the vJoy device axis.
        """
        if not self.is_steering:
            print("Steering not active.")
            return

        self.is_steering = False
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None # Allow garbage collection

        if self.vjoy_device:
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, CENTER_VJOY_AXIS) # Center vJoy on stop

        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0
        # Keep total_accumulated_degrees for potential resume or display
        print("Steering stopped.")
        if self.app_callback:
            self.app_callback("status", "Steering Stopped")

    def on_move(self, x, y):
        """
        Callback function for mouse movement events from pynput listener.
        This is the core of the steering logic, processing mouse input to update steering state.
        Parameters:
            x (int): Current mouse x-coordinate.
            y (int): Current mouse y-coordinate.
        """
        if not self.is_steering or self.screen_center_x is None:
            return

        # Optional: Calculate time delta for more accurate physics if needed.
        # current_time = time.perf_counter()
        # time_delta = current_time - (self.last_event_time if self.last_event_time else current_time)
        # self.last_event_time = current_time

        # 1. Calculate Offset from screen center
        self.current_offset = math.sqrt((x - self.screen_center_x)**2 + (y - self.screen_center_y)**2)

        # 2. Calculate Raw Angle and apply Smoothing
        self.current_raw_angle = self._calculate_raw_angle(x, y)
        self.angle_history.append(self.current_raw_angle) # Add current angle to history deque
        current_smoothed_angle = sum(self.angle_history) / len(self.angle_history) # Moving average

        # 3. Calculate Delta Angle (change in angle since last event)
        # This serves as a proxy for angular velocity for the current discrete mouse event.
        delta_angle = current_smoothed_angle - self.previous_smoothed_angle

        # Normalize delta_angle to handle angle wrap-around (e.g., from -170 to +170 degrees is a 20 deg change, not 340)
        if delta_angle > 180: # Clockwise wrap
            delta_angle -= 360
        elif delta_angle < -180: # Counter-clockwise wrap
            delta_angle += 360

        self.angular_velocity = delta_angle # Degrees per mouse event

        # 4. Calculate Angular Acceleration (change in angular velocity)
        self.angular_acceleration = self.angular_velocity - self.previous_angular_velocity
        self.previous_angular_velocity = self.angular_velocity # Store current velocity for next event's acceleration calc

        # 5. Update Rotation Direction and Accumulated Steering Degrees
        if self.current_offset < self.mouse_center_threshold:
            # If mouse is physically near the screen center, consider it neutral input for rotation.
            # This helps prevent drift when the user intends to stop turning but mouse isn't perfectly still.
            self.rotation_direction = "None"
            # Note: total_accumulated_degrees is not reset here; user must use "Recenter View" or stop/start.
        elif delta_angle > self.direction_change_threshold: # Clockwise movement
            self.rotation_direction = "Clockwise"
            self.total_accumulated_degrees += abs(delta_angle) # Accumulate positive degrees
        elif delta_angle < -self.direction_change_threshold: # Counter-clockwise movement
            self.rotation_direction = "Counterclockwise"
            self.total_accumulated_degrees -= abs(delta_angle) # Accumulate negative degrees (effectively)
        else:
            # If delta_angle is too small, consider it "None" to avoid jitter
            self.rotation_direction = "None"

        # Clamp total_accumulated_degrees to the defined maximum steering lock
        self.total_accumulated_degrees = max(-self.max_degrees, min(self.max_degrees, self.total_accumulated_degrees))

        # Update the previous_smoothed_angle for the next on_move event
        self.previous_smoothed_angle = current_smoothed_angle

        # 6. Update vJoy Device Output
        if self.vjoy_device:
            # Scale total_accumulated_degrees from [-max_degrees, max_degrees] to vJoy's [MIN_VJOY_AXIS, MAX_VJOY_AXIS] range.
            # The vJoy range is typically [0, 32767].
            # Step 1: Normalize total_accumulated_degrees to [0, 1]
            # Input range is self.max_degrees - (-self.max_degrees) = 2 * self.max_degrees
            if (2 * self.max_degrees) == 0: # Avoid division by zero if max_degrees is 0
                normalized_value = 0.5 # Center value
            else:
                normalized_value = (self.total_accumulated_degrees - (-self.max_degrees)) / (2 * self.max_degrees)

            # Step 2: Scale normalized value [0,1] to [MIN_VJOY_AXIS, MAX_VJOY_AXIS]
            axis_value = int(normalized_value * (MAX_VJOY_AXIS - MIN_VJOY_AXIS) + MIN_VJOY_AXIS)

            # Ensure the calculated axis_value is strictly within vJoy's bounds as a failsafe.
            axis_value = max(MIN_VJOY_AXIS, min(MAX_VJOY_AXIS, axis_value))
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, axis_value)

        # 7. Callback to GUI with updated data
        if self.app_callback:
            gui_data = {
                "offset": self.current_offset,
                "raw_angle": self.current_raw_angle, # Instantaneous angle of mouse
                "smoothed_angle": current_smoothed_angle, # Smoothed angle of mouse
                "total_accumulated_degrees": self.total_accumulated_degrees, # The "steering wheel" angle
                "rotation_direction": self.rotation_direction,
                "angular_velocity": self.angular_velocity,
                "angular_acceleration": self.angular_acceleration,
                "vjoy_axis_value": axis_value if self.vjoy_device else CENTER_VJOY_AXIS # Current vJoy output
            }
            self.app_callback("update_gui", gui_data)

    def reset_steering_view(self):
        """
        Resets the accumulated steering angle to zero and centers the vJoy output.
        This is callable by the GUI to allow the user to "re-center" their logical steering wheel.
        """
        self.total_accumulated_degrees = 0.0
        self.angular_velocity = 0.0
        self.previous_angular_velocity = 0.0
        self.angular_acceleration = 0.0
        # Recalculate previous_smoothed_angle based on current mouse position to avoid jump if steering continues
        try:
            mouse_pos = pyvjoy.utils.get_mouse_position()
            self.previous_smoothed_angle = self._calculate_raw_angle(mouse_pos['x'], mouse_pos['y'])
        except Exception as e: # If pynput listener is not active, get_mouse_position might fail
             print(f"Could not get mouse position for reset: {e}")
             # Fallback: use last known raw angle or 0
             self.previous_smoothed_angle = self.current_raw_angle if self.angle_history else 0.0

        self.angle_history.clear()
        for _ in range(self.angle_history.maxlen):
            self.angle_history.append(self.previous_smoothed_angle)

        if self.vjoy_device and self.is_steering: # Only send if steering, otherwise it's centered on stop
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, CENTER_VJOY_AXIS)
        elif self.vjoy_device and not self.is_steering: # If stopped, ensure it reflects centered state
             self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, CENTER_VJOY_AXIS)


        print("Steering view reset.")
        if self.app_callback:
             # Update GUI immediately after reset
            gui_data = {
                "offset": self.current_offset, # May not be 0 if mouse not physically centered
                "raw_angle": self.current_raw_angle,
                "smoothed_angle": self.previous_smoothed_angle,
                "total_accumulated_degrees": self.total_accumulated_degrees,
                "rotation_direction": "None",
                "angular_velocity": self.angular_velocity,
                "angular_acceleration": self.angular_acceleration,
                "vjoy_axis_value": CENTER_VJOY_AXIS
            }
            self.app_callback("update_gui", gui_data)
            self.app_callback("status", "View Recentered")


    def update_sensitivity(self, new_sensitivity):
        """Updates the steering sensitivity."""
        self.sensitivity = float(new_sensitivity)
        # Note: Sensitivity's direct impact on angle accumulation (1:1 mapping) is currently minimal.
        # It could be used to scale delta_angle before accumulation if a non-linear response is desired:
        # e.g., self.total_accumulated_degrees += abs(delta_angle * self.sensitivity_factor)
        # For now, it's primarily a placeholder or for future more complex sensitivity models.
        print(f"Sensitivity updated to: {self.sensitivity}")
        if self.app_callback:
            self.app_callback("status", f"Sensitivity: {self.sensitivity}")

    def get_status(self):
        """Returns a dictionary of the current steering logic status, mainly for GUI initialization."""
        # Added vjoy_status_text for direct use by GUI if needed at init
        vjoy_status_text = "Unknown"
        if self.vjoy_device:
            vjoy_status_text = "Connected"
        else:
            # More detailed status could be stored from _initialize_vjoy if needed
            vjoy_status_text = "Not Found or Error"


        return {
            "is_steering": self.is_steering,
            "vjoy_available": self.vjoy_device is not None,
            "vjoy_status_text": vjoy_status_text, # Provide initial vJoy text
            "screen_center_x": self.screen_center_x,
            "screen_center_y": self.screen_center_y,
            "sensitivity": self.sensitivity,
            "max_degrees": self.max_degrees
            # Other values are sent via update_gui callback
        }

    def close(self):
        """Cleans up resources, particularly stopping the mouse listener and centering vJoy."""
        self.stop_steering() # Ensure listener is stopped and vJoy centered
        print("SteeringLogic closed.")

if __name__ == "__main__":
    # This block allows testing SteeringLogic independently.
    print("Running SteeringLogic CLI test...")

    def dummy_gui_callback_cli(event_type, data):
        """A simple CLI callback for testing SteeringLogic without the full GUI."""
        if event_type == "update_gui":
            print(
                f"Offset: {data['offset']:.2f}, "
                f"Accumulated: {data['total_accumulated_degrees']:.2f}°, "
                f"Dir: {data['rotation_direction']}, "
                f"Vel: {data['angular_velocity']:.2f}°/ev, "
                f"Acc: {data['angular_acceleration']:.2f}°/ev² "
                f"VJoy: {data['vjoy_axis_value']}"
            )
        elif event_type == "status":
            print(f"Logic Status: {data}")
        elif event_type == "vjoy_status":
            print(f"Logic vJoy: {data}")
        elif event_type == "error":
            print(f"Logic Error: {data}")

    logic_cli = SteeringLogic(app_callback=dummy_gui_callback_cli)

    screen_center_x_cli, screen_center_y_cli = 960, 540 # Default
    try:
        # Try to use Tkinter to get actual screen dimensions for a more realistic test
        import tkinter as temp_tk
        temp_root = temp_tk.Tk()
        temp_root.withdraw() # Hide dummy window
        screen_center_x_cli = temp_root.winfo_screenwidth() // 2
        screen_center_y_cli = temp_root.winfo_screenheight() // 2
        temp_root.destroy()
        print(f"Using screen center from Tkinter: {screen_center_x_cli}, {screen_center_y_cli}")
    except Exception as e:
        print(f"Tkinter not available for screen size in CLI test ({e}). Using default center: {screen_center_x_cli}, {screen_center_y_cli}")

    logic_cli.set_screen_center(screen_center_x_cli, screen_center_y_cli)

    initial_status = logic_cli.get_status()
    print(f"Initial vJoy Status for CLI: {initial_status.get('vjoy_status_text', 'N/A')}")


    if initial_status['vjoy_available']:
        print("Starting steering in 3 seconds... Move your mouse in circles around the screen center.")
        print("Press Ctrl+C to stop.")
        time.sleep(3)
        logic_cli.start_steering()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping steering (CLI test)...")
        finally:
            logic_cli.close()
    else:
        print("Could not run CLI test: vJoy device not initialized or error during setup.")
        logic_cli.close() # Ensure cleanup even if not started.

```
