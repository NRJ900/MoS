import tkinter as tk
from tkinter import ttk
try:
    from MOS import MouseSteering
except ImportError:
    class MouseSteering:
        def __init__(self, app):
            self.app = app
            self.mouse_listener = None
            self.sensitivity = 1.0

        def start_steering(self):
            print("Starting mouse steering with sensitivity:", self.sensitivity)

        def stop_steering(self):
            print("Stopping mouse steering")
import ctypes

class MouseSteeringApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MoS V1.0")

        # Center the window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 500
        window_height = 500
        position_top = int(screen_height / 2 - window_height / 2)
        position_left = int(screen_width / 2 - window_width / 2)
        self.root.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')
        self.root.config(bg="#1A1A1A")
        self.root.resizable(False, False)

        # Set up a custom font
        self.font = ("Segoe UI", 12)

        # Initialize Mouse Steering
        self.mouse_steering = MouseSteering(self)

        self.theme = "Dark"

        # Main Frame
        self.main_frame = tk.Frame(self.root, bg="#2C2C2C", bd=10, relief="solid", 
                                   highlightbackground="#444", highlightthickness=1)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.create_widgets()

    def update_opacity(self, value):
        self.root.attributes("-alpha", float(value))

    def switch_theme(self):
        """Toggle between Light and Dark themes."""
        self.theme = "Light" if self.theme == "Dark" else "Dark"
        bg_color = "#F0F0F0" if self.theme == "Light" else "#1A1A1A"
        fg_color = "black" if self.theme == "Light" else "white"

        # Update window background
        self.root.config(bg=bg_color)
        self.main_frame.config(bg=bg_color)

        # Ensure labels exist before updating
        if hasattr(self, 'offset_label'):
            for label in [self.offset_label, self.angle_label]:
                label.config(bg=bg_color, fg=fg_color)

        # Ensure buttons exist before updating
        if hasattr(self, 'start_button'):
            for button in [self.start_button, self.stop_button, self.theme_button]:
                button.config(bg="#0078D4" if self.theme == "Dark" else "#6200EE")

        # Ensure sliders exist before updating
        if hasattr(self, 'sensitivity_slider'):
            self.sensitivity_slider.config(troughcolor="#444" if self.theme == "Dark" else "#DDD")
            self.opacity_slider.config(troughcolor="#444" if self.theme == "Dark" else "#DDD")

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(expand=True, fill="both")

        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main Controls")

        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")

        self.create_main_controls(self.main_tab)
        self.create_settings_controls(self.settings_tab)

    def create_main_controls(self, tab):
        self.start_button = tk.Button(tab, text="Start", command=self.start_steering, 
                                      bg="#0078D4", fg="white", font=self.font, relief="flat")
        self.start_button.pack(pady=20)

        self.stop_button = tk.Button(tab, text="Stop", command=self.stop_steering, 
                                     bg="#D32F2F", fg="white", font=self.font, relief="flat")
        self.stop_button.pack(pady=20)

        self.sensitivity_slider = tk.Scale(tab, from_=0.1, to=10, orient=tk.HORIZONTAL, resolution=0.1,
                                           bg="#2C2C2C", fg="white", font=self.font, label="Sensitivity")
        self.sensitivity_slider.set(1.0)
        self.sensitivity_slider.pack(pady=10)

        self.offset_label = tk.Label(tab, text="Offset: 0.0", bg="#2C2C2C", fg="white", font=self.font)
        self.offset_label.pack(pady=5)

        self.angle_label = tk.Label(tab, text="Angle: 0.0", bg="#2C2C2C", fg="white", font=self.font)
        self.angle_label.pack(pady=5)

    def create_settings_controls(self, tab):
        self.opacity_slider = tk.Scale(tab, from_=0.1, to=1.0, orient=tk.HORIZONTAL, resolution=0.1,
                                       bg="#2C2C2C", fg="white", font=self.font, label="Opacity",
                                       command=self.update_opacity)
        self.opacity_slider.set(1.0)
        self.opacity_slider.pack(pady=20)

        self.theme_button = tk.Button(tab, text="Switch Theme", command=self.switch_theme, 
                                      bg="#0078D4", fg="white", font=self.font, relief="flat")
        self.theme_button.pack(pady=20)

    def start_steering(self):
        if not getattr(self.mouse_steering, "mouse_listener", None) or not self.mouse_steering.mouse_listener.running:
            self.mouse_steering.sensitivity = self.sensitivity_slider.get()
            self.mouse_steering.start_steering()

    def stop_steering(self):
        self.mouse_steering.stop_steering()

    def update_offset_and_angle(self, offset, angle, rotation_direction, rotation_speed, extra_arg=None):
        self.offset_label.config(text=f"Offset: {offset:.2f}")
        self.angle_label.config(text=f"Angle: {angle:.2f}")

if __name__ == "__main__":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()
    app = MouseSteeringApp(root)
    root.mainloop()
