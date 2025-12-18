# Troubleshooting Ideas

This document tracks issues, potential causes, and solutions for the Prince Segmented 3D printer software.

## Issue 1: Intermittent Stage Fault (FS - Stalled Stage) & GUI Sluggishness

**Observed Behavior:**
- The Zaber linear stage faults intermittently with an `FS` (stalled stage) error.
- The fault seems to occur after the retraction/peel sequence in "stepped" mode, but before the layer pause.
- The application's GUI becomes progressively more sluggish and unresponsive the longer the `SensorDataWindow` is open and plotting/logging data.
- The issue began after updates related to the adhesion metrics analysis system.

### Possible Causes

1.  **Memory Leak in Manual Logger:** The primary suspect is a memory leak related to the "Record Work of Adhesion" feature. When this is enabled, it creates a `PeakForceLogger` instance for manual logging. It appears this logger's internal data buffers are appended to continuously without being cleared, leading to unbounded memory growth.
2.  **GUI Thread Starvation:** As the logger's data buffers grow, the main application thread (which also runs the GUI) spends an increasing amount of time processing this data. This starves the GUI of processing time, causing the observed sluggishness.
3.  **Race Condition / Timeout:** The GUI thread starvation is the likely direct cause of the stage fault. Because the main thread is too busy, it may fail to communicate with the Zaber stage controller in a timely manner. This can lead to timeouts or attempts to send a new command while the device is in an indeterminate state, resulting in a stall (`FS`) fault.

### Possible Solutions

1.  **Fix the Manual Logger Lifecycle:** The most direct solution is to fix the memory leak. This involves modifying `support_modules/SensorDataWindow.py`:
    -   In the `on_record_work_checkbox` method, when the checkbox is ticked to *start* recording, explicitly call `start_monitoring_for_layer()` on the `peak_force_logger` instance.
    -   This will ensure its internal data buffers are cleared at the beginning of the recording session, preventing them from growing indefinitely.
    -   The existing logic for *stopping* the logger when the box is unchecked will then function correctly.

2.  **Add a Failsafe Delay:** A less direct, but potentially helpful, secondary solution would be to add a small, explicit `time.sleep(0.1)` after the final retraction move in `Prince_Segmented.py`. This would give the stage an extra moment to settle before the logging-related methods are called, making the system slightly more robust against timing-related race conditions.

### Overlap Between Issues

The GUI sluggishness and the intermittent stage fault are not two separate issues, but rather a cause-and-effect relationship. The performance degradation from the logging memory leak is the root cause, and the random stage fault is a critical symptom of the system becoming unstable as a result.

Resolving the memory leak (Possible Solution 1) is the highest priority and will almost certainly resolve the stage fault issue as a consequence.

## Proposed Efficiency Upgrade: Asynchronous Analysis

To permanently resolve the performance issues and system instability, the real-time adhesion analysis should be moved off the main application thread.

### Problem

Currently, all adhesion calculations are performed sequentially in the main thread at the end of each layer. This blocks all other operations, including the GUI and communication with the printer hardware, causing the application to freeze.

### Solution: Background Worker Thread

The proposed solution is to refactor the `PeakForceLogger` to delegate its analysis to a dedicated background thread.

#### Implementation Plan

1.  **Modify `support_modules/PeakForceLogger.py`:**
    *   **`__init__`:**
        *   A `queue.Queue` will be added to hold analysis jobs.
        *   A new `threading.Thread` will be created and started. It will be configured as a `daemon` thread so it closes automatically with the application. This thread will run a new `_analysis_worker` method.
    *   **`_analysis_worker` method (New):**
        *   This method will run an infinite loop, waiting for data to appear on the analysis queue.
        *   When a job is received, it will unpack the data (layer number, raw sensor arrays) and call the appropriate internal analysis method (`_analyze_with_corrected_calculator`).
        *   The analysis and CSV writing will happen entirely within this thread.
    *   **`stop_monitoring_and_log_peak` method (Refactored):**
        *   This method will no longer perform any calculations.
        *   Its sole responsibility will be to package the collected `_data_buffer` and the relevant metadata (layer number, file path) into a dictionary and `put` it onto the analysis queue.
        *   This makes the method extremely fast, preventing it from blocking the main print loop.
    *   **`close` method (New):**
        *   A method will be added to allow for a graceful shutdown. It will place a special `None` value onto the queue, which will act as a signal for the `_analysis_worker` to break its loop and exit.

2.  **Modify `support_modules/SensorDataWindow.py`:**
    *   **`on_sensor_window_close` method:**
        *   This method will be updated to call the new `close()` method on any active `PeakForceLogger` instances (`automated_peak_force_logger` and the manual `peak_force_logger`). This ensures the background threads are properly terminated when the window is closed.

### Benefits

*   **Decoupling:** The computationally intensive analysis is completely decoupled from the real-time print control loop.
*   **Responsiveness:** The GUI will remain smooth and responsive, as the main thread is no longer being blocked by calculations.
*   **Stability:** The risk of hardware timeouts and faults due to a busy main thread will be virtually eliminated.
*   **Maintainability:** This change reinforces the "single source of truth" principle by keeping the analysis logic in `adhesion_metrics_calculator.py` and simply changing *how* it is called by the `PeakForceLogger`.