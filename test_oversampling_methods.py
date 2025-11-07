"""
Oversampling & Noise Reduction Test
====================================

Test different oversampling and filtering techniques with your Phidget Bridge.

Features:
- Adjustable data interval (8-1000ms)
- Adjustable bridge gain (1x-128x)
- Multiple filtering methods (Moving Avg, Decimation, Median)
- Real-time SNR comparison
- Live plots showing filtering effects

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
from statistics import median

from Phidget22.Phidget import *
from Phidget22.Devices.VoltageRatioInput import *
from Phidget22.PhidgetException import PhidgetException
from Phidget22.BridgeGain import BridgeGain


class OversamplingTest:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Oversampling & Noise Reduction Test - Port 0")
        self.window.geometry("1400x900")
        
        # Phidget channel
        self.channel = None
        
        # Data buffers
        self.buffer_size = 2000  # Large buffer for analysis
        self.raw_data = deque(maxlen=self.buffer_size)
        self.filtered_ma = deque(maxlen=self.buffer_size)
        self.filtered_decimated = deque(maxlen=self.buffer_size)
        self.filtered_median = deque(maxlen=self.buffer_size)
        self.timestamps = deque(maxlen=self.buffer_size)
        
        # Oversampling buffers
        self.oversample_buffer = deque(maxlen=200)
        self.oversample_counter = 0
        
        # Filter settings
        self.ma_window = 10
        self.decimation_factor = 16
        self.median_window = 5
        
        # Statistics
        self.stats = {
            'raw': {'std': 0, 'snr': 0},
            'ma': {'std': 0, 'snr': 0},
            'decimated': {'std': 0, 'snr': 0},
            'median': {'std': 0, 'snr': 0}
        }
        
        # Running flag
        self.running = True
        
        # Measure actual sampling rate
        self.sample_count = 0
        self.last_rate_check = time.time()
        self.actual_sample_rate = 0
        
        self.create_gui()
        self.initialize_phidget()
        
    def create_gui(self):
        """Create the GUI layout."""
        # Top control panel
        control_frame = ttk.LabelFrame(self.window, text="Configuration", padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Row 1: Data interval and bridge gain
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="Data Interval (ms):").pack(side=tk.LEFT, padx=5)
        self.interval_var = tk.StringVar(value="8")
        ttk.Entry(row1, textvariable=self.interval_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Set", command=self.set_data_interval).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="Bridge Gain:").pack(side=tk.LEFT, padx=(20, 5))
        self.gain_var = tk.StringVar(value="1")
        gain_combo = ttk.Combobox(row1, textvariable=self.gain_var, width=8, 
                                   values=["1", "2", "4", "8", "16", "32", "64", "128"])
        gain_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Set", command=self.set_bridge_gain).pack(side=tk.LEFT, padx=5)
        
        # Row 2: Filter parameters
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="Moving Avg Window:").pack(side=tk.LEFT, padx=5)
        self.ma_var = tk.StringVar(value="10")
        ttk.Entry(row2, textvariable=self.ma_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="Update", command=self.update_ma).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row2, text="Decimation Factor:").pack(side=tk.LEFT, padx=(20, 5))
        self.decim_var = tk.StringVar(value="16")
        ttk.Entry(row2, textvariable=self.decim_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="Update", command=self.update_decimation).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row2, text="Median Window:").pack(side=tk.LEFT, padx=(20, 5))
        self.median_var = tk.StringVar(value="5")
        ttk.Entry(row2, textvariable=self.median_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="Update", command=self.update_median).pack(side=tk.LEFT, padx=5)
        
        # Statistics panel
        stats_frame = ttk.LabelFrame(self.window, text="Noise Statistics Comparison", padding="10")
        stats_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Create columns for each method
        methods = [
            ("Raw Data", "raw"),
            ("Moving Average", "ma"),
            ("Decimated", "decimated"),
            ("Median Filter", "median")
        ]
        
        self.stat_labels = {}
        
        for i, (name, key) in enumerate(methods):
            col = ttk.Frame(stats_frame)
            col.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
            
            ttk.Label(col, text=name, font=("Arial", 11, "bold")).pack()
            
            self.stat_labels[f"{key}_std"] = ttk.Label(col, text="Std Dev: ---", font=("Arial", 9))
            self.stat_labels[f"{key}_std"].pack()
            
            self.stat_labels[f"{key}_snr"] = ttk.Label(col, text="SNR: ---", font=("Arial", 9))
            self.stat_labels[f"{key}_snr"].pack()
            
            self.stat_labels[f"{key}_improvement"] = ttk.Label(col, text="Improvement: ---", 
                                                                font=("Arial", 9), foreground="blue")
            self.stat_labels[f"{key}_improvement"].pack()
        
        # Sampling info
        info_frame = ttk.Frame(stats_frame)
        info_frame.pack(side=tk.LEFT, padx=10)
        
        self.lbl_rate = ttk.Label(info_frame, text="Target: ~1200 Hz", font=("Arial", 9))
        self.lbl_rate.pack()
        
        self.lbl_actual_rate = ttk.Label(info_frame, text="Actual: --- Hz", 
                                         font=("Arial", 10, "bold"), foreground="blue")
        self.lbl_actual_rate.pack()
        
        self.lbl_samples = ttk.Label(info_frame, text="Samples: 0", font=("Arial", 9))
        self.lbl_samples.pack()
        
        # Plot frame
        plot_frame = ttk.Frame(self.window)
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create matplotlib figure with 4 subplots
        self.fig = Figure(figsize=(14, 8))
        
        # Subplot 1: Raw data
        self.ax1 = self.fig.add_subplot(411)
        self.ax1.set_title("Raw Data (Unfiltered)")
        self.ax1.set_ylabel("Voltage Ratio")
        self.ax1.grid(True, alpha=0.3)
        self.line_raw, = self.ax1.plot([], [], 'b-', linewidth=0.5, alpha=0.7)
        
        # Subplot 2: Moving average
        self.ax2 = self.fig.add_subplot(412)
        self.ax2.set_title("Moving Average Filter")
        self.ax2.set_ylabel("Voltage Ratio")
        self.ax2.grid(True, alpha=0.3)
        self.line_ma, = self.ax2.plot([], [], 'g-', linewidth=1)
        
        # Subplot 3: Decimated
        self.ax3 = self.fig.add_subplot(413)
        self.ax3.set_title("Decimation (Oversample + Average)")
        self.ax3.set_ylabel("Voltage Ratio")
        self.ax3.grid(True, alpha=0.3)
        self.line_decim, = self.ax3.plot([], [], 'r-', linewidth=1)
        
        # Subplot 4: Median
        self.ax4 = self.fig.add_subplot(414)
        self.ax4.set_title("Median Filter")
        self.ax4.set_xlabel("Time (s)")
        self.ax4.set_ylabel("Voltage Ratio")
        self.ax4.grid(True, alpha=0.3)
        self.line_median, = self.ax4.plot([], [], 'm-', linewidth=1)
        
        self.canvas = FigureCanvasTkAgg(self.fig, plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.fig.tight_layout()
        
    def initialize_phidget(self):
        """Initialize Phidget channel."""
        try:
            print("Initializing Phidget Bridge on Port 0...")
            
            self.channel = VoltageRatioInput()
            self.channel.setChannel(0)
            self.channel.setOnVoltageRatioChangeHandler(self.on_voltage_change)
            self.channel.setOnAttachHandler(self.on_attach)
            self.channel.openWaitForAttachment(5000)
            
            print("Port 0 connected successfully!")
            messagebox.showinfo("Success", "Load cell connected on Port 0!")
            
        except PhidgetException as e:
            print(f"Error initializing Phidget: {e}")
            messagebox.showerror("Phidget Error", f"Failed to initialize: {e.description}")
    
    def on_attach(self, device):
        """Configure channel when attached."""
        try:
            device.setBridgeGain(BridgeGain.BRIDGE_GAIN_1)
            
            # KEY: Set trigger to 0.0 for MAXIMUM hardware speed (~1200 Hz)
            device.setVoltageRatioChangeTrigger(0.0)  # Continuous streaming at max rate
            device.setDataInterval(8)  # This becomes advisory only with trigger=0
            
            if hasattr(device, 'setBridgeEnabled'):
                device.setBridgeEnabled(True)
            
            print("Port 0 configured: MAXIMUM HARDWARE RATE (~1200 Hz), Gain=1x")
            print("Note: With trigger=0.0, you get full hardware speed!")
            self.lbl_rate.config(text="Sampling: ~1200 Hz (max hardware)")
            
        except Exception as e:
            print(f"Error configuring port: {e}")
    
    def on_voltage_change(self, device, voltage_ratio):
        """Handle voltage change - apply all filters."""
        timestamp = time.time()
        
        # Count samples for rate measurement
        self.sample_count += 1
        if timestamp - self.last_rate_check >= 1.0:
            self.actual_sample_rate = self.sample_count / (timestamp - self.last_rate_check)
            self.sample_count = 0
            self.last_rate_check = timestamp
        
        # Store raw data
        self.raw_data.append(voltage_ratio)
        self.timestamps.append(timestamp)
        
        # Moving average filter
        if len(self.raw_data) >= self.ma_window:
            ma_value = sum(list(self.raw_data)[-self.ma_window:]) / self.ma_window
            self.filtered_ma.append(ma_value)
        
        # Decimation filter (oversample + average)
        self.oversample_buffer.append(voltage_ratio)
        self.oversample_counter += 1
        
        if self.oversample_counter >= self.decimation_factor:
            decimated_value = sum(self.oversample_buffer) / len(self.oversample_buffer)
            self.filtered_decimated.append(decimated_value)
            self.oversample_counter = 0
        
        # Median filter
        if len(self.raw_data) >= self.median_window:
            median_value = median(list(self.raw_data)[-self.median_window:])
            self.filtered_median.append(median_value)
    
    def set_data_interval(self):
        """Set the data interval."""
        try:
            interval_ms = int(self.interval_var.get())
            if interval_ms < 8 or interval_ms > 1000:
                messagebox.showerror("Invalid", "Interval must be 8-1000 ms")
                return
            
            if self.channel and self.channel.getAttached():
                self.channel.setDataInterval(interval_ms)
                rate = 1000 / interval_ms
                print(f"Data interval set to {interval_ms}ms ({rate:.1f}Hz)")
                self.lbl_rate.config(text=f"Sampling: {rate:.1f} Hz ({interval_ms}ms)")
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set interval: {e}")
    
    def set_bridge_gain(self):
        """Set the bridge gain."""
        try:
            gain_value = int(self.gain_var.get())
            
            gain_map = {
                1: BridgeGain.BRIDGE_GAIN_1,
                2: BridgeGain.BRIDGE_GAIN_2,
                4: BridgeGain.BRIDGE_GAIN_4,
                8: BridgeGain.BRIDGE_GAIN_8,
                16: BridgeGain.BRIDGE_GAIN_16,
                32: BridgeGain.BRIDGE_GAIN_32,
                64: BridgeGain.BRIDGE_GAIN_64,
                128: BridgeGain.BRIDGE_GAIN_128
            }
            
            if gain_value not in gain_map:
                messagebox.showerror("Invalid", "Gain must be 1, 2, 4, 8, 16, 32, 64, or 128")
                return
            
            if self.channel and self.channel.getAttached():
                self.channel.setBridgeGain(gain_map[gain_value])
                print(f"Bridge gain set to {gain_value}x")
                messagebox.showinfo("Success", f"Bridge gain set to {gain_value}x\n\n"
                                   f"Note: Clear buffers to see effect")
                
                # Clear buffers to show fresh data with new gain
                self.raw_data.clear()
                self.filtered_ma.clear()
                self.filtered_decimated.clear()
                self.filtered_median.clear()
                self.timestamps.clear()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set gain: {e}")
    
    def update_ma(self):
        """Update moving average window."""
        try:
            window = int(self.ma_var.get())
            if window < 1 or window > 200:
                messagebox.showerror("Invalid", "Window must be 1-200")
                return
            self.ma_window = window
            print(f"Moving average window: {window}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def update_decimation(self):
        """Update decimation factor."""
        try:
            factor = int(self.decim_var.get())
            if factor < 1 or factor > 200:
                messagebox.showerror("Invalid", "Factor must be 1-200")
                return
            self.decimation_factor = factor
            self.oversample_buffer = deque(maxlen=factor * 2)
            print(f"Decimation factor: {factor}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def update_median(self):
        """Update median filter window."""
        try:
            window = int(self.median_var.get())
            if window < 1 or window > 51 or window % 2 == 0:
                messagebox.showerror("Invalid", "Window must be odd number, 1-51")
                return
            self.median_window = window
            print(f"Median window: {window}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def calculate_statistics(self):
        """Calculate noise statistics for all methods."""
        if len(self.raw_data) < 50:
            return
        
        # Raw data stats
        raw_array = np.array(self.raw_data)
        raw_mean = np.mean(raw_array)
        raw_std = np.std(raw_array)
        raw_snr = raw_mean / raw_std if raw_std > 0 else 0
        
        self.stats['raw'] = {'std': raw_std, 'snr': raw_snr}
        
        # Moving average stats
        if len(self.filtered_ma) > 10:
            ma_array = np.array(self.filtered_ma)
            ma_std = np.std(ma_array)
            ma_snr = raw_mean / ma_std if ma_std > 0 else 0
            self.stats['ma'] = {'std': ma_std, 'snr': ma_snr}
        
        # Decimated stats
        if len(self.filtered_decimated) > 10:
            decim_array = np.array(self.filtered_decimated)
            decim_std = np.std(decim_array)
            decim_snr = raw_mean / decim_std if decim_std > 0 else 0
            self.stats['decimated'] = {'std': decim_std, 'snr': decim_snr}
        
        # Median stats
        if len(self.filtered_median) > 10:
            median_array = np.array(self.filtered_median)
            median_std = np.std(median_array)
            median_snr = raw_mean / median_std if median_std > 0 else 0
            self.stats['median'] = {'std': median_std, 'snr': median_snr}
    
    def update_display(self):
        """Update statistics and plots."""
        if len(self.raw_data) < 10:
            return
        
        # Calculate statistics
        self.calculate_statistics()
        
        # Update statistics labels
        raw_std = self.stats['raw']['std']
        
        for method in ['raw', 'ma', 'decimated', 'median']:
            std = self.stats[method]['std']
            snr = self.stats[method]['snr']
            
            self.stat_labels[f"{method}_std"].config(text=f"Std Dev: {std:.10f}")
            self.stat_labels[f"{method}_snr"].config(text=f"SNR: {snr:.1f}")
            
            if method != 'raw' and raw_std > 0:
                improvement = (1 - std / raw_std) * 100
                if improvement > 0:
                    self.stat_labels[f"{method}_improvement"].config(
                        text=f"↓ {improvement:.1f}% noise",
                        foreground="green"
                    )
                else:
                    self.stat_labels[f"{method}_improvement"].config(
                        text=f"↑ {abs(improvement):.1f}% noise",
                        foreground="red"
                    )
        
        self.lbl_samples.config(text=f"Samples: {len(self.raw_data)}")
        
        # Update actual sample rate display
        if self.actual_sample_rate > 0:
            self.lbl_actual_rate.config(text=f"Actual: {self.actual_sample_rate:.0f} Hz")
        
        # Update plots
        if len(self.timestamps) > 0:
            t_array = np.array(self.timestamps)
            t_rel = t_array - t_array[0]
            
            # Raw data plot
            self.line_raw.set_data(t_rel, list(self.raw_data))
            self.ax1.relim()
            self.ax1.autoscale_view()
            
            # Moving average plot
            if len(self.filtered_ma) > 0:
                t_ma = t_rel[-len(self.filtered_ma):]
                self.line_ma.set_data(t_ma, list(self.filtered_ma))
                self.ax2.relim()
                self.ax2.autoscale_view()
            
            # Decimated plot
            if len(self.filtered_decimated) > 0:
                # Create time points for decimated data
                t_decim = np.linspace(t_rel[0], t_rel[-1], len(self.filtered_decimated))
                self.line_decim.set_data(t_decim, list(self.filtered_decimated))
                self.ax3.relim()
                self.ax3.autoscale_view()
            
            # Median plot
            if len(self.filtered_median) > 0:
                t_median = t_rel[-len(self.filtered_median):]
                self.line_median.set_data(t_median, list(self.filtered_median))
                self.ax4.relim()
                self.ax4.autoscale_view()
            
            self.canvas.draw()
    
    def update_loop(self):
        """Main update loop."""
        if self.running:
            self.update_display()
            self.window.after(200, self.update_loop)  # Update display every 200ms
    
    def close(self):
        """Clean shutdown."""
        print("Closing...")
        self.running = False
        
        try:
            if self.channel:
                self.channel.close()
            print("Channel closed successfully")
        except Exception as e:
            print(f"Error closing channel: {e}")
        
        self.window.destroy()
    
    def run(self):
        """Start the application."""
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.update_loop()
        self.window.mainloop()


if __name__ == "__main__":
    print("="*60)
    print("Oversampling & Noise Reduction Test")
    print("="*60)
    print("\nTest different filtering techniques:")
    print("  1. Moving Average - continuous filtering")
    print("  2. Decimation - oversample + average")
    print("  3. Median Filter - spike rejection")
    print("\nAdjust parameters and compare results!")
    print("="*60)
    print()
    
    app = OversamplingTest()
    app.run()
