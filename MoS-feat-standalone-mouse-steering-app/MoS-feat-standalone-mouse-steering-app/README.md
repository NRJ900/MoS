# 🖱️ Mouse Steering System 🎮

A **Mouse Steering System** that simulates a **steering wheel** using **mouse movements**, integrating with **vJoy** for virtual joystick input. The system accurately tracks **clockwise and counterclockwise rotations**, ensuring smooth steering for racing or driving simulation games.

## 🚀 Features
- ✅ **Realistic Steering Simulation**: Maps mouse movement to steering angles with a **maximum of 3 full turns (1080°) in each direction**.
- ✅ **Accurate Rotation Tracking**: Differentiates **clockwise** and **counterclockwise** rotations.
- ✅ **Windows 11 Inspired GUI**: A modern and stylish Tkinter interface.
- ✅ **Configurable Sensitivity**: Adjust steering response with a **sensitivity slider**.
- ✅ **Centering Mechanism**: Automatically resets steering when the mouse returns to the center.
- ✅ **vJoy Integration**: Sends real-time input to a virtual joystick for compatibility with racing games.
- ✅ **Live Angle & Offset Display**: Shows current steering angle, offset, and rotation direction.

## 📷 Screenshots
| GUI | Steering in Action |
|:-:|:-:|
| ![GUI Screenshot](https://via.placeholder.com/400) | ![Steering Example](https://via.placeholder.com/400) |

## 🛠 Installation
### Prerequisites:
1. **Python 3.10+**  
2. **vJoy Installed & Configured** ([Download vJoy](https://sourceforge.net/projects/vjoystick/))  
3. **Required Python Libraries**:  
   ```sh
   pip install pyvjoy pynput
   ```

### Steps:
1. **Clone the repository**  
   ```sh
   git clone https://github.com/NRJ900/MoS.git
   cd MoS
   ```
2. **Run the GUI**
   ```sh
   [file_yet_to_be_published.py]
   ```

## 🎮 Usage
1. **Open the GUI** and press the **Start** button.  
2. **Move your mouse in circular motions** to simulate steering.  
3. **Rotation Limits**: Up to **1080° left or right** (3 full turns).  
4. **Press Stop** to end steering.

## ⚙️ Configuration
You can customize various aspects of the steering system:
- **Sensitivity**: Adjustable through the GUI to fine-tune the responsiveness.
- **Rotation Limit**: Restricted to **1080° (3 full rotations) in either direction**.
- **Cursor Centering**: The cursor resets to the screen center when the steering starts.

## 📝 License
This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

## 🙌 Contributing
Contributions are welcome! If you’d like to improve the project, feel free to:
- Fork the repository.
- Create a feature branch.
- Submit a pull request.

For any issues, open a **GitHub Issue**.

## 💡 Acknowledgments
- [vJoy](https://sourceforge.net/projects/vjoystick/) – Virtual Joystick Driver  
- [pynput](https://pypi.org/project/pynput/) – Mouse Event Handling  

---

🔗 **Follow me on GitHub**:  [NRJ900](https://github.com/NRJ900)
