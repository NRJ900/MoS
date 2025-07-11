# mouse_steering_app.py
# This file now contains only the GUI (SteeringApp) and related imports/logic.
# The core steering calculations (SteeringLogic) are in steering_logic.py.
# Constants are in constants.py.

import tkinter as tk
from tkinter import ttk, font, messagebox
import ctypes # For DPI awareness

from steering_logic import SteeringLogic
from constants import CENTER_VJOY_AXIS # For initial GUI display if needed

class SteeringApp:
    """
    The main Tkinter application class for the Mouse Steering Control.
    It provides the user interface and interacts with the SteeringLogic class.
    """
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("MoS - Mouse Steering Control")

        # Attempt DPI Awareness for sharper UI elements on Windows
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1) # Windows 8.1+
        except AttributeError:
            try: # Fallback for older Windows versions (Vista, 7)
                ctypes.windll.user32.SetProcessDPIAware()
            except AttributeError:
                print("Warning: Could not set DPI awareness. UI might appear blurry on high DPI screens.")

        # --- Window Setup ---
        window_width = 600
        window_height = 700 # Increased height for more info and better layout
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # Calculate position for centering the window
        position_top = int(screen_height / 2 - window_height / 2)
        position_left = int(screen_width / 2 - window_width / 2)
        self.root.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')
        self.root.minsize(550, 650) # Minimum size to prevent layout issues

        # --- Initialize Steering Logic ---
        # Pass the GUI's callback method to the SteeringLogic instance
        self.steering_logic = SteeringLogic(app_callback=self.handle_logic_callback)
        # Provide the screen center to the logic (essential for angle calculations)
        self.steering_logic.set_screen_center(screen_width // 2, screen_height // 2)

        # --- Styling and Theming ---
        self.current_theme = "Dark" # Initial theme ("Dark" or "Light")
        self.fonts = {
            "default": font.Font(family="Segoe UI", size=10),
            "label": font.Font(family="Segoe UI", size=11, weight="bold"), # For descriptive labels
            "status": font.Font(family="Segoe UI", size=9),                # For status messages
            "data": font.Font(family="Consolas", size=11)                  # Monospaced for numerical data
        }
        self.colors = {} # Theme-specific colors, populated by apply_theme()

        # --- Main UI Structure ---
        self.create_widgets() # Create all GUI elements
        self.apply_theme()    # Apply the initial theme to all widgets

        # Update GUI with initial status from SteeringLogic
        initial_logic_status = self.steering_logic.get_status()
        self.update_gui_elements(initial_logic_status)

        # Explicitly call vjoy status update from logic to GUI
        # The vjoy_status_text key was added to get_status() in steering_logic.py
        vjoy_text = initial_logic_status.get('vjoy_status_text', 'Initializing...')
        self.vjoy_status_label.config(text=f"vJoy: {vjoy_text}")
        if not initial_logic_status.get('vjoy_available', False):
             self.vjoy_status_label.config(foreground=self.colors.get("error", "red"))
             self.start_button.config(state=tk.DISABLED)
        else:
            self.vjoy_status_label.config(foreground=self.colors.get("success", "green"))


        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def apply_theme(self):
        """Applies the selected color theme (Dark/Light) to the GUI elements."""
        if self.current_theme == "Dark":
            self.colors = {
                "bg": "#2B2B2B", "fg": "#BBBBBB", "widget_bg": "#3C3F41", # General background, foreground, widget backgrounds
                "button_bg": "#4A4D4F", "button_fg": "#BBBBBB",           # Button colors
                "accent": "#007ACC", "error": "#FF6B68", "success": "#A9DC76", # Accent (for data), error, success colors
                "slider_trough": "#555555", "label_fg": "#E0E0E0"         # Slider trough color, specific label foreground
            }
        else: # Light Theme
            self.colors = {
                "bg": "#F0F0F0", "fg": "#333333", "widget_bg": "#FFFFFF",
                "button_bg": "#E0E0E0", "button_fg": "#333333",
                "accent": "#005FAF", "error": "#D32F2F", "success": "#388E3C", # Slightly adjusted accent for light theme
                "slider_trough": "#CCCCCC", "label_fg": "#222222"
            }

        self.root.configure(bg=self.colors["bg"]) # Set root window background

        # Configure ttk styles for consistent theming
        s = ttk.Style()
        s.theme_use('clam') # Using 'clam' or 'alt', 'default' as base for better customisation than 'vista' or 'xpnative'

        s.configure("TFrame", background=self.colors["bg"])
        s.configure("Main.TFrame", background=self.colors["bg"]) # Specific style for main content frames

        s.configure("TButton", font=self.fonts["default"], padding=5,
                    background=self.colors["button_bg"], foreground=self.colors["button_fg"])
        s.map("TButton",
              background=[('active', self.colors["accent"]), ('disabled', self.colors["widget_bg"])],
              foreground=[('disabled', self.colors["fg"])])

        s.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=self.fonts["default"])
        s.configure("Status.TLabel", font=self.fonts["status"], background=self.colors["bg"], foreground=self.colors["fg"])
        s.configure("Data.TLabel", font=self.fonts["data"], background=self.colors["bg"], foreground=self.colors["accent"])
        s.configure("Header.TLabel", font=self.fonts["label"], background=self.colors["bg"], foreground=self.colors["label_fg"])

        s.configure("TScale", troughcolor=self.colors["slider_trough"], background=self.colors["widget_bg"]) # Basic scale theming
        s.map("TScale", background=[('active', self.colors["widget_bg"])])


        s.configure("Horizontal.TProgressbar", troughcolor=self.colors["slider_trough"], background=self.colors["accent"], borderwidth=0)

        # If widgets already exist, try to update their individual styles (important after theme toggle)
        if hasattr(self, 'main_frame'):
            self.main_frame.configure(style="Main.TFrame")
            frames_to_update = [
                getattr(self, name, None) for name in
                ['control_frame', 'data_frame', 'settings_frame', 'status_theme_frame']
            ]
            for frame in frames_to_update:
                if frame:
                    frame.configure(style="Main.TFrame")
                    for widget in frame.winfo_children():
                        self.configure_widget_theme(widget)

            self.update_data_labels_theme()
            self.configure_widget_theme(self.angle_progress, "Horizontal.TProgressbar")
            self.configure_widget_theme(self.sensitivity_slider, "TScale")
            self.configure_widget_theme(self.opacity_slider, "TScale")
            self.configure_widget_theme(self.start_button, "TButton")
            self.configure_widget_theme(self.recenter_button, "TButton")
            self.configure_widget_theme(self.theme_button, "TButton")
            self.configure_widget_theme(self.vjoy_status_label, "Status.TLabel")
            self.configure_widget_theme(self.app_status_label, "Status.TLabel")


    def configure_widget_theme(self, widget, style_name=None):
        """Helper to apply ttk style to a widget if it exists and is a ttk widget."""
        if not widget: return
        try:
            if style_name:
                widget.configure(style=style_name)
            else:
                if isinstance(widget, ttk.Button): widget.configure(style="TButton")
                elif isinstance(widget, ttk.Label): widget.configure(style="TLabel")
                elif isinstance(widget, ttk.Frame): widget.configure(style="TFrame")
                elif isinstance(widget, ttk.Scale): widget.configure(style="TScale")
                elif isinstance(widget, ttk.Progressbar): widget.configure(style="Horizontal.TProgressbar")

        except tk.TclError:
            pass

    def create_widgets(self):
        """Creates and lays out all GUI widgets."""
        self.main_frame = ttk.Frame(self.root, style="Main.TFrame")
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.control_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.control_frame.pack(pady=(5,10), fill="x")

        self.start_button = ttk.Button(self.control_frame, text="Start Steering", command=self.toggle_steering, width=15)
        self.start_button.pack(side="left", padx=5, expand=True, fill="x")

        self.recenter_button = ttk.Button(self.control_frame, text="Recenter View", command=self.steering_logic.reset_steering_view, width=15)
        self.recenter_button.pack(side="left", padx=5, expand=True, fill="x")

        self.data_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.data_frame.pack(pady=5, fill="both", expand=True)
        self.data_frame.columnconfigure(1, weight=1)

        row_idx = 0
        self.data_labels = {}

        def add_data_row(text, key):
            nonlocal row_idx
            lbl_text = ttk.Label(self.data_frame, text=text, style="Header.TLabel")
            lbl_text.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)

            val_text = "--"
            lbl_value = ttk.Label(self.data_frame, text=val_text, style="Data.TLabel", anchor="e")
            lbl_value.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
            self.data_labels[key] = lbl_value
            row_idx += 1
            return lbl_text, lbl_value

        add_data_row("Accumulated Angle:", "total_accumulated_degrees")
        add_data_row("Rotation Direction:", "rotation_direction")
        add_data_row("Angular Velocity:", "angular_velocity")
        add_data_row("Angular Acceleration:", "angular_acceleration")
        add_data_row("Mouse Offset (from center):", "offset")
        add_data_row("Smoothed Mouse Angle:", "smoothed_angle")
        add_data_row("vJoy Axis Output:", "vjoy_axis_value")

        lbl_progress = ttk.Label(self.data_frame, text="Steering Wheel Position:", style="Header.TLabel")
        lbl_progress.grid(row=row_idx, column=0, sticky="w", padx=5, pady=(10,3))
        self.angle_progress = ttk.Progressbar(self.data_frame, orient="horizontal", length=300, mode="determinate",
                                              maximum=self.steering_logic.max_degrees * 2,
                                              value=self.steering_logic.max_degrees)
        self.angle_progress.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=(10,3))
        row_idx +=1

        self.settings_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.settings_frame.pack(pady=5, fill="x")
        self.settings_frame.columnconfigure(1, weight=1)

        lbl_sensitivity = ttk.Label(self.settings_frame, text="Sensitivity:", style="Header.TLabel")
        lbl_sensitivity.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.sensitivity_slider = ttk.Scale(self.settings_frame, from_=0.1, to=5.0, orient=tk.HORIZONTAL,
                                           value=self.steering_logic.sensitivity,
                                           command=lambda s_val: self.steering_logic.update_sensitivity(float(s_val)))
        self.sensitivity_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        lbl_opacity = ttk.Label(self.settings_frame, text="Window Opacity:", style="Header.TLabel")
        lbl_opacity.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.opacity_slider = ttk.Scale(self.settings_frame, from_=0.2, to=1.0, orient=tk.HORIZONTAL,
                                       value=1.0, command=self.update_opacity)
        self.opacity_slider.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.status_theme_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.status_theme_frame.pack(side="bottom", fill="x", pady=(10,0), anchor="s")

        self.vjoy_status_label = ttk.Label(self.status_theme_frame, text="vJoy: Initializing...", style="Status.TLabel", anchor="w")
        self.vjoy_status_label.pack(side="left", padx=5)

        self.app_status_label = ttk.Label(self.status_theme_frame, text="App: Idle", style="Status.TLabel", anchor="w")
        self.app_status_label.pack(side="left", padx=5, expand=True, fill="x")

        self.theme_button = ttk.Button(self.status_theme_frame, text="Toggle Theme", command=self.toggle_theme, width=15)
        self.theme_button.pack(side="right", padx=5)

    def update_data_labels_theme(self):
        """Specifically updates theme colors for data labels after a theme change."""
        if not hasattr(self, 'data_labels'):
            return
        for key, label_widget in self.data_labels.items():
            try:
                label_widget.configure(style="Data.TLabel")
                parent_frame = label_widget.master
                row_info = label_widget.grid_info()["row"]
                descriptor_label = parent_frame.grid_slaves(row=row_info, column=0)[0]
                descriptor_label.configure(style="Header.TLabel")
            except (tk.TclError, IndexError, AttributeError):
                 pass

        if hasattr(self, 'angle_progress'):
            parent_frame = self.angle_progress.master
            row_info = self.angle_progress.grid_info()["row"]
            try:
                descriptor_label = parent_frame.grid_slaves(row=row_info, column=0)[0]
                descriptor_label.configure(style="Header.TLabel")
            except (tk.TclError, IndexError, AttributeError):
                pass


    def toggle_theme(self):
        """Switches between Dark and Light themes and applies changes."""
        self.current_theme = "Light" if self.current_theme == "Dark" else "Dark"
        self.apply_theme()

    def toggle_steering(self):
        """Starts or stops the steering logic based on its current state."""
        if self.steering_logic.is_steering:
            self.steering_logic.stop_steering()
        else:
            if not self.steering_logic.vjoy_device:
                 messagebox.showerror("vJoy Error", "vJoy device not available. Cannot start steering.")
                 return
            self.steering_logic.start_steering()

    def update_opacity(self, value_str):
        """Updates the window opacity based on the slider value."""
        try:
            opacity_value = float(value_str)
            self.root.attributes("-alpha", opacity_value)
        except ValueError:
            pass

    def update_gui_elements(self, data):
        """
        Updates all relevant GUI labels and progress bar with data received from SteeringLogic.
        'data' is a dictionary typically received from the 'update_gui' callback or get_status().
        """
        if not hasattr(self, 'data_labels'): return

        self.data_labels["total_accumulated_degrees"].config(text=f"{data.get('total_accumulated_degrees', 0.0):.2f}°")
        self.data_labels["rotation_direction"].config(text=str(data.get('rotation_direction', 'None')))
        self.data_labels["angular_velocity"].config(text=f"{data.get('angular_velocity', 0.0):.2f}°/event")
        self.data_labels["angular_acceleration"].config(text=f"{data.get('angular_acceleration', 0.0):.2f}°/event²")
        self.data_labels["offset"].config(text=f"{data.get('offset', 0.0):.2f} px")
        self.data_labels["smoothed_angle"].config(text=f"{data.get('smoothed_angle', 0.0):.2f}°")
        # Use CENTER_VJOY_AXIS for default if key is missing (e.g. from initial get_status)
        self.data_labels["vjoy_axis_value"].config(text=str(data.get('vjoy_axis_value', CENTER_VJOY_AXIS)))

        progress_val = data.get('total_accumulated_degrees', 0.0) + self.steering_logic.max_degrees
        self.angle_progress['value'] = progress_val

        current_steering_status = data.get('is_steering', self.steering_logic.is_steering) # Prefer data if available
        if current_steering_status and self.start_button.cget('text') != "Stop Steering":
            self.start_button.configure(text="Stop Steering")
        elif not current_steering_status and self.start_button.cget('text') != "Start Steering":
            self.start_button.configure(text="Start Steering")

    def handle_logic_callback(self, event_type, data):
        """
        Handles callbacks from the SteeringLogic instance.
        Updates GUI elements based on the event type and data received.
        """
        if event_type == "update_gui":
            self.update_gui_elements(data)
        elif event_type == "status":
            self.app_status_label.config(text=f"App: {data}")
            if data == "Steering Active":
                self.app_status_label.config(foreground=self.colors.get("success", "green"))
            elif data == "Steering Stopped" or data == "View Recentered":
                 self.app_status_label.config(foreground=self.colors.get("fg", "black"))
            else:
                self.app_status_label.config(foreground=self.colors.get("accent", "blue"))

        elif event_type == "vjoy_status":
            self.vjoy_status_label.config(text=f"vJoy: {data}")
            if "Error" in data or "Not Found" in data:
                self.vjoy_status_label.config(foreground=self.colors.get("error", "red"))
                self.start_button.config(state=tk.DISABLED)
            elif "Connected" in data :
                self.vjoy_status_label.config(foreground=self.colors.get("success", "green"))
                self.start_button.config(state=tk.NORMAL)
        elif event_type == "error":
            messagebox.showerror("Steering Logic Error", str(data))
            self.app_status_label.config(text=f"App Error (see popup)", foreground=self.colors.get("error", "red"))

    def on_close(self):
        """Handles the window close event for graceful shutdown."""
        print("Closing application via window 'X' button...")
        if self.steering_logic:
            self.steering_logic.close()
        self.root.destroy()

if __name__ == "__main__":
    run_gui_app = True

    if run_gui_app:
        main_root = tk.Tk()
        app_instance = SteeringApp(main_root)
        main_root.mainloop()
    else:
        print("Skipping GUI, running SteeringLogic CLI test (ensure `run_gui_app` is False)...")
        print("To run CLI test for SteeringLogic, ensure it has its own executable __main__ or modify this section.")

```
