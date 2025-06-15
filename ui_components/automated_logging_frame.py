from tkinter import Frame, Label, Entry, Button, Checkbutton
from tkinter import ttk, BooleanVar, StringVar, W, X, LEFT, TOP, END

class AutomatedLoggingFrame(ttk.LabelFrame):
    def __init__(self, master, sensor_data_window_ref, control_box_font):
        super().__init__(master, text="Automated Layer Logging Control", padding=(10, 5))
        self.sensor_data_window = sensor_data_window_ref # Reference to the main SensorDataWindow
        self.control_box_font = control_box_font

        # Row 0 (within frame_auto_log): Enable, Layer Inputs, Add Button
        auto_log_row0 = Frame(self)
        auto_log_row0.pack(side=TOP, fill=X, pady=2)

        self.auto_log_enabled_var = BooleanVar(value=False)
        self.cb_auto_log_enabled = Checkbutton(
            auto_log_row0, text="Enable Automated Logging",
            variable=self.auto_log_enabled_var,
            font=self.control_box_font,
            command=self._ui_on_auto_log_enable_change
        )
        self.cb_auto_log_enabled.pack(side=LEFT, padx=(0, 10))
        
        self.lbl_current_window_start = Label(auto_log_row0, text="Start L:", font=self.control_box_font)
        self.lbl_current_window_start.pack(side=LEFT, padx=(5, 0))
        self.current_window_start_var = StringVar()
        self.t_current_window_start = Entry(auto_log_row0, textvariable=self.current_window_start_var, width=5, font=self.control_box_font)
        self.t_current_window_start.pack(side=LEFT, padx=(2, 5))

        self.lbl_current_window_end = Label(auto_log_row0, text="End L:", font=self.control_box_font)
        self.lbl_current_window_end.pack(side=LEFT, padx=(5, 0))
        self.current_window_end_var = StringVar()
        self.t_current_window_end = Entry(auto_log_row0, textvariable=self.current_window_end_var, width=5, font=self.control_box_font)
        self.t_current_window_end.pack(side=LEFT, padx=(2, 5))

        self.btn_add_window_to_file = Button(
            auto_log_row0, text="Add Window",
            command=self._ui_add_window_to_file,
            font=self.control_box_font
        )
        self.btn_add_window_to_file.pack(side=LEFT, padx=(10, 0))
        
        # Row 1 (within frame_auto_log): File display
        auto_log_row1 = Frame(self)
        auto_log_row1.pack(side=TOP, fill=X, pady=(5, 2))

        self.active_logging_windows_filepath_var = StringVar(value="No windows file active.")
        self.lbl_active_logging_windows_file = Label(
            auto_log_row1, textvariable=self.active_logging_windows_filepath_var,
            width=70, relief="sunken", anchor=W, font=self.control_box_font
        )
        self.lbl_active_logging_windows_file.pack(side=LEFT, fill=X, expand=True)

    def _ui_on_auto_log_enable_change(self):
        is_enabled = self.auto_log_enabled_var.get()
        self.sensor_data_window.handle_auto_log_enable_change(is_enabled)

    def _ui_add_window_to_file(self):
        start_layer_str = self.current_window_start_var.get()
        end_layer_str = self.current_window_end_var.get()
        self.sensor_data_window.handle_add_logging_window(start_layer_str, end_layer_str)

    # --- Methods to be called by SensorDataWindow to update this frame's UI ---
    def set_auto_log_enabled_checkbox(self, enabled_state):
        self.auto_log_enabled_var.set(enabled_state)

    def update_logging_windows_file_display(self, display_text):
        self.active_logging_windows_filepath_var.set(display_text)

    def clear_layer_input_fields(self):
        self.current_window_start_var.set("")
        self.current_window_end_var.set("")