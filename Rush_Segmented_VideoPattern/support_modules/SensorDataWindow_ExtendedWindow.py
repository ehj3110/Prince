from tkinter import *
from tkinter import messagebox, font as tkFont
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import queue
import threading
import time
import traceback
import os
import sys
from pathlib import Path
import tkinter as tk

# Add current directory to path for local imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from zaber_motion import Units
from PositionLogger import PositionLogger
try:
    from ForceGaugeManager import ForceGaugeManager
except Exception:
    ForceGaugeManager = None


class SensorDataWindow:
    MAX_PLOT_POINTS = 20000  # Maximum number of data points to keep for plotting

    def __init__(self, master_window, zaber_axis_ref, main_app_status_callback, prince_main_app_ref):
        self.master = master_window
        self.zaber_axis = zaber_axis_ref
        self.update_main_status = main_app_status_callback
        self.prince_main_app_ref = prince_main_app_ref
        self.force_gauge_is_calibrated = False

        self.force_data_queue_for_logger = queue.Queue()

        self.sensor_window = Toplevel(master_window)
        self.sensor_window.title("Sensor Data")
        self.sensor_window.geometry("800x900")

        control_box_font = tkFont.Font(family="Helvetica", size=11)
        control_box_title_font = tkFont.Font(family="Helvetica", size=11, weight="bold")
        control_box_borderwidth = 3

        top_banner_frame = Frame(self.sensor_window)
        top_banner_frame.pack(side=TOP, fill=X, padx=10, pady=(5, 0))

        title_font = tkFont.Font(family="Helvetica", size=20, weight="bold")
        self.lbl_title = Label(top_banner_frame, text="Sensor Readout Panel", font=title_font)
        self.lbl_title.pack(side=LEFT, padx=(0, 10))

        credit_text = '''
Professor Cheng Sun, c-sun@northwestern.edu
Evan Jones, evanjones2026@u.northwestern.edu
'''
        credit_font = tkFont.Font(family="Helvetica", size=7)
        self.lbl_credit = Label(top_banner_frame, text=credit_text, font=credit_font, justify=LEFT)
        self.lbl_credit.pack(side=RIGHT, padx=(10, 0))

        outer_readout_frame = Frame(self.sensor_window)
        outer_readout_frame.pack(side=TOP, fill=X, padx=10, pady=(15, 5))

        readout_content_frame = Frame(outer_readout_frame)
        readout_content_frame.pack()

        readout_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.lbl_current_position = Label(readout_content_frame, text="Position: --- mm", font=readout_font)
        self.lbl_current_position.pack(side=LEFT, padx=(0, 20))

        self.lbl_current_force = Label(readout_content_frame, text="Force: --- N", font=readout_font)
        self.lbl_current_force.pack(side=LEFT, padx=(20, 0))

        self._perf_status_var = StringVar(value="Perf: idle")
        self.lbl_perf_status = Label(outer_readout_frame, textvariable=self._perf_status_var, anchor=W, font=control_box_font)
        self.lbl_perf_status.pack(side=TOP, fill=X, pady=(5, 0))

        self.figure = Figure(figsize=(6, 3), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax2 = self.ax.twinx()
        self.ax.set_facecolor("white")
        self.ax2.set_facecolor("white")

        self.ax.set_title("Linear Stage Data")
        self.ax.set_xlabel("Elapsed Time (s)")
        self.ax.set_ylabel("Position (mm)", color='b')
        self.ax2.set_ylabel("Force (N)", color='r')

        self.line_position, = self.ax.plot([], [], 'b-', label='Position (mm)')
        self.line_force, = self.ax2.plot([], [], 'r-', label='Force (N)')
        lines = [self.line_position, self.line_force]
        self.ax.legend(lines, [l.get_label() for l in lines], loc='upper left')

        self.ax.tick_params(axis='y', labelcolor='b')
        self.ax2.tick_params(axis='y', labelcolor='r')

        self.canvas = FigureCanvasTkAgg(self.figure, self.sensor_window)
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True, padx=10, pady=(5, 0))
        self.figure.tight_layout()

        controls_main_frame = Frame(self.sensor_window, relief=GROOVE, borderwidth=control_box_borderwidth)
        controls_main_frame.pack(side=TOP, pady=(5, 10), padx=10, fill=X)

        buttons_and_sampling_frame = Frame(controls_main_frame)
        buttons_and_sampling_frame.pack(side=TOP, fill=X, pady=(4, 5), padx=5)
        Label(buttons_and_sampling_frame, text="Sampling (ms):", font=control_box_font).pack(side=LEFT, padx=(0, 5))
        self.sampling_rate_entry = Entry(buttons_and_sampling_frame, width=6, font=control_box_font)
        self.sampling_rate_entry.insert(0, "50")
        self.sampling_rate_entry.pack(side=LEFT, padx=(0, 10))

        self.b_clear_plot = Button(buttons_and_sampling_frame, text="Clear Plot", command=self.clear_plot_data, font=control_box_font)
        self.b_clear_plot.pack(side=LEFT, padx=5)
        self.b_live_readout = Button(buttons_and_sampling_frame, text="Start Live Readout", command=self.toggle_live_readout, font=control_box_font)
        self.b_live_readout.pack(side=LEFT, padx=5)

        force_gauge_main_frame = Frame(self.sensor_window, relief=GROOVE, borderwidth=control_box_borderwidth)
        force_gauge_main_frame.pack(side=TOP, pady=(0, 10), padx=10, fill=X)

        Label(force_gauge_main_frame, text="Force Gauge Information", font=control_box_title_font).pack(anchor=W, padx=5, pady=(5, 2))

        force_controls_row1 = Frame(force_gauge_main_frame)
        force_controls_row1.pack(fill=X, padx=5, pady=2)

        self.b_quick_calibrate = Button(force_controls_row1, text="Quick Calibrate", command=lambda: self.force_gauge_manager.quick_calibrate_force_gauge(), font=control_box_font)
        self.b_quick_calibrate.pack(side=LEFT, padx=(0, 5))

        self.b_calibrate_force_gauge = Button(force_controls_row1, text="Calibrate Force Gauge", command=lambda: self.force_gauge_manager.calibrate_force_gauge(), font=control_box_font)
        self.b_calibrate_force_gauge.pack(side=LEFT, padx=5)

        self.b_tare_force_gauge = Button(force_controls_row1, text="Tare", command=self.tare_force_gauge, font=control_box_font)
        self.b_tare_force_gauge.pack(side=LEFT, padx=5)

        self.b_save_calibration = Button(force_controls_row1, text="Save Calibration", command=self.save_force_gauge_calibration, font=control_box_font)
        self.b_save_calibration.pack(side=LEFT, padx=5)

        self.lbl_force_gauge_status = Label(force_controls_row1, text="Force: N/A", font=control_box_font, anchor=W)
        self.lbl_force_gauge_status.pack(side=LEFT, padx=5)

        force_info_row2 = Frame(force_gauge_main_frame)
        force_info_row2.pack(fill=X, padx=5, pady=2)

        self.lbl_gain = Label(force_info_row2, text="Gain: N/A", font=control_box_font, anchor=W)
        self.lbl_gain.pack(side=LEFT, padx=(0, 10))

        self.lbl_offset = Label(force_info_row2, text="Offset: N/A", font=control_box_font, anchor=W)
        self.lbl_offset.pack(side=LEFT, padx=10)

        if ForceGaugeManager is None:
            raise ImportError("ForceGaugeManager could not be imported. Install dependencies or inject a test manager.")

        self.force_gauge_manager = ForceGaugeManager(
            gain_label=self.lbl_gain,
            offset_label=self.lbl_offset,
            force_status_label=self.lbl_force_gauge_status,
            large_force_readout_label=self.lbl_current_force,
            output_force_queue=self.force_data_queue_for_logger,
            parent_window=self.sensor_window,
            sensor_window_ref=self,
        )

        self.plot_data_x = []
        self.plot_data_y_position = []
        self.plot_data_y_force = []
        self.is_live_readout_enabled = False
        self.plot_start_time = None
        self.last_y_rescale_time = 0
        self._last_plot_draw_time = 0
        self._min_plot_draw_interval_s = 0.08
        self._last_queue_warning_time = 0
        self._perf_last_report_time = time.time()
        self._perf_frame_count = 0
        self._perf_target_report_interval_s = 0.5

        self.position_plot_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.position_logger = None

        self._shading = []

        self.persistent_readout_active = False
        self.persistent_readout_update_interval_ms = 150
        self._latest_position_mm = None
        self._position_poll_interval_s = 0.08
        self._position_poll_stop_event = threading.Event()
        self._position_poll_thread = None

        self.sensor_window.protocol("WM_DELETE_WINDOW", self.on_sensor_window_close)

        self._start_persistent_readouts()

    def on_sensor_window_close(self):
        self.update_main_status("Sensor data window closed by user.")
        if self.is_live_readout_enabled:
            self.stop_live_readout()

        if self.force_gauge_manager:
            self.force_gauge_manager.stop_force_reading_thread()

        if self.persistent_readout_active:
            self._stop_persistent_readouts()

        if self.sensor_window.winfo_exists():
            self.sensor_window.destroy()

        if self.prince_main_app_ref:
            self.prince_main_app_ref.sensor_data_window_instance = None
            if hasattr(self.prince_main_app_ref, 'update_auto_home_button_state'):
                self.prince_main_app_ref.update_auto_home_button_state()

    def _start_persistent_readouts(self):
        if not self.persistent_readout_active:
            self.persistent_readout_active = True
            self._position_poll_stop_event.clear()
            if self._position_poll_thread is None or not self._position_poll_thread.is_alive():
                self._position_poll_thread = threading.Thread(target=self._position_poll_loop, daemon=True)
                self._position_poll_thread.start()
            self._update_persistent_readouts()

    def _position_poll_loop(self):
        while not self._position_poll_stop_event.is_set():
            try:
                if self.zaber_axis:
                    self._latest_position_mm = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
            except Exception as e:
                print(f"Error polling position in background: {e}")
            self._position_poll_stop_event.wait(self._position_poll_interval_s)

    def _update_persistent_readouts(self):
        if not self.persistent_readout_active or not self.sensor_window.winfo_exists():
            return

        try:
            current_pos_mm = self._latest_position_mm
            if isinstance(current_pos_mm, (int, float)):
                self.lbl_current_position.config(text=f"Position: {current_pos_mm:.4f} mm")
        except Exception as e:
            print(f"Error in _update_persistent_readouts: {e}")

        if self.persistent_readout_active and self.sensor_window.winfo_exists():
            self.sensor_window.after(self.persistent_readout_update_interval_ms, self._update_persistent_readouts)

    def _stop_persistent_readouts(self):
        self.persistent_readout_active = False
        self._position_poll_stop_event.set()
        if self._position_poll_thread and self._position_poll_thread.is_alive():
            self._position_poll_thread.join(timeout=0.5)
        self.update_main_status("Persistent readouts stopped.")

    def clear_plot_data(self):
        self.plot_data_x.clear()
        self.plot_data_y_position.clear()
        self.plot_data_y_force.clear()

        while not self.force_data_queue_for_logger.empty():
            try:
                self.force_data_queue_for_logger.get_nowait()
            except queue.Empty:
                break

        while not self.position_plot_queue.empty():
            try:
                self.position_plot_queue.get_nowait()
            except queue.Empty:
                break

        if not self.is_live_readout_enabled:
            self.plot_start_time = None

        self.line_position.set_data([], [])
        self.line_force.set_data([], [])

        self.ax.relim()
        self.ax.autoscale_view(True, True, True)
        self.ax2.relim()
        self.ax2.autoscale_view(True, True, True)

        self.canvas.draw()
        self.update_main_status("Plot data cleared.")

    def update_calibration_status_for_main_app(self, status):
        self.force_gauge_is_calibrated = status
        if self.prince_main_app_ref and hasattr(self.prince_main_app_ref, 'update_auto_home_button_state'):
            self.prince_main_app_ref.update_auto_home_button_state()

    def is_force_gauge_calibrated_internally(self):
        return self.force_gauge_is_calibrated

    def toggle_live_readout(self):
        if self.is_live_readout_enabled:
            self.stop_live_readout()
        else:
            self.start_live_readout()

    def _get_sampling_rate_ms(self, normalize_entry=False):
        sampling_rate_raw = self.sampling_rate_entry.get()
        sampling_rate_str = sampling_rate_raw.strip()

        if not sampling_rate_str:
            raise ValueError("Sampling rate is empty")

        sampling_rate = int(sampling_rate_str)
        if sampling_rate <= 0:
            raise ValueError("Sampling rate must be positive")

        if normalize_entry and sampling_rate_raw != sampling_rate_str:
            self.sampling_rate_entry.delete(0, tk.END)
            self.sampling_rate_entry.insert(0, sampling_rate_str)

        return sampling_rate

    def start_live_readout(self):
        try:
            self.last_y_rescale_time = time.time()

            self.plot_data_x.clear()
            self.plot_data_y_position.clear()
            self.plot_data_y_force.clear()
            self.plot_start_time = time.time()

            try:
                sampling_rate = self._get_sampling_rate_ms(normalize_entry=True)
            except ValueError:
                messagebox.showerror("Error", "Sampling rate must be a positive integer.", parent=self.sensor_window)
                return

            if self.force_gauge_manager:
                phidget_interval = sampling_rate
                if self.force_gauge_manager.set_data_interval(phidget_interval):
                    print(f"Force gauge data interval synchronized to {phidget_interval}ms")
                else:
                    print("Warning: Could not synchronize force gauge data interval")

            self.stop_event.clear()
            self.position_logger = PositionLogger(
                self.zaber_axis,
                self.stop_event,
                position_plot_queue=self.position_plot_queue,
                force_data_queue_ref=self.force_data_queue_for_logger,
                log_interval_ms=sampling_rate,
                csv_logging_initially_enabled=False,
            )

            self.position_logger.start()
            self.is_live_readout_enabled = True
            self.b_live_readout.config(text="Stop Live Readout")
            self.update_plot()
        except Exception as e:
            print(f"Error starting live readout: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Could not start live readout: {e}", parent=self.sensor_window)
            self.is_live_readout_enabled = False
            self.b_live_readout.config(text="Start Live Readout")

    def stop_live_readout(self):
        self.is_live_readout_enabled = False
        if self.position_logger and self.position_logger.is_alive():
            self.stop_event.set()
            self.position_logger.join(timeout=2.0)
            if self.position_logger.is_alive():
                print("Warning: PositionLogger thread did not terminate in time.")
        self.b_live_readout.config(text="Start Live Readout")

        while not self.position_plot_queue.empty():
            try:
                self.position_plot_queue.get_nowait()
            except queue.Empty:
                break
        print("Live readout stopped.")

    def update_plot(self):
        plot_loop_start = time.perf_counter()
        try:
            new_data_processed = False
            rendered_points = 0

            max_queue_items_per_cycle = 350
            items_processed = 0

            queue_size = self.position_plot_queue.qsize()
            if queue_size > 1000:
                now = time.time()
                if now - self._last_queue_warning_time > 1.0:
                    print(f"Warning: Position plot queue is large ({queue_size} items). GUI may slow down.")
                    self._last_queue_warning_time = now
                if queue_size > 5000:
                    drained = 0
                    while not self.position_plot_queue.empty() and drained < queue_size - 1000:
                        self.position_plot_queue.get_nowait()
                        drained += 1
                    if now - self._last_queue_warning_time > 1.0:
                        print(f"Drained {drained} old data points from queue to prevent freeze.")
                        self._last_queue_warning_time = now

            while not self.position_plot_queue.empty() and items_processed < max_queue_items_per_cycle:
                time_stamp, position, force = self.position_plot_queue.get_nowait()
                new_data_processed = True
                items_processed += 1

                if self.plot_start_time is None:
                    self.plot_start_time = time_stamp

                elapsed_time = time_stamp - self.plot_start_time
                self.plot_data_x.append(elapsed_time)
                self.plot_data_y_position.append(position if position is not None else float('nan'))
                self.plot_data_y_force.append(force if force is not None else float('nan'))

            if new_data_processed:
                if len(self.plot_data_x) > self.MAX_PLOT_POINTS:
                    self.plot_data_x = self.plot_data_x[-self.MAX_PLOT_POINTS:]
                if len(self.plot_data_y_position) > self.MAX_PLOT_POINTS:
                    self.plot_data_y_position = self.plot_data_y_position[-self.MAX_PLOT_POINTS:]
                if len(self.plot_data_y_force) > self.MAX_PLOT_POINTS:
                    self.plot_data_y_force = self.plot_data_y_force[-self.MAX_PLOT_POINTS:]

                min_len = min(len(self.plot_data_x), len(self.plot_data_y_position), len(self.plot_data_y_force))
                current_plot_x = self.plot_data_x[-min_len:] if min_len > 0 else []
                current_plot_y_pos = self.plot_data_y_position[-min_len:] if min_len > 0 else []
                current_plot_y_force = self.plot_data_y_force[-min_len:] if min_len > 0 else []

                # Decimate older points more aggressively while keeping recent detail.
                if min_len > 4000:
                    keep_tail = 1500
                    head_end = max(0, min_len - keep_tail)
                    if head_end > 0:
                        stride = max(2, head_end // 2200)
                        current_plot_x = current_plot_x[:head_end:stride] + current_plot_x[head_end:]
                        current_plot_y_pos = current_plot_y_pos[:head_end:stride] + current_plot_y_pos[head_end:]
                        current_plot_y_force = current_plot_y_force[:head_end:stride] + current_plot_y_force[head_end:]

                rendered_points = len(current_plot_x)

                self.line_position.set_data(current_plot_x, current_plot_y_pos)
                self.line_force.set_data(current_plot_x, current_plot_y_force)

                self.ax.relim()
                self.ax2.relim()

                current_time_for_rescale = time.time()
                if current_time_for_rescale - self.last_y_rescale_time >= 0.5:
                    self.ax.autoscale_view(True, True, True)
                    self.ax2.autoscale_view(True, True, True)
                    self.last_y_rescale_time = current_time_for_rescale
                else:
                    self.ax.autoscale_view(True, False, False)
                    self.ax2.autoscale_view(True, False, False)

                for coll in self._shading:
                    coll.remove()
                self._shading.clear()

                draw_due = (current_time_for_rescale - self._last_plot_draw_time) >= self._min_plot_draw_interval_s
                if draw_due or queue_size > 1000:
                    self.canvas.draw_idle()
                    self._last_plot_draw_time = current_time_for_rescale

                self._perf_frame_count += 1
                report_elapsed = current_time_for_rescale - self._perf_last_report_time
                if report_elapsed >= self._perf_target_report_interval_s:
                    fps = self._perf_frame_count / report_elapsed if report_elapsed > 0 else 0.0
                    loop_ms = (time.perf_counter() - plot_loop_start) * 1000.0
                    if hasattr(self, 'lbl_perf_status') and self.lbl_perf_status.winfo_exists():
                        self._perf_status_var.set(
                            f"Perf: q={queue_size} proc={items_processed} render={rendered_points} loop={loop_ms:.1f}ms fps={fps:.1f}"
                        )
                    self._perf_last_report_time = current_time_for_rescale
                    self._perf_frame_count = 0

        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error updating plot: {e}")
            traceback.print_exc()
        finally:
            if self.is_live_readout_enabled and self.sensor_window.winfo_exists():
                try:
                    sampling_rate = self._get_sampling_rate_ms()
                except ValueError:
                    sampling_rate = 10
                self.sensor_window.after(max(30, sampling_rate // 3), self.update_plot)

    # Compatibility stubs for stripped logging features.
    def configure_automated_layer_logging(self, *args, **kwargs):
        self.update_main_status("Automated layer logging is disabled in SensorDataWindow_ExtendedWindow.", warning=True)
        return False

    def configure_automated_logging(self, *args, **kwargs):
        self.update_main_status("Automated logging is disabled in SensorDataWindow_ExtendedWindow.", warning=True)
        return False

    def update_auto_logger_current_layer(self, *args, **kwargs):
        return False

    def stop_and_save_automated_logs(self):
        return False

    def tare_force_gauge(self):
        try:
            if not self.force_gauge_manager or not self.force_gauge_manager.is_calibrated():
                messagebox.showerror("Error", "Force gauge must be calibrated before taring.", parent=self.sensor_window)
                return

            if not self.force_gauge_manager.voltage_ratio_input or not self.force_gauge_manager.voltage_ratio_input.getAttached():
                messagebox.showerror("Error", "Force gauge is not connected.", parent=self.sensor_window)
                return

            current_voltage_ratio = self.force_gauge_manager.voltage_ratio_input.getVoltageRatio()
            self.force_gauge_manager.OFFSET = current_voltage_ratio

            if hasattr(self, 'lbl_offset'):
                self.lbl_offset.config(text=f"Offset: {self.force_gauge_manager.OFFSET:.8f}")

            messagebox.showinfo("Tare Complete", f"Force gauge tared successfully.\nNew offset: {self.force_gauge_manager.OFFSET:.8f}", parent=self.sensor_window)
            print(f"Force gauge tared - New offset: {self.force_gauge_manager.OFFSET:.8f}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to tare force gauge: {e}", parent=self.sensor_window)
            print(f"Error during tare operation: {e}")
            traceback.print_exc()

    def save_force_gauge_calibration(self):
        try:
            if not self.force_gauge_manager or not self.force_gauge_manager.is_calibrated():
                messagebox.showerror("Error", "Force gauge must be calibrated before saving.", parent=self.sensor_window)
                return

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"force_gauge_calibration_{timestamp}.txt"

            current_dir = os.getcwd()
            file_path = os.path.join(current_dir, filename)

            with open(file_path, 'w') as f:
                f.write("# Force Gauge Calibration Data\n")
                f.write(f"# Saved on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"GAIN={self.force_gauge_manager.GAIN}\n")
                f.write(f"OFFSET={self.force_gauge_manager.OFFSET}\n")

            messagebox.showinfo("Calibration Saved", f"Calibration saved to:\n{file_path}", parent=self.sensor_window)
            print(f"Calibration saved to: {file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save calibration: {e}", parent=self.sensor_window)
            print(f"Error saving calibration: {e}")
