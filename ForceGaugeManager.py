import time
import traceback
import queue
from tkinter import messagebox, simpledialog
from Phidget22.Phidget import *
from Phidget22.Devices.VoltageRatioInput import *
from Phidget22.Net import *
from Phidget22.PhidgetException import PhidgetException
from Phidget22.ErrorCode import ErrorCode
from Phidget22.BridgeGain import BridgeGain

class ForceGaugeManager:
    def __init__(self, gain_label, offset_label, force_status_label, large_force_readout_label, output_force_queue, parent_window, sensor_window_ref):
        self.gain_label = gain_label
        self.offset_label = offset_label
        self.force_status_label = force_status_label
        self.large_force_readout_label = large_force_readout_label
        self.output_force_queue = output_force_queue
        self.parent_window = parent_window
        self.sensor_window_ref = sensor_window_ref

        self.GAIN = None
        self.OFFSET = None
        self.voltage_ratio_input = None
        self.latest_calibrated_force = 0.0 # Initialize to a default float value
        self.calibrated_once = False
        self.initialize_phidget()

    def initialize_phidget(self):
        try:
            print("Initializing VoltageRatioInput (ForceGaugeManager)...")
            self.voltage_ratio_input = VoltageRatioInput()
            self.voltage_ratio_input.setChannel(2) # Assuming channel 2, adjust if necessary
            self.voltage_ratio_input.setOnVoltageRatioChangeHandler(self._onVoltageRatioChange)
            self.voltage_ratio_input.setOnAttachHandler(self._onAttach)
            self.voltage_ratio_input.setOnDetachHandler(self._onDetach)
            self.voltage_ratio_input.setOnErrorHandler(self._onError)
            self.voltage_ratio_input.openWaitForAttachment(5000)
            print("Phidget connected successfully (ForceGaugeManager)!")
        except PhidgetException as ex:
            traceback.print_exc()
            messagebox.showerror("Phidget Error", f"PhidgetException {ex.code} ({ex.description}): {ex.details}", parent=self.parent_window)
            print(f"PhidgetException {ex.code} ({ex.description}): {ex.details}")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Phidget Error", f"Unexpected error initializing Phidget: {e}", parent=self.parent_window)
            print(f"Unexpected error in initialize_phidget (ForceGaugeManager): {e}")

    def _onAttach(self, phidget):
        print("Phidget device attached (ForceGaugeManager).")
        # You might want to update a status label here if you have one for Phidget connection

    def _onDetach(self, phidget):
        print("Phidget device detached (ForceGaugeManager).")
        # Update status label, disable calibration buttons, etc.

    def _onError(self, phidget, errorCode, errorString):
        print(f"Phidget Error (ForceGaugeManager): {errorString} (Code: {errorCode})")
        # Potentially show a messagebox or update a status label

    def _onVoltageRatioChange(self, phidget, voltageRatio):
        try:
            current_force_text = "Force: --- N"
            if self.GAIN is not None and self.OFFSET is not None:
                force = (voltageRatio - self.OFFSET) * self.GAIN
                self.latest_calibrated_force = force # This is already being updated
                current_force_text = f"Force: {force:.6f} N"
                if self.force_status_label:
                    self.force_status_label.config(text=current_force_text)
                if self.large_force_readout_label:
                    self.large_force_readout_label.config(text=current_force_text)
                
                # Put calibrated force onto the queue for PositionLogger
                if self.output_force_queue:
                    try:
                        self.output_force_queue.put_nowait(("force_calibrated", force))
                    except queue.Full:
                        print("Force data queue for logger is full (ForceGaugeManager). Data point lost.")
            else:
                self.latest_calibrated_force = 0.0 # Ensure it's a float if not calibrated
                voltage_text = f"Voltage Ratio: {voltageRatio:.8f} (Calibration needed)"
                if self.force_status_label:
                    self.force_status_label.config(text=voltage_text)
                if self.large_force_readout_label:
                    self.large_force_readout_label.config(text="Force: --- N (Calibrate)")
        except Exception as e:
            print(f"Error in _onVoltageRatioChange (ForceGaugeManager): {e}")
            traceback.print_exc()
            self.latest_calibrated_force = 0.0 # Ensure it's a float on error

    def get_latest_calibrated_force(self):
        """Returns the latest calibrated force reading."""
        return self.latest_calibrated_force

    def get_force_N(self):
        """
        Returns the latest calibrated force reading in Newtons.
        Provides direct access to the latest calibrated force.
        """
        # self.latest_calibrated_force is initialized to 0.0 and updated with float values.
        return self.latest_calibrated_force

    def is_calibrated(self):
        """Returns true if the gauge has been calibrated at least once."""
        return self.calibrated_once

    def calibrate_force_gauge(self):
        try:
            print("Starting calibration (ForceGaugeManager)...")
            if not self.voltage_ratio_input or not self.voltage_ratio_input.getAttached():
                messagebox.showerror("Calibration Error", "Force sensor not attached.", parent=self.parent_window)
                return

            messagebox.showinfo("Calibration Step 1", "Please ensure the load cell is at zero force, then click OK.", parent=self.parent_window)
            time.sleep(0.5) # Allow sensor to stabilize if needed, though getVoltageRatio should be current
            zero_force_voltage_ratio = self.voltage_ratio_input.getVoltageRatio()
            self.OFFSET = zero_force_voltage_ratio
            print(f"Zero force voltage ratio (OFFSET): {self.OFFSET:.8f}")

            known_force_str = simpledialog.askstring("Calibration Step 2", "Enter the known force in Newtons (N):", parent=self.parent_window)
            if known_force_str is None: # User cancelled
                print("Calibration cancelled by user at known force input.")
                return 
            
            try:
                known_force = float(known_force_str)
            except ValueError:
                messagebox.showerror("Calibration Error", "Invalid force value entered. Please enter a number.", parent=self.parent_window)
                return

            messagebox.showinfo("Calibration Step 2", f"Please apply the known force of {known_force:.4f} N to the load cell, then click OK.", parent=self.parent_window)
            time.sleep(0.5) 
            known_force_voltage_ratio = self.voltage_ratio_input.getVoltageRatio()

            if abs(known_force_voltage_ratio - self.OFFSET) < 1e-9: # Check for significant change
                messagebox.showerror("Calibration Error", "Voltage ratio did not change significantly. Check applied force or sensor connection.", parent=self.parent_window)
                return

            self.GAIN = known_force / (known_force_voltage_ratio - self.OFFSET)
            print(f"Voltage ratio with known force: {known_force_voltage_ratio:.8f}")
            print(f"Calibration complete. GAIN: {self.GAIN:.4f}, OFFSET: {self.OFFSET:.8f}")

            if self.gain_label:
                self.gain_label.config(text=f"Gain: {self.GAIN:.4f}")
            if self.offset_label:
                self.offset_label.config(text=f"Offset: {self.OFFSET:.8f}")
            
            if self.GAIN is not None and self.OFFSET is not None:
                self.calibrated_once = True
                if self.sensor_window_ref:
                    self.sensor_window_ref.update_calibration_status_for_main_app(True)
                messagebox.showinfo("Calibration Complete", f"Calibration successful.\nGain: {self.GAIN:.4f}\nOffset: {self.OFFSET:.8f}", parent=self.parent_window)
            else:
                if self.sensor_window_ref:
                    self.sensor_window_ref.update_calibration_status_for_main_app(False)

        except PhidgetException as pe:
            print(f"Phidget error during calibration (ForceGaugeManager): {pe}")
            messagebox.showerror("Calibration Error", f"Phidget error: {pe.description}", parent=self.parent_window)
        except Exception as e:
            print(f"Error during calibration (ForceGaugeManager): {e}")
            messagebox.showerror("Calibration Error", f"An error occurred during calibration: {e}", parent=self.parent_window)
            traceback.print_exc()

    def quick_calibrate_force_gauge(self):
        default_gain = 10118.0739
        default_offset = -0.00000914
        
        self.GAIN = default_gain
        self.OFFSET = default_offset
        
        if self.gain_label:
            self.gain_label.config(text=f"Gain: {self.GAIN:.4f}")
        if self.offset_label:
            self.offset_label.config(text=f"Offset: {self.OFFSET:.8f}")
        
        self.calibrated_once = True
        if self.sensor_window_ref:
            self.sensor_window_ref.update_calibration_status_for_main_app(True)
        
        print(f"Quick calibration applied (ForceGaugeManager). GAIN: {self.GAIN:.4f}, OFFSET: {self.OFFSET:.8f}")
        messagebox.showinfo("Quick Calibration", "Default calibration values applied.", parent=self.parent_window)

    def stop_force_reading_thread(self):
        """Stops the force reading by closing the Phidget device."""
        print("ForceGaugeManager: stop_force_reading_thread called, invoking close_phidget.")
        self.close_phidget()

    def close_phidget(self):
        print("Closing Phidget connection (ForceGaugeManager)...")
        if self.voltage_ratio_input and self.voltage_ratio_input.getAttached():
            try:
                self.voltage_ratio_input.close()
                print("Phidget connection closed successfully (ForceGaugeManager).")
            except PhidgetException as ex:
                print(f"PhidgetException during close: {ex.description}")
        elif self.voltage_ratio_input:
             print("Phidget was initialized but not attached or already closed.")
        else:
            print("No Phidget to close.")