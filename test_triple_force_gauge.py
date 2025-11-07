"""
Triple Force Gauge Test Script
===============================

Test script for three-load-cell parallel configuration.
Mimics SensorDataWindow and ForceGaugeManager workflow with live plotting.

Hardware Setup:
- Phidget Bridge (new unit)
- Load Cell #1: Port 0
- Load Cell #2: Port 1  
- Load Cell #3: Port 2

This script will:
1. Open a GUI window similar to SensorDataWindow
2. Initialize all three channels
3. Run the same calibration routine as the main printing system
4. Display live plots showing individual + summed forces
5. Allow monitoring of force alignment across all three cells

Author: Cheng Sun Lab Team
Date: October 31, 2025
"""

import time
import sys
import queue
import threading
from collections import deque
from tkinter import *
from tkinter import messagebox, simpledialog, font as tkFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from Phidget22.Phidget import *
from Phidget22.Devices.VoltageRatioInput import *
from Phidget22.PhidgetException import PhidgetException
from Phidget22.BridgeGain import BridgeGain

class TripleForceGaugeManager:
    """
    Manager for three parallel load cells.
    Mimics ForceGaugeManager architecture but handles 3 channels.
    """
    
    def __init__(self, gain_labels, offset_labels, force_status_label, 
                 large_force_readout_label, parent_window):
        # GUI labels (3 sets for individual channels + 1 for total)
        self.gain_labels = gain_labels  # List of 3 labels
        self.offset_labels = offset_labels  # List of 3 labels
        self.force_status_label = force_status_label
        self.large_force_readout_label = large_force_readout_label
        self.parent_window = parent_window
        
        # Calibration data for each channel
        self.GAINS = [None, None, None]
        self.OFFSETS = [None, None, None]
        
        # Phidget channels
        self.voltage_ratio_inputs = [None, None, None]
        self.channel_ports = [0, 1, 2]
        
        # Latest readings
        self.latest_voltages = [0.0, 0.0, 0.0]
        self.latest_forces = [0.0, 0.0, 0.0]
        self.latest_total_force = 0.0
        
        # Status
        self.calibrated = [False, False, False]
        self.attached = [False, False, False]
        self.calibrated_once = False  # True when all 3 are calibrated
        
        # Threading for data collection
        self.running = True
        self.data_queues = [queue.Queue(maxsize=1000) for _ in range(3)]
        
        # High-frequency data buffering
        self.voltage_buffers = [deque(maxlen=100) for _ in range(3)]
        self.force_buffers = [deque(maxlen=100) for _ in range(3)]
        
        # Initialize in background
        self.initialization_thread = threading.Thread(
            target=self.initialize_channels_background, daemon=True)
        self.initialization_thread.start()
        
    def initialize_channels_background(self):
        """Initialize all three Phidget channels in background thread."""
        print("\n" + "="*60)
        print("TRIPLE FORCE GAUGE INITIALIZATION")
        print("="*60)
        
        for i, port in enumerate(self.channel_ports):
            print(f"\nInitializing Channel {i} (Port {port})...")
            
            try:
                ch = VoltageRatioInput()
                ch.setChannel(port)
                
                # Set up event handlers
                ch.setOnAttachHandler(lambda sender, i=i: self.on_attach(sender, i))
                ch.setOnDetachHandler(lambda sender, i=i: self.on_detach(sender, i))
                ch.setOnVoltageRatioChangeHandler(
                    lambda sender, voltage, i=i: self.on_voltage_change(sender, voltage, i))
                ch.setOnErrorHandler(
                    lambda sender, code, desc, i=i: self.on_error(sender, code, desc, i))
                
                # Open and attach
                ch.openWaitForAttachment(5000)
                
                # Configure for high sensitivity
                ch.setBridgeGain(BridgeGain.BRIDGE_GAIN_128)
                ch.setDataInterval(8)  # ~125 Hz
                
                self.voltage_ratio_inputs[i] = ch
                print(f"  ✅ Channel {i} initialized successfully")
                
            except PhidgetException as e:
                print(f"  ❌ Channel {i} initialization failed: {e}")
                self.voltage_ratio_inputs[i] = None
                
        print("="*60)
        
        # Update GUI
        if all(self.attached):
            self.update_status_label("All 3 channels attached ✅", color="green")
        else:
            attached_count = sum(self.attached)
            self.update_status_label(f"⚠️ Only {attached_count}/3 channels attached", color="orange")
            
    def on_attach(self, sender, channel_index):
        """Handle channel attachment."""
        self.attached[channel_index] = True
        print(f"✅ Channel {channel_index} attached")
        
    def on_detach(self, sender, channel_index):
        """Handle channel detachment."""
        self.attached[channel_index] = False
        print(f"⚠️ Channel {channel_index} detached")
        self.update_status_label(f"⚠️ Channel {channel_index} detached!", color="red")
        
    def on_voltage_change(self, sender, voltage_ratio, channel_index):
        """Handle voltage ratio change (high-frequency callback)."""
        self.latest_voltages[channel_index] = voltage_ratio
        self.voltage_buffers[channel_index].append(voltage_ratio)
        
        # Calculate force if calibrated
        # Formula: Force = Gain × (Voltage - Offset)
        # Where Offset is the tared (zero-force) voltage
        if self.calibrated[channel_index]:
            force = self.GAINS[channel_index] * (voltage_ratio - self.OFFSETS[channel_index])
            self.latest_forces[channel_index] = force
            self.force_buffers[channel_index].append(force)
            
        # Update total force
        if all(self.calibrated):
            self.latest_total_force = sum(self.latest_forces)
            
    def on_error(self, sender, error_code, error_string, channel_index):
        """Handle errors."""
        print(f"❌ Channel {channel_index} Error: {error_string}")
        
    def calibrate_force_gauge(self):
        """
        Calibrate all three force gauges simultaneously using two-point calibration.
        All three cells are loaded together, and each gets calibrated to the SAME force value.
        Mimics the ForceGaugeManager.calibrate_force_gauge() routine.
        """
        try:
            print("\nStarting triple force gauge calibration (simultaneous mode)...")
            
            # Check all channels attached
            if not all(self.attached):
                messagebox.showerror("Calibration Error", 
                    "Not all force sensors are attached!\n" +
                    "\n".join([f"Channel {i}: {'✅' if self.attached[i] else '❌'}" 
                              for i in range(3)]),
                    parent=self.parent_window)
                return
                
            # Step 1: Zero force calibration (tare all channels INDIVIDUALLY)
            messagebox.showinfo("Calibration Step 1", 
                "Please ensure ALL THREE load cells are at zero force.\n\n"
                "Remove any applied force from the system, then click OK.",
                parent=self.parent_window)
            
            time.sleep(0.5)  # Stabilize
            
            print("\n--- TARE (Zero Force) Calibration ---")
            for i in range(3):
                if self.voltage_ratio_inputs[i]:
                    zero_voltage = self.voltage_ratio_inputs[i].getVoltageRatio()
                    self.OFFSETS[i] = zero_voltage
                    print(f"Channel {i} - Tare voltage (OFFSET): {zero_voltage:.8f} V/V")
                    
            # Step 2: Known force calibration (ALL CHANNELS SIMULTANEOUSLY)
            known_force_str = simpledialog.askstring("Calibration Step 2",
                "Enter the TOTAL known force in Newtons (N):\n\n"
                "This is the total force that will be applied to ALL THREE cells.\n"
                "Each cell will be calibrated assuming it bears an equal share.\n\n"
                "Example: If you apply 9.81 N total (1kg), each cell sees ~3.27 N",
                parent=self.parent_window)
                
            if known_force_str is None:
                print("Calibration cancelled by user")
                return
                
            try:
                total_known_force = float(known_force_str)
            except ValueError:
                messagebox.showerror("Calibration Error", 
                    "Invalid force value. Please enter a number.",
                    parent=self.parent_window)
                return
            
            # Each cell should ideally see 1/3 of the total force
            force_per_cell = total_known_force / 3.0
            
            # Apply force to all three cells simultaneously
            messagebox.showinfo("Calibration - Apply Force",
                f"Apply {total_known_force:.4f} N TOTAL force to the system.\n\n"
                f"The force should be distributed across all three cells.\n"
                f"(Ideally each cell sees ~{force_per_cell:.4f} N)\n\n"
                f"Click OK when force is fully applied and stable.",
                parent=self.parent_window)
                
            time.sleep(0.5)  # Stabilize
            
            # Calibrate all three channels at once
            print("\n--- Apply Known Force Calibration ---")
            loaded_voltages = []
            for i in range(3):
                if self.voltage_ratio_inputs[i]:
                    loaded_voltage = self.voltage_ratio_inputs[i].getVoltageRatio()
                    loaded_voltages.append(loaded_voltage)
                    
                    # Check for significant change (can be positive OR negative)
                    voltage_change = loaded_voltage - self.OFFSETS[i]
                    if abs(voltage_change) < 1e-9:
                        messagebox.showerror("Calibration Error",
                            f"Channel {i}: Voltage did not change!\n"
                            f"Check that force is applied or sensor connection.",
                            parent=self.parent_window)
                        return
                    
                    print(f"Channel {i} - Loaded voltage: {loaded_voltage:.8f} V/V")
                    print(f"Channel {i} - Voltage CHANGE (Δ): {voltage_change:+.8f} V/V")
            
            # Calculate the actual force seen by each cell based on voltage distribution
            # Sum ABSOLUTE values of voltage changes to handle compression (negative changes)
            voltage_changes = [loaded_voltages[i] - self.OFFSETS[i] for i in range(3)]
            total_voltage_change = sum(abs(change) for change in voltage_changes)
            
            print(f"\n--- Force Distribution Calculation ---")
            print(f"Total absolute voltage change: {total_voltage_change:.8f} V/V")
            
            # Each cell's gain is calculated based on its proportional share of the voltage change
            for i in range(3):
                voltage_change = voltage_changes[i]
                
                # This cell's share of the total force based on its voltage response
                force_fraction = abs(voltage_change) / total_voltage_change
                actual_force_on_cell = total_known_force * force_fraction
                
                # Calculate gain: Force = Gain × (Voltage - Offset)
                # For compression cells, voltage_change is negative, so we need to handle the sign
                # We want positive force output for compression, so:
                # If voltage decreases (negative change) with applied force, gain should be negative
                self.GAINS[i] = actual_force_on_cell / abs(voltage_change)
                if voltage_change < 0:
                    self.GAINS[i] = -self.GAINS[i]  # Negative gain for compression
                
                self.calibrated[i] = True
                
                print(f"\nChannel {i}:")
                print(f"  Voltage change: {voltage_change:+.8f} V/V")
                print(f"  Force fraction: {force_fraction*100:.2f}% of total")
                print(f"  Force on cell: {actual_force_on_cell:.4f} N")
                print(f"  GAIN: {self.GAINS[i]:.4f} N/(V/V)")
                print(f"  OFFSET: {self.OFFSETS[i]:.8f} V/V")
                print(f"  --> Formula: Force = {self.GAINS[i]:.4f} × (V - {self.OFFSETS[i]:.8f})")
                
                # Update GUI labels
                if self.gain_labels[i]:
                    self.gain_labels[i].config(text=f"Ch{i} Gain: {self.GAINS[i]:.4f}")
                if self.offset_labels[i]:
                    self.offset_labels[i].config(text=f"Ch{i} Offset: {self.OFFSETS[i]:.8f}")
            
            # Verify the sum
            calculated_total = sum(actual_force_on_cell for i in range(3))
            print(f"\nVerification: Sum of individual forces = {calculated_total:.4f} N (should be {total_known_force:.4f} N)")
                    
            # All channels calibrated
            self.calibrated_once = True
            self.update_status_label("All channels calibrated ✅", color="green")
            
            # Show results with force distribution
            force_distribution = "\n".join([
                f"Channel {i}: {abs(voltage_changes[i]) / total_voltage_change * 100:.1f}% "
                f"(~{total_known_force * abs(voltage_changes[i]) / total_voltage_change:.4f} N)"
                for i in range(3)
            ])
            
            messagebox.showinfo("Calibration Complete",
                f"All three channels calibrated successfully!\n\n"
                f"Applied total force: {total_known_force:.4f} N\n\n"
                f"Force distribution:\n{force_distribution}\n\n"
                f"Note: Uneven distribution may indicate mechanical misalignment.",
                parent=self.parent_window)
                
            print("="*60)
            print("CALIBRATION COMPLETE")
            print("="*60)
            
        except PhidgetException as pe:
            print(f"Phidget error during calibration: {pe}")
            messagebox.showerror("Calibration Error", 
                f"Phidget error: {pe.description}",
                parent=self.parent_window)
        except Exception as e:
            print(f"Error during calibration: {e}")
            messagebox.showerror("Calibration Error",
                f"An error occurred: {e}",
                parent=self.parent_window)
            import traceback
            traceback.print_exc()
            
    def get_latest_total_force(self):
        """Get the summed force from all three channels."""
        return self.latest_total_force
        
    def get_latest_individual_forces(self):
        """Get individual forces as a list."""
        return self.latest_forces.copy()
        
    def is_calibrated(self):
        """Check if all channels are calibrated."""
        return self.calibrated_once and all(self.calibrated)
        
    def update_status_label(self, message, color="black"):
        """Update the status label."""
        if self.force_status_label:
            try:
                self.force_status_label.config(text=message, fg=color)
            except:
                pass
                
    def shutdown(self):
        """Clean shutdown of all channels."""
        print("\nShutting down triple force gauge manager...")
        self.running = False
        
        for i, ch in enumerate(self.voltage_ratio_inputs):
            if ch:
                try:
                    ch.close()
                    print(f"  ✅ Channel {i} closed")
                except:
                    pass


class TripleForcePlotWindow:
    """
    Popup window with live plotting of voltage ratios and forces.
    Shows raw sensor data and calculated forces for diagnostics.
    """
    
    def __init__(self, master, force_manager):
        self.force_manager = force_manager
        
        # Create toplevel window
        self.window = Toplevel(master)
        self.window.title("Triple Force Gauge - Live Monitor")
        self.window.geometry("900x900")
        
        # Title
        title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        title_label = Label(self.window, text="Live Sensor Monitoring - Voltage Ratios & Forces",
                           font=title_font)
        title_label.pack(side=TOP, pady=10)
        
        # Create matplotlib figure with 3 subplots
        self.figure = Figure(figsize=(9, 8), dpi=100)
        
        # Top subplot: Voltage ratios (RAW DATA)
        self.ax1 = self.figure.add_subplot(311)
        self.ax1.set_title("Raw Voltage Ratios (V/V)", fontsize=11, weight='bold')
        self.ax1.set_ylabel("Voltage Ratio", fontsize=10)
        self.ax1.grid(True, alpha=0.3)
        
        # Middle subplot: Individual forces
        self.ax2 = self.figure.add_subplot(312)
        self.ax2.set_title("Individual Load Cell Forces", fontsize=11, weight='bold')
        self.ax2.set_ylabel("Force (N)", fontsize=10)
        self.ax2.grid(True, alpha=0.3)
        
        # Bottom subplot: Total force
        self.ax3 = self.figure.add_subplot(313)
        self.ax3.set_title("Total Force (Sum of All Three)", fontsize=11, weight='bold')
        self.ax3.set_xlabel("Time (s)", fontsize=10)
        self.ax3.set_ylabel("Force (N)", fontsize=10)
        self.ax3.grid(True, alpha=0.3)
        
        self.figure.tight_layout(pad=2.0)
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.window)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
        
        # Data storage
        self.time_data = deque(maxlen=500)  # 500 points
        
        # Voltage ratio data
        self.voltage_ch0 = deque(maxlen=500)
        self.voltage_ch1 = deque(maxlen=500)
        self.voltage_ch2 = deque(maxlen=500)
        
        # Force data
        self.force_ch0 = deque(maxlen=500)
        self.force_ch1 = deque(maxlen=500)
        self.force_ch2 = deque(maxlen=500)
        self.force_total = deque(maxlen=500)
        
        self.start_time = time.time()
        
        # Plot lines for voltage ratios
        self.line_v0, = self.ax1.plot([], [], 'b-', label='Channel 0', linewidth=1.5)
        self.line_v1, = self.ax1.plot([], [], 'r-', label='Channel 1', linewidth=1.5)
        self.line_v2, = self.ax1.plot([], [], 'g-', label='Channel 2', linewidth=1.5)
        self.ax1.legend(loc='upper right', fontsize=9)
        
        # Plot lines for individual forces
        self.line_f0, = self.ax2.plot([], [], 'b-', label='Channel 0', linewidth=1.5)
        self.line_f1, = self.ax2.plot([], [], 'r-', label='Channel 1', linewidth=1.5)
        self.line_f2, = self.ax2.plot([], [], 'g-', label='Channel 2', linewidth=1.5)
        self.ax2.legend(loc='upper right', fontsize=9)
        
        # Plot line for total force
        self.line_total, = self.ax3.plot([], [], 'k-', linewidth=2)
        
        # Start update loop
        self.running = True
        self.update_plot()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def update_plot(self):
        """Update plots with latest voltage and force data."""
        if not self.running:
            return
            
        # Get latest voltages and forces
        voltages = [
            self.force_manager.latest_voltages[0],
            self.force_manager.latest_voltages[1],
            self.force_manager.latest_voltages[2]
        ]
        forces = self.force_manager.get_latest_individual_forces()
        total_force = self.force_manager.get_latest_total_force()
        current_time = time.time() - self.start_time
        
        # Append data
        self.time_data.append(current_time)
        
        # Voltage ratios
        self.voltage_ch0.append(voltages[0])
        self.voltage_ch1.append(voltages[1])
        self.voltage_ch2.append(voltages[2])
        
        # Forces
        self.force_ch0.append(forces[0])
        self.force_ch1.append(forces[1])
        self.force_ch2.append(forces[2])
        self.force_total.append(total_force)
        
        # Update plot lines
        time_array = list(self.time_data)
        
        # Voltage ratio plots
        self.line_v0.set_data(time_array, list(self.voltage_ch0))
        self.line_v1.set_data(time_array, list(self.voltage_ch1))
        self.line_v2.set_data(time_array, list(self.voltage_ch2))
        
        # Force plots
        self.line_f0.set_data(time_array, list(self.force_ch0))
        self.line_f1.set_data(time_array, list(self.force_ch1))
        self.line_f2.set_data(time_array, list(self.force_ch2))
        self.line_total.set_data(time_array, list(self.force_total))
        
        # Adjust axes
        if len(time_array) > 0:
            # X-axis (time) - same for all plots
            max_time = max(10, time_array[-1])
            self.ax1.set_xlim(0, max_time)
            self.ax2.set_xlim(0, max_time)
            self.ax3.set_xlim(0, max_time)
            
            # Y-axis for voltage ratios (top plot)
            all_voltages = list(self.voltage_ch0) + list(self.voltage_ch1) + list(self.voltage_ch2)
            if all_voltages:
                min_v = min(all_voltages)
                max_v = max(all_voltages)
                padding_v = max(0.0001, (max_v - min_v) * 0.1)
                self.ax1.set_ylim(min_v - padding_v, max_v + padding_v)
            
            # Y-axis for individual forces (middle plot)
            all_forces = list(self.force_ch0) + list(self.force_ch1) + list(self.force_ch2)
            if all_forces:
                min_f = min(all_forces)
                max_f = max(all_forces)
                padding_f = max(0.1, (max_f - min_f) * 0.1)
                self.ax2.set_ylim(min_f - padding_f, max_f + padding_f)
                
            # Y-axis for total force (bottom plot)
            if list(self.force_total):
                min_t = min(self.force_total)
                max_t = max(self.force_total)
                padding_t = max(0.1, (max_t - min_t) * 0.1)
                self.ax3.set_ylim(min_t - padding_t, max_t + padding_t)
        
        self.canvas.draw()
        
        # Schedule next update (50ms = 20 Hz)
        if self.running:
            self.window.after(50, self.update_plot)
            
    def on_close(self):
        """Handle window close."""
        self.running = False
        self.window.destroy()


class TripleForceGaugeTestWindow:
    """
    Main test window that mimics SensorDataWindow structure.
    """
    
    def __init__(self, master):
        self.master = master
        self.master.title("Triple Force Gauge Test System")
        self.master.geometry("600x500")
        
        # Title
        title_font = tkFont.Font(family="Helvetica", size=16, weight="bold")
        title_label = Label(self.master, text="Triple Load Cell Test System", font=title_font)
        title_label.pack(side=TOP, pady=15)
        
        # Status banner
        status_frame = Frame(self.master)
        status_frame.pack(side=TOP, fill=X, padx=20, pady=5)
        
        status_label_font = tkFont.Font(family="Helvetica", size=10)
        Label(status_frame, text="Status:", font=status_label_font).pack(side=LEFT)
        
        self.status_label = Label(status_frame, text="Initializing...", 
                                 font=status_label_font, fg="orange")
        self.status_label.pack(side=LEFT, padx=10)
        
        # Large force readout
        readout_frame = Frame(self.master, relief=RIDGE, borderwidth=3)
        readout_frame.pack(side=TOP, fill=X, padx=20, pady=15)
        
        readout_font = tkFont.Font(family="Helvetica", size=18, weight="bold")
        self.force_readout_label = Label(readout_frame, text="Total Force: --- N",
                                        font=readout_font, fg="blue")
        self.force_readout_label.pack(pady=10)
        
        # Individual channel readouts
        channels_frame = LabelFrame(self.master, text="Individual Channel Forces",
                                    font=tkFont.Font(family="Helvetica", size=10, weight="bold"),
                                    relief=RIDGE, borderwidth=2)
        channels_frame.pack(side=TOP, fill=BOTH, expand=True, padx=20, pady=10)
        
        readout_small_font = tkFont.Font(family="Helvetica", size=11)
        
        self.channel_force_labels = []
        for i in range(3):
            ch_frame = Frame(channels_frame)
            ch_frame.pack(side=TOP, fill=X, padx=10, pady=5)
            
            Label(ch_frame, text=f"Channel {i}:", font=readout_small_font).pack(side=LEFT)
            force_label = Label(ch_frame, text="--- N", font=readout_small_font, 
                              fg=["blue", "red", "green"][i])
            force_label.pack(side=LEFT, padx=10)
            self.channel_force_labels.append(force_label)
            
        # Calibration info
        cal_frame = LabelFrame(self.master, text="Calibration Parameters",
                              font=tkFont.Font(family="Helvetica", size=10, weight="bold"),
                              relief=RIDGE, borderwidth=2)
        cal_frame.pack(side=TOP, fill=X, padx=20, pady=10)
        
        cal_font = tkFont.Font(family="Helvetica", size=9)
        
        self.gain_labels = []
        self.offset_labels = []
        
        for i in range(3):
            gain_label = Label(cal_frame, text=f"Ch{i} Gain: ---", font=cal_font)
            gain_label.grid(row=i, column=0, sticky=W, padx=5, pady=2)
            self.gain_labels.append(gain_label)
            
            offset_label = Label(cal_frame, text=f"Ch{i} Offset: ---", font=cal_font)
            offset_label.grid(row=i, column=1, sticky=W, padx=5, pady=2)
            self.offset_labels.append(offset_label)
            
        # Control buttons
        button_frame = Frame(self.master)
        button_frame.pack(side=TOP, fill=X, padx=20, pady=15)
        
        button_font = tkFont.Font(family="Helvetica", size=11, weight="bold")
        
        self.calibrate_button = Button(button_frame, text="Calibrate Force Gauges",
                                       font=button_font, bg="lightblue",
                                       command=self.calibrate_gauges, height=2)
        self.calibrate_button.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        self.plot_button = Button(button_frame, text="Open Live Plot",
                                  font=button_font, bg="lightgreen",
                                  command=self.open_live_plot, height=2)
        self.plot_button.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        # Initialize force gauge manager
        self.force_manager = TripleForceGaugeManager(
            gain_labels=self.gain_labels,
            offset_labels=self.offset_labels,
            force_status_label=self.status_label,
            large_force_readout_label=self.force_readout_label,
            parent_window=self.master
        )
        
        # Plot window reference
        self.plot_window = None
        
        # Start GUI update loop
        self.update_gui()
        
        # Handle window close
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def update_gui(self):
        """Update GUI with latest force readings."""
        # Update total force
        if self.force_manager.is_calibrated():
            total_force = self.force_manager.get_latest_total_force()
            self.force_readout_label.config(text=f"Total Force: {total_force:+.4f} N")
            
            # Update individual forces
            forces = self.force_manager.get_latest_individual_forces()
            for i, force_label in enumerate(self.channel_force_labels):
                force_label.config(text=f"{forces[i]:+.4f} N")
        else:
            self.force_readout_label.config(text="Total Force: Not Calibrated")
            for force_label in self.channel_force_labels:
                force_label.config(text="--- N")
                
        # Schedule next update
        self.master.after(100, self.update_gui)  # 10 Hz
        
    def calibrate_gauges(self):
        """Run calibration routine."""
        self.force_manager.calibrate_force_gauge()
            
    def open_live_plot(self):
        """Open the live plotting window."""
        if self.plot_window is None:
            self.plot_window = TripleForcePlotWindow(self.master, self.force_manager)
        else:
            messagebox.showinfo("Plot Already Open",
                "Live plot window is already open!",
                parent=self.master)
                
    def on_close(self):
        """Handle window close."""
        if messagebox.askokcancel("Quit", "Close the test system?", parent=self.master):
            self.force_manager.shutdown()
            if self.plot_window:
                self.plot_window.on_close()
            self.master.destroy()


def main():
    """Main entry point."""
    root = Tk()
    app = TripleForceGaugeTestWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
