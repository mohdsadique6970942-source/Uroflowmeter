# 💧 Uroflowmeter (Volume & Flow Rate Measurement System)

This project is a real-time **uroflowmeter** designed to measure **liquid volume (ml)** and **volumetric flow rate (ml/s)** using a load cell and HX711 amplifier with ESP32 XIAO. It ensures accurate measurement through calibration and supports both serial monitor output and GUI-based visualization.

---

## 🚀 Features
- Real-time volume and flow rate measurement  
- Load cell + HX711 based sensing  
- High accuracy using multi-point calibration  
- Serial monitor output (Arduino IDE)  
- GUI-based visualization and data analysis  
- Custom 3D printed enclosure for clean and professional setup  

---

## 🧰 Components Used
- ESP32 XIAO R4M1 (or Arduino compatible board)  
- Load Cell (3kg)  
- HX711 Amplifier Module  
- Connecting Wires  
- Container setup  

---

## 🖨️ 3D Design & Mounting
A **custom 3D model** was designed to support and mount all components, providing a stable and professional structure.

- Ensures proper alignment of load cell and container  
- Improves accuracy by reducing vibration/noise  
- Gives a clean and organized look  

📁 3D printing files are available in: 3D Print folder above

---

## 💻 Code Files

### 🔹 Serial Monitor Code
- `uroflowmeter_serial.ino`  
- Runs on Arduino IDE  
- Displays volume and flow rate in Serial Monitor  

### 🔹 GUI Code
- Arduino File: `Uroflowmeter_Code_GUI.ino`  
- Python File: `Uroflowmeter_GUI.py`  
- Used for real-time visualization and monitoring  

### 🔹 Calibration Code ⚠️
- Available inside: `Uroflowmeter & GUI Codes` folder    
- Used to calibrate the load cell before measurement  

---

## ⚙️ Calibration (Important Step) ⚠️
Before using the system, **you must calibrate the load cell**:

1. Upload calibration code  
2. Open Serial Monitor  
3. Place known weights  
4. Note calibration factor  
5. Update it in main code  

👉 Calibration is **mandatory for accurate results** , Code is given in above folder

---

## ⚙️ How to Use GUI

### Step 1: Upload Arduino Code
Upload `Uroflowmeter_Code_GUI.ino` using Arduino IDE  

---

### Step 2: Close Serial Monitor ⚠️
- Close Serial Monitor after uploading  
- (Required: GUI cannot access COM port otherwise)

---

### Step 3: Install Python Libraries
Open command prompt: write - pip install "libraryname", then Enter

---

### Step 4: Run GUI
Uroflowmeter_GUI.py

---

### Step 5: Configure GUI
- Select correct COM Port
- Select correct Baud Rate
- Click Connect / OK
  
---

### Step 6: Start Measurement
- Place container on load cell
- Press "T" To tare the container Weight
- System will display:
  Volume (ml)
  Flow Rate (ml/s)
  
---

## 🔌 Working Principle

The load cell measures weight changes, which are converted into volume. Flow rate is calculated using change in volume over time. Data is transmitted via serial communication and displayed on Serial Monitor or GUI.

---

## 📊 Applications
- Medical diagnostics (uroflow analysis)
- Fluid measurement systems
- Research and data logging
  
---

## 📚 Learning Outcomes
- Sensor interfacing (HX711 + Load Cell)
- Real-time data acquisition
- Arduino–Python communication
- GUI-based monitoring
- 3D design for embedded systems

---

## ⚠️ Important Notes
- Calibration is required before use
- Use stable power supply
- Close Serial Monitor before running GUI

--- 

## 📄 License

This project is open-source and intended for educational and research purposes.
