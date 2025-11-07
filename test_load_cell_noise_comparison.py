"""
Load Cell Noise Comparison Test
================================

Compares noise characteristics between:
- Port 0: Single load cell (original)
- Port 2: Three load cells in parallel

Features:
- Real-time noise statistics (std dev, peak-to-peak, SNR)
- Moving average filtering with configurable window
- Oversampling options
- Live plotting of both channels
- CSV data export for analysis

Author: ehj3110
Date: November 6, 2025
"""

import time
import numpy as np
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import csv
from datetime import datetime

from Phidget22.Phidget import *
from Phidget22.Devices.VoltageRatioInput import *
from Phidget22.PhidgetException import PhidgetException
from Phidget22.BridgeGain import BridgeGain


class NoiseComparisonTest:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Load Cell Noise Comparison - Port 0 vs Port 2")
        self.window.geometry("1400x900")
        
        # Phidget channels
        self.channel_0 = None  # Single load cell
        self.channel_2 = None  # Three cells in parallel
        
        # Data buffers (10 seconds at 100Hz = 1000 samples)
        self.buffer_size = 1000
        self.data_port0 = deque(maxlen=self.buffer_size)
        self.data_port2 = deque(maxlen=self.buffer_size)
        self.timestamps = deque(maxlen=self.buffer_size)
        
        # Moving average buffers
        self.ma_window = 10  # Default 10-sample moving average
        self.ma_port0 = deque(maxlen=100)  # For MA calculation
        self.ma_port2 = deque(maxlen=100)
        
        # Statistics
        self.stats_port0 = {'mean': 0, 'std': 0, 'pp': 0, 'snr': 0}
        self.stats_port2 = {'mean': 0, 'std': 0, 'pp': 0, 'snr': 0}
        
        # Data recording
        self.recording = False
        self.recorded_data = []
        
        # Running flag
        self.running = True
        
        self.create_gui()
        self.initialize_phidgets()
        
    def create_gui(self):
        """Create the GUI layout."""
        # Top control panel
        control_frame = ttk.Frame(self.window, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Sampling rate control
        ttk.Label(control_frame, text="Data Interval (ms):").pack(side=tk.LEFT, padx=5)
        self.interval_var = tk.StringVar(value="10")
        interval_entry = ttk.Entry(control_frame, textvariable=self.interval_var, width=8)
        interval_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Set Interval", command=self.set_data_interval).pack(side=tk.LEFT, padx=5)
        
        # Moving average control
        ttk.Label(control_frame, text="Moving Avg Window:").pack(side=tk.LEFT, padx=(20, 5))
        self.ma_var = tk.StringVar(value="10")
        ma_entry = ttk.Entry(control_frame, textvariable=self.ma_var, width=8)
        ma_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Update", command=self.update_ma_window).pack(side=tk.LEFT, padx=5)
        
        # Recording controls
        ttk.Label(control_frame, text="Recording:").pack(side=tk.LEFT, padx=(20, 5))
        self.record_btn = ttk.Button(control_frame, text="Start Recording", command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        
        # Statistics display frame
        stats_frame = ttk.LabelFrame(self.window, text="Noise Statistics (last 1000 samples)", padding="10")
        stats_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Port 0 stats
        port0_frame = ttk.Frame(stats_frame)
        port0_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        ttk.Label(port0_frame, text="PORT 0 (Single Cell)", font=("Arial", 12, "bold")).pack()
        self.lbl_p0_mean = ttk.Label(port0_frame, text="Mean: ---", font=("Arial", 10))
        self.lbl_p0_mean.pack()
        self.lbl_p0_std = ttk.Label(port0_frame, text="Std Dev: ---", font=("Arial", 10))
        self.lbl_p0_std.pack()
        self.lbl_p0_pp = ttk.Label(port0_frame, text="Peak-Peak: ---", font=("Arial", 10))
        self.lbl_p0_pp.pack()
        self.lbl_p0_snr = ttk.Label(port0_frame, text="SNR: ---", font=("Arial", 10))
        self.lbl_p0_snr.pack()
        
        # Port 2 stats
        port2_frame = ttk.Frame(stats_frame)
        port2_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        ttk.Label(port2_frame, text="PORT 2 (3 Cells Parallel)", font=("Arial", 12, "bold")).pack()
        self.lbl_p2_mean = ttk.Label(port2_frame, text="Mean: ---", font=("Arial", 10))
        self.lbl_p2_mean.pack()
        self.lbl_p2_std = ttk.Label(port2_frame, text="Std Dev: ---", font=("Arial", 10))
        self.lbl_p2_std.pack()
        self.lbl_p2_pp = ttk.Label(port2_frame, text="Peak-Peak: ---", font=("Arial", 10))
        self.lbl_p2_pp.pack()
        self.lbl_p2_snr = ttk.Label(port2_frame, text="SNR: ---", font=("Arial", 10))
        self.lbl_p2_snr.pack()
        
        # Comparison frame
        compare_frame = ttk.Frame(stats_frame)
        compare_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        ttk.Label(compare_frame, text="Comparison", font=("Arial", 12, "bold")).pack()
        self.lbl_noise_ratio = ttk.Label(compare_frame, text="Noise Ratio (P2/P0): ---", font=("Arial", 10))
        self.lbl_noise_ratio.pack()
        self.lbl_improvement = ttk.Label(compare_frame, text="Improvement: ---", font=("Arial", 10))
        self.lbl_improvement.pack()
        self.lbl_sample_count = ttk.Label(compare_frame, text="Samples: 0", font=("Arial", 10))
        self.lbl_sample_count.pack()
        
        # Plot frame
        plot_frame = ttk.Frame(self.window)
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create matplotlib figure with 3 subplots
        self.fig = Figure(figsize=(14, 8))
        
        # Subplot 1: Raw voltage time series
        self.ax1 = self.fig.add_subplot(311)
        self.ax1.set_title("Raw Voltage Ratios (10s window)")
        self.ax1.set_ylabel("Voltage Ratio")
        self.ax1.grid(True, alpha=0.3)
        self.line_p0_raw, = self.ax1.plot([], [], 'b-', label='Port 0 (Single)', linewidth=1)
        self.line_p2_raw, = self.ax1.plot([], [], 'r-', label='Port 2 (Parallel)', linewidth=1)
        self.ax1.legend()
        
        # Subplot 2: Moving average
        self.ax2 = self.fig.add_subplot(312)
        self.ax2.set_title("Moving Average (Filtered)")
        self.ax2.set_ylabel("Voltage Ratio")
        self.ax2.grid(True, alpha=0.3)
        self.line_p0_ma, = self.ax2.plot([], [], 'b-', label='Port 0 MA', linewidth=1.5)
        self.line_p2_ma, = self.ax2.plot([], [], 'r-', label='Port 2 MA', linewidth=1.5)
        self.ax2.legend()
        
        # Subplot 3: Histogram (noise distribution)
        self.ax3 = self.fig.add_subplot(313)
        self.ax3.set_title("Noise Distribution (Histogram)")
        self.ax3.set_xlabel("Deviation from Mean")
        self.ax3.set_ylabel("Frequency")
        self.ax3.grid(True, alpha=0.3)
        
        self.canvas = FigureCanvasTkAgg(self.fig, plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.fig.tight_layout()
        
    def initialize_phidgets(self):
        """Initialize both Phidget channels."""
        try:
            print("Initializing Phidget channels...")
            
            # Channel 0 - Single load cell
            print("Setting up Port 0 (Single cell)...")
            self.channel_0 = VoltageRatioInput()
            self.channel_0.setChannel(0)
            self.channel_0.setOnVoltageRatioChangeHandler(lambda _, v: self.on_voltage_change_0(v))
            self.channel_0.setOnAttachHandler(lambda _: self.on_attach(0))
            self.channel_0.openWaitForAttachment(5000)
            
            # Channel 2 - Three cells in parallel
            print("Setting up Port 2 (Three cells parallel)...")
            self.channel_2 = VoltageRatioInput()
            self.channel_2.setChannel(2)
            self.channel_2.setOnVoltageRatioChangeHandler(lambda _, v: self.on_voltage_change_2(v))
            self.channel_2.setOnAttachHandler(lambda _: self.on_attach(2))
            self.channel_2.openWaitForAttachment(5000)
            
            print("Both channels initialized successfully!")
            messagebox.showinfo("Success", "Both load cells connected successfully!")
            
        except PhidgetException as e:
            print(f"Error initializing Phidgets: {e}")
            messagebox.showerror("Phidget Error", f"Failed to initialize: {e.description}")
    
    def on_attach(self, channel):
        """Configure channel when attached."""
        try:
            if channel == 0:
                device = self.channel_0
            else:
                device = self.channel_2
            
            device.setBridgeGain(BridgeGain.BRIDGE_GAIN_1)
            device.setDataInterval(10)  # 10ms = 100Hz
            device.setVoltageRatioChangeTrigger(0.0)  # Continuous updates
            
            if hasattr(device, 'setBridgeEnabled'):
                device.setBridgeEnabled(True)
            
            print(f"Port {channel} configured: 100Hz, continuous updates")
            
        except Exception as e:
            print(f"Error configuring port {channel}: {e}")
    
    def on_voltage_change_0(self, voltage_ratio):
        """Handle voltage change from Port 0."""
        timestamp = time.time()
        self.data_port0.append(voltage_ratio)
        
        # Update timestamp buffer (synchronized with Port 0)
        if len(self.timestamps) == 0 or timestamp > self.timestamps[-1]:
            self.timestamps.append(timestamp)
    
    def on_voltage_change_2(self, voltage_ratio):
        """Handle voltage change from Port 2."""
        self.data_port2.append(voltage_ratio)
    
    def set_data_interval(self):
        """Set the data interval for both channels."""
        try:
            interval_ms = int(self.interval_var.get())
            if interval_ms < 8 or interval_ms > 1000:
                messagebox.showerror("Invalid Interval", "Interval must be between 8 and 1000 ms")
                return
            
            if self.channel_0 and self.channel_0.getAttached():
                self.channel_0.setDataInterval(interval_ms)
            
            if self.channel_2 and self.channel_2.getAttached():
                self.channel_2.setDataInterval(interval_ms)
            
            print(f"Data interval set to {interval_ms}ms ({1000/interval_ms:.1f}Hz)")
            messagebox.showinfo("Success", f"Sampling rate: {1000/interval_ms:.1f}Hz")
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set interval: {e}")
    
    def update_ma_window(self):
        """Update moving average window size."""
        try:
            window = int(self.ma_var.get())
            if window < 1 or window > 100:
                messagebox.showerror("Invalid Window", "Window must be between 1 and 100")
                return
            
            self.ma_window = window
            print(f"Moving average window set to {window} samples")
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def calculate_statistics(self, data_buffer):
        """Calculate noise statistics for a data buffer."""
        if len(data_buffer) < 10:
            return {'mean': 0, 'std': 0, 'pp': 0, 'snr': 0}
        
        data_array = np.array(data_buffer)
        
        mean = np.mean(data_array)
        std = np.std(data_array)
        peak_to_peak = np.max(data_array) - np.min(data_array)
        snr = mean / std if std > 0 else 0
        
        return {
            'mean': mean,
            'std': std,
            'pp': peak_to_peak,
            'snr': snr
        }
    
    def calculate_moving_average(self, data_buffer, window):
        """Calculate moving average."""
        if len(data_buffer) < window:
            return list(data_buffer)
        
        data_array = np.array(data_buffer)
        ma = np.convolve(data_array, np.ones(window)/window, mode='valid')
        return ma
    
    def toggle_recording(self):
        """Start/stop recording data."""
        self.recording = not self.recording
        
        if self.recording:
            self.recorded_data = []
            self.record_btn.config(text="Stop Recording")
            print("Recording started...")
        else:
            self.record_btn.config(text="Start Recording")
            print(f"Recording stopped. {len(self.recorded_data)} samples captured.")
    
    def export_csv(self):
        """Export recorded data to CSV."""
        if len(self.recorded_data) == 0:
            messagebox.showwarning("No Data", "No recorded data to export. Start recording first.")
            return
        
        filename = f"load_cell_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Port_0_Raw', 'Port_2_Raw', 'Port_0_MA', 'Port_2_MA'])
                writer.writerows(self.recorded_data)
            
            print(f"Data exported to {filename}")
            messagebox.showinfo("Export Successful", f"Data saved to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def update_plots(self):
        """Update all plots with current data."""
        if len(self.data_port0) < 10 or len(self.data_port2) < 10:
            return
        
        # Calculate statistics
        self.stats_port0 = self.calculate_statistics(self.data_port0)
        self.stats_port2 = self.calculate_statistics(self.data_port2)
        
        # Update statistics labels
        self.lbl_p0_mean.config(text=f"Mean: {self.stats_port0['mean']:.8f}")
        self.lbl_p0_std.config(text=f"Std Dev: {self.stats_port0['std']:.10f}")
        self.lbl_p0_pp.config(text=f"Peak-Peak: {self.stats_port0['pp']:.10f}")
        self.lbl_p0_snr.config(text=f"SNR: {self.stats_port0['snr']:.1f}")
        
        self.lbl_p2_mean.config(text=f"Mean: {self.stats_port2['mean']:.8f}")
        self.lbl_p2_std.config(text=f"Std Dev: {self.stats_port2['std']:.10f}")
        self.lbl_p2_pp.config(text=f"Peak-Peak: {self.stats_port2['pp']:.10f}")
        self.lbl_p2_snr.config(text=f"SNR: {self.stats_port2['snr']:.1f}")
        
        # Comparison
        if self.stats_port0['std'] > 0:
            noise_ratio = self.stats_port2['std'] / self.stats_port0['std']
            improvement = (1 - noise_ratio) * 100
            
            self.lbl_noise_ratio.config(text=f"Noise Ratio (P2/P0): {noise_ratio:.3f}")
            
            if improvement > 0:
                self.lbl_improvement.config(text=f"Improvement: {improvement:.1f}% better", foreground="green")
            else:
                self.lbl_improvement.config(text=f"Improvement: {abs(improvement):.1f}% worse", foreground="red")
        
        self.lbl_sample_count.config(text=f"Samples: {len(self.data_port0)}")
        
        # Prepare time axis (relative time in seconds)
        if len(self.timestamps) > 0:
            t_array = np.array(self.timestamps)
            t_rel = t_array - t_array[0]
        else:
            t_rel = np.arange(len(self.data_port0))
        
        # Update raw data plot
        data_p0 = list(self.data_port0)
        data_p2 = list(self.data_port2)
        
        # Align lengths
        min_len = min(len(data_p0), len(data_p2), len(t_rel))
        t_rel = t_rel[:min_len]
        data_p0 = data_p0[:min_len]
        data_p2 = data_p2[:min_len]
        
        self.line_p0_raw.set_data(t_rel, data_p0)
        self.line_p2_raw.set_data(t_rel, data_p2)
        self.ax1.relim()
        self.ax1.autoscale_view()
        
        # Calculate and plot moving averages
        ma_p0 = self.calculate_moving_average(data_p0, self.ma_window)
        ma_p2 = self.calculate_moving_average(data_p2, self.ma_window)
        
        if len(ma_p0) > 0:
            t_ma = t_rel[self.ma_window-1:]
            self.line_p0_ma.set_data(t_ma, ma_p0)
            self.line_p2_ma.set_data(t_ma, ma_p2)
            self.ax2.relim()
            self.ax2.autoscale_view()
        
        # Update histogram (noise distribution)
        self.ax3.clear()
        
        # Deviations from mean
        dev_p0 = np.array(data_p0) - self.stats_port0['mean']
        dev_p2 = np.array(data_p2) - self.stats_port2['mean']
        
        bins = 30
        self.ax3.hist(dev_p0, bins=bins, alpha=0.5, color='blue', label='Port 0')
        self.ax3.hist(dev_p2, bins=bins, alpha=0.5, color='red', label='Port 2')
        self.ax3.set_xlabel("Deviation from Mean")
        self.ax3.set_ylabel("Frequency")
        self.ax3.legend()
        self.ax3.grid(True, alpha=0.3)
        
        # Record data if recording
        if self.recording and len(ma_p0) > 0:
            for i in range(min(len(t_rel), len(ma_p0))):
                if i < len(data_p0) and i < len(data_p2):
                    ma_idx = min(i, len(ma_p0)-1)
                    self.recorded_data.append([
                        t_rel[i],
                        data_p0[i],
                        data_p2[i],
                        ma_p0[ma_idx] if ma_idx >= 0 else 0,
                        ma_p2[ma_idx] if ma_idx >= 0 else 0
                    ])
        
        self.canvas.draw()
    
    def update_loop(self):
        """Main update loop."""
        if self.running:
            self.update_plots()
            self.window.after(100, self.update_loop)  # Update every 100ms
    
    def close(self):
        """Clean shutdown."""
        print("Closing...")
        self.running = False
        
        try:
            if self.channel_0:
                self.channel_0.close()
            if self.channel_2:
                self.channel_2.close()
            print("Channels closed successfully")
        except Exception as e:
            print(f"Error closing channels: {e}")
        
        self.window.destroy()
    
    def run(self):
        """Start the application."""
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.update_loop()
        self.window.mainloop()


if __name__ == "__main__":
    print("="*60)
    print("Load Cell Noise Comparison Test")
    print("="*60)
    print("\nThis tool compares noise characteristics between:")
    print("  - Port 0: Single load cell")
    print("  - Port 2: Three load cells in parallel")
    print("\nFeatures:")
    print("  - Real-time noise statistics")
    print("  - Moving average filtering")
    print("  - Adjustable sampling rate")
    print("  - Data recording and export")
    print("="*60)
    print()
    
    app = NoiseComparisonTest()
    app.run()
