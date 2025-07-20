"""
Main application file for the Mouse Steering (MoS) program.
Contains the PyQt6 GUI.
"""
import sys
import qdarkstyle # For a dark theme, if available and chosen
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QDial, QFrame, QProgressBar, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush
import math # For trigonometric functions in SteeringWheelWidget

import config
from core_logic import SteeringLogic

class SteeringWheelWidget(QWidget):
    """
    A custom PyQt6 widget to visually represent the steering wheel's angle.
    Displays a dial with an indicator line that rotates based on the input angle.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0  # Current steering angle in degrees
        self.max_degrees = config.MAX_STEERING_DEGREES # Max possible steering angle
        self.setMinimumSize(150, 150) # Ensure the widget has a reasonable default size

        # Default colors, can be updated by theme changes
        self.wheel_color = QColor(Qt.GlobalColor.cyan)
        self.indicator_color = QColor(Qt.GlobalColor.red)
        self.tick_color = QColor(Qt.GlobalColor.lightGray)
        self.background_color = QColor(Qt.GlobalColor.transparent) # Or a specific background

    def set_angle(self, angle_degrees: float):
        """
        Sets the current angle of the steering wheel.
        The angle is clamped to the [-max_degrees, +max_degrees] range.
        Triggers a repaint of the widget.
        """
        self.angle = max(-self.max_degrees, min(self.max_degrees, angle_degrees))
        self.update() # Request a repaint

    def set_colors(self, wheel_color, indicator_color, tick_color, background_color=None):
        """Allows external theme changes to update widget colors."""
        self.wheel_color = wheel_color
        self.indicator_color = indicator_color
        self.tick_color = tick_color
        if background_color:
            self.background_color = background_color
        self.update()

    def paintEvent(self, event):
        """Handles the painting of the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing) # Smooth lines

        side = min(self.width(), self.height()) # Use the smaller dimension for a circular widget

        # Set background if specified
        if self.background_color != QColor(Qt.GlobalColor.transparent):
            painter.fillRect(self.rect(), self.background_color)

        # Center the coordinate system and scale for consistent drawing
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0) # Scale to a base 200x200 drawing area

        # --- Draw the steering wheel ---
        # Outer circle (rim of the wheel)
        painter.setPen(QPen(self.wheel_color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(-90, -90, 180, 180) # Diameter 180

        # Center hub of the wheel
        painter.setBrush(QBrush(self.wheel_color))
        painter.setPen(Qt.PenStyle.NoPen) # No outline for the hub
        painter.drawEllipse(-10, -10, 20, 20) # Diameter 20

        # --- Draw reference ticks on the wheel ---
        # This section draws static ticks on the wheel rim.
        # The indicator will rotate relative to these.
        num_visual_ticks = 12 # e.g., like a clock face
        for i in range(num_visual_ticks):
            angle_deg_tick = i * (360.0 / num_visual_ticks)
            painter.save() # Save current painter state
            painter.rotate(angle_deg_tick)

            is_major_tick = (i % 3 == 0) # Make every 3rd tick slightly longer/thicker
            tick_length = 10 if is_major_tick else 6
            tick_width = 3 if is_major_tick else 2

            painter.setPen(QPen(self.tick_color, tick_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(0, -80, 0, -80 - tick_length) # Draw tick line from inner rim outwards
            painter.restore() # Restore painter state

        # --- Draw the rotating indicator line ---
        # The indicator shows the current steering angle.
        # For multi-turn wheels (like 1080 deg), we need to decide how to represent this.
        # Option 1: Show only the current turn's angle (angle % 360).
        # Option 2: Make the indicator very sensitive (as it was).
        # Option 3: Use the progress bar for total accumulated, and this dial for fine-tuning/current turn.
        # Let's go with Option 1 for a clearer single-turn visual on the dial.

        display_angle = self.angle % 360
        if self.angle < 0 and display_angle != 0: # Ensure negative angles also map correctly in 0-360 range for rotation
            display_angle = 360 - abs(display_angle) if abs(display_angle)>1e-3 else 0

        painter.rotate(display_angle) # Rotate based on the current turn's angle

        painter.setPen(QPen(self.indicator_color, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(0, 10, 0, -75) # Line from near center hub outwards


class MainWindow(QMainWindow):
    """
    Main application window for the Mouse Steering program.
    Handles UI layout, user interactions, and communication with SteeringLogic.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.setGeometry(100, 100, config.DEFAULT_WINDOW_WIDTH, config.DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(QSize(550, 700)) # Ensure a minimum sensible size

        # Instantiate the core steering logic
        self.logic = SteeringLogic()

        self.setup_ui()      # Create and arrange all widgets
        self.connect_signals_slots() # Connect GUI events and logic signals
        self.apply_theme(config.DEFAULT_THEME) # Apply the initial visual theme

        # Initialize UI displays with current state from logic
        initial_status = self.logic.get_current_status_summary()
        self.update_vjoy_status_display(initial_status.get("vjoy_status_message", "Initializing..."))
        self.update_gui_data(initial_status)
        self.sensitivity_slider.setValue(int(initial_status.get("sensitivity", config.DEFAULT_SENSITIVITY) * 10))


    def setup_ui(self):
        """Creates and arranges all UI widgets within the main window."""
        main_widget = QWidget() # Central widget to hold the layout
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget) # Main vertical layout

        # --- Controls Section (Start/Stop, Recenter) ---
        controls_layout = QHBoxLayout()
        self.start_stop_button = QPushButton("Start Steering")
        self.start_stop_button.setCheckable(True) # Allows toggled state
        self.start_stop_button.setFixedHeight(40) # Give buttons a bit more height
        self.recenter_button = QPushButton("Recenter View")
        self.recenter_button.setFixedHeight(40)
        controls_layout.addWidget(self.start_stop_button)
        controls_layout.addWidget(self.recenter_button)
        main_layout.addLayout(controls_layout)

        # --- Data Display Section ---
        data_frame = QFrame()
        data_frame.setFrameShape(QFrame.Shape.StyledPanel) # Adds a bit of visual separation
        data_frame.setObjectName("DataFrame")
        data_grid_layout = QVBoxLayout(data_frame) # Changed to QVBoxLayout for simpler label pairs

        self.labels = {} # Dictionary to hold references to value labels for easy updating

        # Helper to add a named data row (label + value)
        def add_data_label(text, key):
            row_layout = QHBoxLayout()
            lbl_name = QLabel(f"{text}:")
            lbl_name.setObjectName("DataLabelName")
            lbl_value = QLabel("N/A") # Placeholder value
            lbl_value.setObjectName("DataLabelValue")
            lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row_layout.addWidget(lbl_name)
            row_layout.addStretch() # Add stretch to push value to the right if needed, or fixed width
            row_layout.addWidget(lbl_value)
            data_grid_layout.addLayout(row_layout)
            self.labels[key] = lbl_value

        add_data_label("Accumulated Angle", "total_accumulated_degrees")
        add_data_label("Direction", "rotation_direction")
        add_data_label("Ang. Velocity", "angular_velocity")
        add_data_label("Ang. Acceleration", "angular_acceleration")
        add_data_label("Mouse Offset", "offset")
        add_data_label("vJoy Axis", "vjoy_axis_value")
        main_layout.addWidget(data_frame)

        # --- Steering Wheel Visualization ---
        self.steering_wheel_widget = SteeringWheelWidget()
        main_layout.addWidget(self.steering_wheel_widget, 0, Qt.AlignmentFlag.AlignCenter) # Add with stretch factor 0

        # Progress bar for total accumulated angle (linear representation)
        self.angle_progress_bar = QProgressBar()
        self.angle_progress_bar.setRange(0, config.MAX_STEERING_DEGREES * 2) # Range from -max_deg to +max_deg
        self.angle_progress_bar.setValue(config.MAX_STEERING_DEGREES) # Initial center position
        self.angle_progress_bar.setTextVisible(False) # Hide percentage text
        self.angle_progress_bar.setFixedHeight(10) # Make it slimmer
        main_layout.addWidget(self.angle_progress_bar)

        main_layout.addStretch(1) # Add stretch before settings to push them down a bit

        # --- Settings Section (Sensitivity) ---
        settings_frame = QFrame()
        settings_frame.setFrameShape(QFrame.Shape.StyledPanel)
        settings_layout = QHBoxLayout(settings_frame)

        sensitivity_label = QLabel("Sensitivity:")
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(1, 100) # Represents 0.1 to 10.0 (value / 10.0)
        self.sensitivity_slider.setToolTip("Adjusts steering input responsiveness")
        settings_layout.addWidget(sensitivity_label)
        settings_layout.addWidget(self.sensitivity_slider)
        main_layout.addWidget(settings_frame)

        # --- Status Bar (via QMainWindow) ---
        self.status_bar = self.statusBar()
        self.vjoy_status_label = QLabel("vJoy: Initializing...")
        self.vjoy_status_label.setObjectName("StatusBarLabel")
        self.app_status_label = QLabel("App: Idle")
        self.app_status_label.setObjectName("StatusBarLabel")
        self.status_bar.addPermanentWidget(self.vjoy_status_label, stretch=1) # Stretch factor for relative sizing
        self.status_bar.addPermanentWidget(self.app_status_label, stretch=2)

        # Theme toggle button (could be in a menu too)
        self.theme_button = QPushButton("Toggle Theme")
        self.theme_button.setFixedWidth(120)
        # Add to a small layout to align right, or directly to main_layout with alignment
        theme_button_layout = QHBoxLayout()
        theme_button_layout.addStretch()
        theme_button_layout.addWidget(self.theme_button)
        main_layout.addLayout(theme_button_layout)


    def connect_signals_slots(self):
        """Connects GUI widget signals to appropriate slots (methods) and logic signals to GUI slots."""
        self.start_stop_button.clicked.connect(self.on_toggle_steering)
        self.recenter_button.clicked.connect(self.logic.recenter_view) # Directly call logic method
        self.sensitivity_slider.valueChanged.connect(self.on_sensitivity_changed)
        self.theme_button.clicked.connect(self.toggle_theme)

        # Connect signals from SteeringLogic to GUI slots
        # These ensure thread-safe updates from the logic (potentially running in pynput's thread) to the GUI.
        if config.HAS_PYQT: # True if core_logic successfully imported PyQt and defined signals
            self.logic.data_updated.connect(self.update_gui_data)
            self.logic.status_changed.connect(self.update_app_status_display)
            self.logic.vjoy_status_changed.connect(self.update_vjoy_status_display)
            self.logic.error_occurred.connect(self.show_error_message)
        else:
            # Fallback if signals aren't used (e.g., PyQt not found in core_logic's context)
            # This relies on the GUI having a method to handle these calls.
            # For thread safety, these callbacks would need to post events to Qt's event loop.
            # The signal/slot mechanism handles this automatically.
            print("Warning: SteeringLogic not using PyQt signals. Falling back to direct callback if defined.")
            self.logic.parent_gui_callback = self.handle_legacy_callback_from_logic

    @pyqtSlot(dict) # Explicitly mark as a PyQt slot
    def update_gui_data(self, data: dict):
        """Updates data display labels and visualizers with new data from SteeringLogic."""
        self.labels["total_accumulated_degrees"].setText(f"{data.get('total_accumulated_degrees', 0.0):.1f}°")
        self.labels["rotation_direction"].setText(str(data.get('rotation_direction', 'None')))
        self.labels["angular_velocity"].setText(f"{data.get('angular_velocity', 0.0):.2f} °/evt")
        self.labels["angular_acceleration"].setText(f"{data.get('angular_acceleration', 0.0):.2f} °/evt²")
        self.labels["offset"].setText(f"{data.get('offset', 0.0):.1f} px")
        self.labels["vjoy_axis_value"].setText(str(data.get('vjoy_axis_value', config.CENTER_VJOY_AXIS)))

        self.steering_wheel_widget.set_angle(data.get('total_accumulated_degrees', 0.0))

        progress_val = data.get('total_accumulated_degrees', 0.0) + config.MAX_STEERING_DEGREES
        self.angle_progress_bar.setValue(int(progress_val))

        # Update Start/Stop button state and text
        is_steering = data.get('is_steering', False)
        if is_steering != self.start_stop_button.isChecked(): # Sync if different
            self.start_stop_button.setChecked(is_steering)
        self.start_stop_button.setText("Stop Steering" if is_steering else "Start Steering")

    @pyqtSlot(str)
    def update_app_status_display(self, status_text: str):
        """Updates the application status label in the status bar."""
        self.app_status_label.setText(f"App: {status_text}")
        # Basic color coding for status (can be enhanced with QSS)
        if "Active" in status_text:
            self.app_status_label.setStyleSheet("color: #A9DC76;") # Greenish
        elif "Error" in status_text:
            self.app_status_label.setStyleSheet("color: #FF6B68;") # Reddish
        else: # Default color from stylesheet or palette
            self.app_status_label.setStyleSheet("")

    @pyqtSlot(str)
    def update_vjoy_status_display(self, status_text: str):
        """Updates the vJoy status label in the status bar and enables/disables start button."""
        self.vjoy_status_label.setText(f"vJoy: {status_text}")
        if "Connected" in status_text:
            self.vjoy_status_label.setStyleSheet("color: #A9DC76;") # Greenish
            self.start_stop_button.setEnabled(True)
        elif "Error" in status_text or "Not Found" in status_text:
            self.vjoy_status_label.setStyleSheet("color: #FF6B68;") # Reddish
            self.start_stop_button.setEnabled(False)
        else: # Initializing or other states
            self.vjoy_status_label.setStyleSheet("")
            self.start_stop_button.setEnabled(False) # Default to disabled if status is unclear

    @pyqtSlot(str)
    def show_error_message(self, error_text: str):
        """Displays a critical error message in a dialog box."""
        QMessageBox.critical(self, "Application Error", error_text)
        self.update_app_status_display(f"Error: {error_text[:30]}...")

    def handle_legacy_callback_from_logic(self, event_type, data):
        """
        Fallback handler if SteeringLogic uses the traditional callback mechanism
        instead of PyQt signals. This method would need to ensure thread-safety
        if called from a non-GUI thread, e.g., by using QTimer.singleShot.
        """
        print(f"Legacy callback received: {event_type} - {data}") # For debugging
        # Example for thread-safe update (if this method is called from another thread):
        # QTimer.singleShot(0, lambda: self._process_legacy_callback(event_type, data))
        # For now, direct call assuming signals are preferred and this is a deep fallback.
        self._process_legacy_callback(event_type, data)

    def _process_legacy_callback(self, event_type, data):
        """Processes data from the legacy callback (called by handle_legacy_callback_from_logic)."""
        if event_type == "data_updated": self.update_gui_data(data)
        elif event_type == "status_changed": self.update_app_status_display(data)
        elif event_type == "vjoy_status_changed": self.update_vjoy_status_display(data)
        elif event_type == "error_occurred": self.show_error_message(data)

    def on_toggle_steering(self, checked: bool):
        """Handles the Start/Stop Steering button click."""
        if checked: # Button is now in "checked" state (meaning user wants to start)
            # It's good practice to get current screen dimensions when starting,
            # though less critical if the window isn't resizable or screen setup doesn't change.
            current_screen = self.screen()
            if current_screen: # Check if screen object is available
                 screen_geometry = current_screen.geometry()
                 self.logic.set_screen_center(screen_geometry.width() // 2, screen_geometry.height() // 2)
            else: # Fallback if screen() is None (should not happen for a visible window)
                print("Warning: Could not get screen geometry. Using potentially stale center point.")

            self.logic.start()
        else: # Button is now in "unchecked" state (meaning user wants to stop)
            self.logic.stop()
        # The button text and actual state will be updated via the data_updated signal.

    def on_sensitivity_changed(self, value: int):
        """Handles changes from the sensitivity slider."""
        actual_sensitivity = value / 10.0 # Scale slider value (1-100) to sensitivity range (0.1-10.0)
        self.logic.set_sensitivity(actual_sensitivity)

    def toggle_theme(self):
        """Switches between dark and light themes."""
        if config.DEFAULT_THEME == config.THEME_DARK: # Assuming current theme is tracked by this default
            self.apply_theme(config.THEME_LIGHT)
            config.DEFAULT_THEME = config.THEME_LIGHT # Update the 'current' theme
        else:
            self.apply_theme(config.THEME_DARK)
            config.DEFAULT_THEME = config.THEME_DARK

    def apply_theme(self, theme_name: str):
        """Applies the specified visual theme to the application."""
        qss = ""
        palette = QPalette() # Start with a default palette

        if theme_name == config.THEME_DARK:
            try:
                # Attempt to use qdarkstyle for a comprehensive dark theme
                qss = qdarkstyle.load_stylesheet_pyqt6()
                self.setStyleSheet(qss)
                # qdarkstyle often sets its own palette, so further palette changes might conflict or be minor.
            except ImportError:
                print("qdarkstyle not found. Applying basic dark palette.")
                # Fallback to a basic QPalette-based dark theme
                palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
                palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
                palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
                palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
                palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
                palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
                palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
                palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
                palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
                palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
                QApplication.instance().setPalette(palette)
                self.setStyleSheet("") # Clear any previous QSS if using palette

            # Update custom widget colors for dark theme
            if self.steering_wheel_widget:
                self.steering_wheel_widget.set_colors(
                    wheel_color=QColor(75, 175, 225), indicator_color=QColor(255, 100, 100),
                    tick_color=QColor(100, 100, 100), background_color=QColor(53,53,53)
                )
        else: # Light theme
            self.setStyleSheet("") # Clear any custom QSS
            QApplication.instance().setPalette(QApplication.style().standardPalette()) # Reset to system default
            # Update custom widget colors for light theme
            if self.steering_wheel_widget:
                self.steering_wheel_widget.set_colors(
                    wheel_color=QColor(Qt.GlobalColor.blue), indicator_color=QColor(Qt.GlobalColor.red),
                    tick_color=QColor(Qt.GlobalColor.darkGray), background_color=QApplication.style().standardPalette().color(QPalette.ColorRole.Window)
                )

        # Force style updates on some widgets if QSS/Palette changes don't propagate automatically enough
        self.update_app_status_display(self.app_status_label.text().replace("App: ", ""))
        self.update_vjoy_status_display(self.vjoy_status_label.text().replace("vJoy: ", ""))


    def closeEvent(self, event):
        """Handles the main window close event (e.g., clicking the 'X' button)."""
        print("Close event triggered. Shutting down logic...")
        self.logic.close() # Ensure core logic is stopped and resources released
        event.accept() # Accept the close event

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # It's good practice to set application name and version if distributing
    app.setApplicationName(config.APP_NAME)
    # app.setApplicationVersion("1.0.0")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


