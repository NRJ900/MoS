"""
Core logic for the Mouse Steering application.
Handles mouse input, steering calculations, and vJoy output.
"""
import math
import time
from collections import deque
import pyvjoy
from pynput import mouse as pynput_mouse
from PyQt6.QtCore import QObject, pyqtSignal
HAS_PYQT = True  # Assume PyQt is available for this example
# Attempt to import Qt core for signals if this class were to become a QObject
# For now, using a standard callback passed from the GUI.
"""try:
    from PyQt6.QtCore import QObject, pyqtSignal
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    # Define dummy QObject and pyqtSignal if PyQt6 is not available
    # This allows the class structure to be defined, but signals won't work.
    # The app will rely on HAS_PYQT to use callbacks if signals are not possible.
    class QObject:
        def __init__(self, parent=None): pass
    class pyqtSignal:
        def __init__(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass"""


import config # Import constants and settings

# If SteeringLogic is to emit Qt signals, it should inherit from QObject.
# For now, a callback approach is simpler to implement without full Qt event loop knowledge here.
# If HAS_PYQT is True, one could define signals here:
# data_updated_signal = pyqtSignal(dict)
# status_updated_signal = pyqtSignal(str)
# vjoy_status_signal = pyqtSignal(str)

# In core_logic.py, change the SteeringLogic class definition to:
class SteeringLogic(QObject if config.HAS_PYQT else object): # Inherit QObject if PyQt is available
    """
    Manages mouse input, steering calculations, and vJoy output.
    Communicates with the GUI via callbacks or Qt signals.
    """
    if HAS_PYQT:
        # Define signals that can be emitted to the GUI
        data_updated = pyqtSignal(dict)
        status_changed = pyqtSignal(str)
        vjoy_status_changed = pyqtSignal(str)
        error_occurred = pyqtSignal(str)

    def __init__(self, parent_gui_callback=None):
        super().__init__() # Call QObject.__init__ if applicable

        self.parent_gui_callback = parent_gui_callback # Traditional callback

        # Steering parameters from config
        self.sensitivity = config.DEFAULT_SENSITIVITY
        self.max_degrees = config.MAX_STEERING_DEGREES
        self.direction_change_threshold = config.DIRECTION_CHANGE_THRESHOLD_DEG
        self.mouse_center_threshold = config.MOUSE_CENTER_THRESHOLD_PX

        # State variables
        self.current_raw_angle = 0.0
        self.previous_smoothed_angle = 0.0
        self.total_accumulated_degrees = 0.0
        self.rotation_direction = "None" # "Clockwise", "Counterclockwise", "None"
        self.current_offset = 0.0
        self.angular_velocity = 0.0 # Degrees per event (or per second if using time_delta)
        self.previous_angular_velocity = 0.0
        self.angular_acceleration = 0.0

        # Screen and mouse position (to be set by GUI)
        self.screen_center_x = None
        self.screen_center_y = None

        # Smoothing
        self.angle_history = deque(maxlen=config.ANGLE_SMOOTHING_FACTOR)
        self.last_event_time = None # For time-based calculations if TIME_DELTA_MODE is 'real_time'

        # vJoy and mouse listener
        self.vjoy_device = None
        self.mouse_listener = None
        self.is_steering = False
        self.vjoy_status_message = "vJoy: Not Initialized"

        self._initialize_vjoy()

    def _emit_or_callback(self, signal_name_or_type, data):
        """Helper to emit Qt signal or use traditional callback."""
        if HAS_PYQT:
            if signal_name_or_type == "data_updated" and hasattr(self, 'data_updated'):
                self.data_updated.emit(data)
            elif signal_name_or_type == "status_changed" and hasattr(self, 'status_changed'):
                self.status_changed.emit(data)
            elif signal_name_or_type == "vjoy_status_changed" and hasattr(self, 'vjoy_status_changed'):
                self.vjoy_status_changed.emit(data)
            elif signal_name_or_type == "error_occurred" and hasattr(self, 'error_occurred'):
                self.error_occurred.emit(data)
            # If a signal emitter was not found but a callback exists, use it.
            elif self.parent_gui_callback:
                 self.parent_gui_callback(signal_name_or_type, data)
        elif self.parent_gui_callback:
            # Fallback to traditional callback if PyQt is not used/available
            self.parent_gui_callback(signal_name_or_type, data)


    def _initialize_vjoy(self):
        try:
            self.vjoy_device = pyvjoy.VJoyDevice(config.VJOY_DEVICE_ID)
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, config.CENTER_VJOY_AXIS)
            self.vjoy_status_message = "Connected"
            print(f"vJoy device {config.VJOY_DEVICE_ID} initialized and centered.")
        except pyvjoy.exceptions.vJoyFailedToAcquireException as e:
            self.vjoy_status_message = f"Error acquiring: {e}"
            print(f"Error acquiring vJoy device {config.VJOY_DEVICE_ID}: {e}")
            self.vjoy_device = None
        except Exception as e:
            self.vjoy_status_message = f"Not Found or General Error: {e}"
            print(f"General vJoy Error for device {config.VJOY_DEVICE_ID}: {e}")
            self.vjoy_device = None
        self._emit_or_callback("vjoy_status_changed", self.vjoy_status_message)


    def set_screen_center(self, center_x, center_y):
        self.screen_center_x = center_x
        self.screen_center_y = center_y
        # Initialize previous_smoothed_angle based on current mouse position relative to the new center
        # This helps prevent a large initial jump in delta_angle when steering starts.
        try:
            # pynput's mouse controller can get current position without an active listener
            controller = pynput_mouse.Controller()
            current_mouse_x, current_mouse_y = controller.position
            self.previous_smoothed_angle = self._calculate_raw_angle(current_mouse_x, current_mouse_y)
        except Exception as e:
            print(f"Warning: Could not get initial mouse position for screen center: {e}. Defaulting angle.")
            self.previous_smoothed_angle = 0.0 # Fallback

        self.angle_history.clear()
        for _ in range(self.angle_history.maxlen or 1): # Ensure maxlen is at least 1
            self.angle_history.append(self.previous_smoothed_angle)

    def _calculate_raw_angle(self, x, y):
        if self.screen_center_x is None or self.screen_center_y is None:
            return 0.0
        return math.degrees(math.atan2(y - self.screen_center_y, x - self.screen_center_x))

    def start(self):
        if self.is_steering:
            self._emit_or_callback("status_changed", "Already Steering")
            return

        if not self.vjoy_device:
            self._emit_or_callback("error_occurred", "vJoy device not available. Cannot start.")
            return

        if self.screen_center_x is None or self.screen_center_y is None:
            self._emit_or_callback("error_occurred", "Screen center not set. GUI should set this first.")
            return

        self.is_steering = True
        # Reset/Initialize relevant state variables for a fresh start
        try:
            controller = pynput_mouse.Controller()
            current_mouse_x, current_mouse_y = controller.position
            self.previous_smoothed_angle = self._calculate_raw_angle(current_mouse_x, current_mouse_y)
        except Exception:
            self.previous_smoothed_angle = 0.0 # Fallback

        self.angle_history.clear()
        for _ in range(self.angle_history.maxlen or 1):
             self.angle_history.append(self.previous_smoothed_angle)

        self.angular_velocity = 0.0
        self.previous_angular_velocity = 0.0
        self.angular_acceleration = 0.0
        self.rotation_direction = "None"
        if config.TIME_DELTA_MODE == "real_time":
            self.last_event_time = time.perf_counter()

        # Start the pynput mouse listener
        # Listener runs in its own thread, so on_move needs to be thread-safe if it modifies shared state
        # that is also accessed by the GUI thread directly (which it does via callbacks/signals).
        # PyQt signals are thread-safe. Direct callbacks to GUI methods that update widgets
        # must be handled carefully (e.g., using QMetaObject.invokeMethod or QTimer.singleShot(0, ...)).
        self.mouse_listener = pynput_mouse.Listener(on_move=self._on_move_handler)
        self.mouse_listener.start()
        self._emit_or_callback("status_changed", "Steering Active")
        print("Steering started.")

    def stop(self):
        if not self.is_steering:
            self._emit_or_callback("status_changed", "Not Steering")
            return

        self.is_steering = False
        if self.mouse_listener:
            self.mouse_listener.stop() # Request listener to stop
            # self.mouse_listener.join() # Wait for listener thread to finish - can cause deadlock if called from listener thread
            self.mouse_listener = None

        if self.vjoy_device:
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, config.CENTER_VJOY_AXIS)

        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0
        self._emit_or_callback("status_changed", "Steering Stopped")
        print("Steering stopped.")
        # Send final state
        self._send_data_update()


    def _on_move_handler(self, x, y):
        if not self.is_steering or self.screen_center_x is None:
            return False # Returning False from on_move can stop the listener

        time_delta = 1.0 # Default if per_event
        if config.TIME_DELTA_MODE == "real_time":
            current_time = time.perf_counter()
            time_delta = current_time - (self.last_event_time if self.last_event_time is not None else current_time)
            self.last_event_time = current_time
            if time_delta == 0: time_delta = 1e-6 # Avoid division by zero, use a tiny non-zero value

        self.current_offset = math.sqrt((x - self.screen_center_x)**2 + (y - self.screen_center_y)**2)
        self.current_raw_angle = self._calculate_raw_angle(x, y)
        self.angle_history.append(self.current_raw_angle)
        current_smoothed_angle = sum(self.angle_history) / len(self.angle_history)

        delta_angle = current_smoothed_angle - self.previous_smoothed_angle
        if delta_angle > 180: delta_angle -= 360
        elif delta_angle < -180: delta_angle += 360

        # Velocity/Acceleration based on time_delta (can be per-event if time_delta=1)
        new_angular_velocity = delta_angle / time_delta
        self.angular_acceleration = (new_angular_velocity - self.angular_velocity) / time_delta
        self.angular_velocity = new_angular_velocity
        # previous_angular_velocity is not needed if we define accel as change from last event's velocity

        if self.current_offset < self.mouse_center_threshold:
            self.rotation_direction = "None"
        elif delta_angle > self.direction_change_threshold:
            self.rotation_direction = "Clockwise"
            self.total_accumulated_degrees += abs(delta_angle) # Use raw delta_angle for accumulation step
        elif delta_angle < -self.direction_change_threshold:
            self.rotation_direction = "Counterclockwise"
            self.total_accumulated_degrees -= abs(delta_angle)
        else:
            self.rotation_direction = "None"

        self.total_accumulated_degrees = max(-self.max_degrees, min(self.max_degrees, self.total_accumulated_degrees))
        self.previous_smoothed_angle = current_smoothed_angle

        if self.vjoy_device:
            # Scale total_accumulated_degrees
            if (2 * self.max_degrees) == 0: normalized_value = 0.5
            else: normalized_value = (self.total_accumulated_degrees + self.max_degrees) / (2 * self.max_degrees)
            axis_value = int(normalized_value * (config.MAX_VJOY_AXIS - config.MIN_VJOY_AXIS) + config.MIN_VJOY_AXIS)
            axis_value = max(config.MIN_VJOY_AXIS, min(config.MAX_VJOY_AXIS, axis_value))
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, axis_value)

        self._send_data_update()
        return True # Keep listener alive

    def _send_data_update(self):
        """Helper to package and send data to GUI."""
        axis_val = config.CENTER_VJOY_AXIS
        if self.vjoy_device:
            # This recalculates, ideally store from _on_move_handler if vJoy was updated there
            if (2 * self.max_degrees) == 0: norm_val = 0.5
            else: norm_val = (self.total_accumulated_degrees + self.max_degrees) / (2 * self.max_degrees)
            axis_val = int(norm_val * (config.MAX_VJOY_AXIS - config.MIN_VJOY_AXIS) + config.MIN_VJOY_AXIS)
            axis_val = max(config.MIN_VJOY_AXIS, min(config.MAX_VJOY_AXIS, axis_val))

        data = {
            "offset": self.current_offset,
            "raw_angle": self.current_raw_angle,
            "smoothed_angle": self.previous_smoothed_angle, # Or current_smoothed_angle from local context
            "total_accumulated_degrees": self.total_accumulated_degrees,
            "rotation_direction": self.rotation_direction,
            "angular_velocity": self.angular_velocity,
            "angular_acceleration": self.angular_acceleration,
            "vjoy_axis_value": axis_val,
            "is_steering": self.is_steering
        }
        self._emit_or_callback("data_updated", data)

    def recenter_view(self):
        self.total_accumulated_degrees = 0.0
        self.angular_velocity = 0.0
        # self.previous_angular_velocity = 0.0 # Keep this to avoid large accel spike if movement continues
        self.angular_acceleration = 0.0

        try: # Re-initialize previous_smoothed_angle based on current mouse pos
            controller = pynput_mouse.Controller()
            current_mouse_x, current_mouse_y = controller.position
            self.previous_smoothed_angle = self._calculate_raw_angle(current_mouse_x, current_mouse_y)
        except Exception: self.previous_smoothed_angle = 0.0

        self.angle_history.clear()
        for _ in range(self.angle_history.maxlen or 1):
            self.angle_history.append(self.previous_smoothed_angle)

        if self.vjoy_device:
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, config.CENTER_VJOY_AXIS)

        self._emit_or_callback("status_changed", "View Recentered")
        self._send_data_update() # Send updated state
        print("Steering view reset.")

    def set_sensitivity(self, new_sensitivity):
        self.sensitivity = float(new_sensitivity)
        # Future: this sensitivity could scale delta_angle before accumulation or affect smoothing.
        # For now, it's a parameter that the GUI can control.
        self._emit_or_callback("status_changed", f"Sensitivity: {self.sensitivity:.2f}")
        print(f"Sensitivity updated to: {self.sensitivity:.2f}")

    def get_current_status_summary(self):
        """Returns a snapshot of key status elements, useful for GUI init or polling."""
        return {
            "is_steering": self.is_steering,
            "vjoy_available": self.vjoy_device is not None,
            "vjoy_status_message": self.vjoy_status_message,
            "sensitivity": self.sensitivity,
            "max_degrees": self.max_degrees,
            # Current values that are frequently updated can also be here if needed for init
            "total_accumulated_degrees": self.total_accumulated_degrees,
            "vjoy_axis_value": self._get_current_vjoy_axis_value() # Helper for this
        }

    def _get_current_vjoy_axis_value(self):
        if not self.vjoy_device: return config.CENTER_VJOY_AXIS
        if (2 * self.max_degrees) == 0: normalized_value = 0.5
        else: normalized_value = (self.total_accumulated_degrees + self.max_degrees) / (2 * self.max_degrees)
        axis_value = int(normalized_value * (config.MAX_VJOY_AXIS - config.MIN_VJOY_AXIS) + config.MIN_VJOY_AXIS)
        return max(config.MIN_VJOY_AXIS, min(config.MAX_VJOY_AXIS, axis_value))


    def close(self):
        print("Closing SteeringLogic...")
        self.stop() # Ensure listener is stopped and vJoy centered
        # Any other cleanup (e.g. if using QObject and it needs manual deletion)
        print("SteeringLogic closed.")

# Example CLI test for core_logic.py
if __name__ == "__main__":
    print("Running core_logic.py CLI test...")

    # Dummy callback for CLI testing
    def cli_test_callback(event_type, data):
        if event_type == "data_updated":
            print(
                f"Data: Accum: {data['total_accumulated_degrees']:.1f}°, "
                f"Dir: {data['rotation_direction']}, "
                f"Vel: {data['angular_velocity']:.2f}, Acc: {data['angular_acceleration']:.2f}, "
                f"VJoy: {data['vjoy_axis_value']}"
            )
        elif event_type == "status_changed":
            print(f"Status: {data}")
        elif event_type == "vjoy_status_changed":
            print(f"vJoy Status: {data}")
        elif event_type == "error_occurred":
            print(f"Error: {data}")

    logic = SteeringLogic(parent_gui_callback=cli_test_callback)

    # For CLI test, attempt to set a screen center.
    # In a real app, GUI provides this from actual screen dimensions.
    center_x, center_y = 960, 540 # Common 1920x1080 screen center
    try:
        # Attempt to use Tkinter just to get screen dimensions for a more realistic center
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        actual_center_x = root.winfo_screenwidth() // 2
        actual_center_y = root.winfo_screenheight() // 2
        if actual_center_x > 0 and actual_center_y > 0: # Check if valid dimensions were obtained
            center_x, center_y = actual_center_x, actual_center_y
        root.destroy()
        print(f"Using screen center (from Tkinter if available): {center_x}, {center_y}")
    except Exception as e:
        print(f"Could not use Tkinter for screen dimensions ({e}). Using default center: {center_x}, {center_y}")

    logic.set_screen_center(center_x, center_y)

    status_summary = logic.get_current_status_summary()
    if not status_summary["vjoy_available"]:
        print(f"vJoy not available ({status_summary['vjoy_status_message']}). Exiting CLI test.")
    else:
        print(f"vJoy available. Sensitivity: {status_summary['sensitivity']}. Max Degrees: {status_summary['max_degrees']}.")
        print("Starting steering in 3 seconds. Move mouse in circles. Press Ctrl+C to stop.")
        time.sleep(3)
        logic.start()
        try:
            while logic.is_steering: # Loop while steering is active
                time.sleep(0.5) # Keep main thread alive
        except KeyboardInterrupt:
            print("\nCtrl+C detected. Stopping steering...")
        finally:
            logic.close()

