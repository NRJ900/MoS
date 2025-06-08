import pyvjoy
import tkinter as tk
from tkinter import ttk
from tkinter import font
from pynput import mouse as pynput_mouse
import ctypes
import time

class MouseSteeringApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MoS V1.0")
        self.root.geometry("500x500")
        self.root.configure(bg="#2C3E50")  # Set initial background color

        # vJoy device
        self.vjoy_device = None
        try:
            self.vjoy_device = pyvjoy.VJoyDevice(1)
        except pyvjoy.exceptions.vJoyFailedToAcquireException as e:
            print(f"Error acquiring vJoy device: {e}")

        self.sensitivity = 1.0
        self.is_steering = False

        self.update_center_position()  # Initialize center position
        self.create_widgets()
        self.center_mouse()  # Center mouse cursor at start

        self.mouse_listener = None  # Initially no listener

        # Bind window close event to cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # Create a notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        # Main control tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main Controls")

        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")

        # Add widgets to main tab
        self.create_main_controls(self.main_tab)

        # Add settings to settings tab
        self.create_settings_controls(self.settings_tab)

    def create_main_controls(self, tab):
        button_font = font.Font(family="Helvetica", size=12, weight="bold")
        label_font = font.Font(family="Helvetica", size=10, weight="bold")

        # Start Button
        self.start_button = tk.Button(tab, text="Start", font=button_font, command=self.start_steering, 
                                      bg="#27AE60", fg="white", relief="raised", bd=3, width=10)
        self.start_button.pack(pady=10)

        # Stop Button
        self.stop_button = tk.Button(tab, text="Stop", font=button_font, command=self.stop_steering, 
                                     bg="#E74C3C", fg="white", relief="raised", bd=3, width=10)
        self.stop_button.pack(pady=10)

        # Sensitivity Slider
        self.sensitivity_slider = tk.Scale(tab, from_=0.1, to=10, orient=tk.HORIZONTAL, resolution=0.1, 
                                           command=self.update_sensitivity, bg="#34495E", fg="white", 
                                           troughcolor="#95A5A6", font=label_font, length=300)
        self.sensitivity_slider.set(self.sensitivity)
        self.sensitivity_slider.pack(pady=15)

        # Sensitivity Label
        self.sensitivity_label = tk.Label(tab, text=f"Sensitivity: {self.sensitivity}", font=label_font, 
                                          bg="#2C3E50", fg="white")
        self.sensitivity_label.pack(pady=5)

        # Indicator Frame
        self.indicator_frame = tk.Frame(tab, bg="#2C3E50")
        self.indicator_frame.pack(pady=20)

        # Left, Center, and Right Indicators
        self.left_indicator = tk.Label(self.indicator_frame, text="Left", bg="#ECF0F1", fg="#E74C3C", font=label_font, 
                                       width=10, relief="ridge", bd=2)
        self.left_indicator.grid(row=0, column=0, padx=10)

        self.center_indicator = tk.Label(self.indicator_frame, text="Center", bg="#ECF0F1", fg="#27AE60", font=label_font, 
                                         width=10, relief="ridge", bd=2)
        self.center_indicator.grid(row=0, column=1, padx=10)

        self.right_indicator = tk.Label(self.indicator_frame, text="Right", bg="#ECF0F1", fg="#3498DB", font=label_font, 
                                        width=10, relief="ridge", bd=2)
        self.right_indicator.grid(row=0, column=2, padx=10)

        # Angle Label
        self.angle_label = tk.Label(tab, text="Turn Angle: 0%", font=label_font, bg="#2C3E50", fg="white")
        self.angle_label.pack(pady=5)

        # Offset Label
        self.offset_label = tk.Label(tab, text="Offset: 0%", font=label_font, bg="#2C3E50", fg="white")
        self.offset_label.pack(pady=5)

    def create_settings_controls(self, tab):
        label_font = font.Font(family="Helvetica", size=10, weight="bold")

        # Opacity Slider
        self.opacity_slider = tk.Scale(tab, from_=0.1, to=1.0, orient=tk.HORIZONTAL, resolution=0.05, 
                                       command=self.update_opacity, length=300)
        self.opacity_slider.set(1.0)  # Default opacity is 1 (fully opaque)
        self.opacity_slider.pack(pady=15)

        # Opacity Label
        self.opacity_label = tk.Label(tab, text="Window Opacity", font=label_font)
        self.opacity_label.pack(pady=5)

        # Theme Dropdown
        self.theme_label = tk.Label(tab, text="Select Theme", font=label_font)
        self.theme_label.pack(pady=5)

        self.theme_var = tk.StringVar(tab)
        self.theme_var.set("Default")  # Default theme
        self.theme_menu = ttk.OptionMenu(tab, self.theme_var, "Default", "Dark", "Light", command=self.change_theme)
        self.theme_menu.pack(pady=10)

    def update_center_position(self):
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2

    def start_steering(self):
        if not self.is_steering and self.vjoy_device:
            self.is_steering = True
            self.center_mouse()
            time.sleep(0.1)
            self.mouse_listener = pynput_mouse.Listener(on_move=self.on_move)
            self.mouse_listener.start()

    def stop_steering(self):
        if self.is_steering:
            self.is_steering = False
            if self.mouse_listener is not None:
                self.mouse_listener.stop()

    def on_move(self, x, y):
        if self.is_steering and self.vjoy_device:
            delta_x = x - self.center_x
            turn_angle = (delta_x / (self.screen_width // 2)) * self.sensitivity
            turn_angle = max(min(turn_angle, 1), -1)  # Clamping to range [-1, 1]
            axis_value = int((turn_angle + 1) * 16383)  # Map [-1, 1] to [0, 32767]
            self.vjoy_device.set_axis(pyvjoy.HID_USAGE_X, axis_value)

            offset_percentage = (delta_x / (self.screen_width // 2)) * 100
            offset_percentage = max(min(offset_percentage, 100), -100)
            direction = 'Left' if offset_percentage < 0 else 'Right'
            
            self.update_indicator(turn_angle)
            self.angle_label.config(text=f"Turn Angle: {round(turn_angle * 100, 2)}%")
            self.offset_label.config(text=f"Offset: {round(offset_percentage, 2)}% {direction}")

    def update_indicator(self, angle):
        if angle < -0.1:
            self.left_indicator.config(bg="#E74C3C", fg="white")
            self.center_indicator.config(bg="#ECF0F1", fg="#27AE60")
            self.right_indicator.config(bg="#ECF0F1", fg="#3498DB")
        elif angle > 0.1:
            self.left_indicator.config(bg="#ECF0F1", fg="#E74C3C")
            self.center_indicator.config(bg="#ECF0F1", fg="#27AE60")
            self.right_indicator.config(bg="#3498DB", fg="white")
        else:
            self.left_indicator.config(bg="#ECF0F1", fg="#E74C3C")
            self.center_indicator.config(bg="#27AE60", fg="white")
            self.right_indicator.config(bg="#ECF0F1", fg="#3498DB")

    def update_sensitivity(self, value):
        self.sensitivity = float(value)
        self.sensitivity_label.config(text=f"Sensitivity: {self.sensitivity}")

    def update_opacity(self, value):
        opacity = float(value)
        self.root.attributes('-alpha', opacity)

    def change_theme(self, selected_theme):
        if selected_theme == "Dark":
            self.root.configure(bg="#2C3E50")
            self.sensitivity_slider.configure(bg="#34495E", fg="white", troughcolor="#95A5A6")
            self.sensitivity_label.configure(bg="#2C3E50", fg="white")
            self.angle_label.configure(bg="#2C3E50", fg="white")
            self.offset_label.configure(bg="#2C3E50", fg="white")
            self.left_indicator.configure(bg="#ECF0F1", fg="#E74C3C")
            self.center_indicator.configure(bg="#ECF0F1", fg="#27AE60")
            self.right_indicator.configure(bg="#ECF0F1", fg="#3498DB")
        elif selected_theme == "Light":
            self.root.configure(bg="white")
            self.sensitivity_slider.configure(bg="lightgrey", fg="black", troughcolor="darkgrey")
            self.sensitivity_label.configure(bg="white", fg="black")
            self.angle_label.configure(bg="white", fg="black")
            self.offset_label.configure(bg="white", fg="black")
            self.left_indicator.configure(bg="white", fg="#E74C3C")
            self.center_indicator.configure(bg="white", fg="#27AE60")
            self.right_indicator.configure(bg="white", fg="#3498DB")
        else:
            # Default Theme
            self.root.configure(bg="#2C3E50")
            self.sensitivity_slider.configure(bg="#34495E", fg="white", troughcolor="#95A5A6")
            self.sensitivity_label.configure(bg="#2C3E50", fg="white")
            self.angle_label.configure(bg="#2C3E50", fg="white")
            self.offset_label.configure(bg="#2C3E50", fg="white")
            self.left_indicator.configure(bg="#ECF0F1", fg="#E74C3C")
            self.center_indicator.configure(bg="#ECF0F1", fg="#27AE60")
            self.right_indicator.configure(bg="#ECF0F1", fg="#3498DB")

    def center_mouse(self):
        # Center the mouse cursor on the screen
        ctypes.windll.user32.SetCursorPos(self.center_x, self.center_y)

    def on_close(self):
        self.stop_steering()
        self.root.destroy()

# Main application execution
root = tk.Tk()
app = MouseSteeringApp(root)
root.mainloop()
