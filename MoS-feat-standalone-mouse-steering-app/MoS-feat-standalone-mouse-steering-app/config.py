"""
Configuration and constants for the Mouse Steering Application.
"""

# vJoy Settings
VJOY_DEVICE_ID = 1
MAX_VJOY_AXIS = 32767  # Max value for a vJoy axis (0x7FFF)
MIN_VJOY_AXIS = 0      # Min value for a vJoy axis
CENTER_VJOY_AXIS = (MAX_VJOY_AXIS + MIN_VJOY_AXIS) // 2 # Center value for a vJoy axis

# Steering Parameters
MAX_STEERING_DEGREES = 1080  # Max steering lock: 3 full rotations (3 * 360°)
DEFAULT_SENSITIVITY = 1.0    # General sensitivity multiplier (can be refined in logic)
MOUSE_CENTER_THRESHOLD_PX = 15 # Pixels: Radius to consider mouse as physically centered
DIRECTION_CHANGE_THRESHOLD_DEG = 1.0  # Degrees: Min angle change to detect rotation direction
ANGLE_SMOOTHING_FACTOR = 5 # Number of past angle samples to average for smoothing

# UI Settings
APP_NAME = "MoS - Advanced Mouse Steering"
DEFAULT_WINDOW_WIDTH = 650
DEFAULT_WINDOW_HEIGHT = 750 # Adjusted for potentially more info with PyQt
UI_REFRESH_RATE_MS = 16 # Roughly 60 FPS for UI updates, if polling or timed updates are used

# Theming (Placeholder - actual QSS might be more complex or in separate files)
THEME_DARK = "dark"
THEME_LIGHT = "light"
DEFAULT_THEME = THEME_DARK

# Logging (Placeholder)
LOG_LEVEL = "INFO"

# Mouse listener settings
# Some mouse listeners might offer a 'blocking' or 'non-blocking' mode.
# pynput runs its listener in a separate thread, so it's non-blocking by nature.

# physics/calculation settings
TIME_DELTA_MODE = "per_event" # "per_event" or "real_time". "per_event" is simpler for now.
                              # "real_time" would require using time.perf_counter() for velocity/accel.

# Add this to config.py after the other imports/constants
try:
    from PyQt6.QtCore import QObject, pyqtSignal
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False