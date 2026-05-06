"""
Lifecycle logger for Rush shutdown instrumentation.

Captures monotonic timestamps, thread IDs, command order, and outcomes during
stop/close/cleanup sequences to diagnose freeze and power-cycle issues.
"""

import threading
import time
import json
import traceback
from pathlib import Path
from datetime import datetime
from collections import deque


class LifecycleLogger:
    """Records shutdown events with high-precision timing and context."""
    
    def __init__(self, max_events=500, log_dir=None):
        """Initialize logger.
        
        Args:
            max_events: Maximum events to retain in memory (roll buffer).
            log_dir: Directory to write session logs to (default: Rush_Segmented_VideoPattern/logs).
        """
        self.lock = threading.Lock()
        self.events = deque(maxlen=max_events)
        self.start_time = time.monotonic()
        self.session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
        
        if log_dir is None:
            log_dir = Path(__file__).parent / "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.cleanup_call_count = 0
        self.gui_close_initiated = False
        self.print_thread_joined = False
        
        self.log_event("logger_start", {
            "session_id": self.session_id,
            "log_dir": str(self.log_dir)
        })
    
    def log_event(self, event_type, details=None, level="INFO"):
        """Record an event.
        
        Args:
            event_type: Short event name (e.g., "dmp_stopsequence", "gui_close_start").
            details: Dict of event-specific data.
            level: Log level (INFO, WARNING, ERROR).
        """
        with self.lock:
            elapsed = time.monotonic() - self.start_time
            event = {
                "timestamp_elapsed_sec": round(elapsed, 4),
                "timestamp_iso": datetime.now().isoformat(),
                "event_type": event_type,
                "thread_id": threading.current_thread().ident,
                "thread_name": threading.current_thread().name,
                "level": level,
                "details": details or {}
            }
            self.events.append(event)
    
    def log_dlp_command(self, command_name, result="pending", timeout_sec=None, exception=None):
        """Log a DLP command attempt.
        
        Args:
            command_name: DLP method name (e.g., "stopsequence", "power", "standby").
            result: "success", "timeout", "exception", "pending".
            timeout_sec: Timeout value used (for debugging).
            exception: Exception object if result=="exception".
        """
        details = {
            "command": command_name,
            "result": result,
        }
        if timeout_sec is not None:
            details["timeout_sec"] = timeout_sec
        if exception is not None:
            details["exception_type"] = type(exception).__name__
            details["exception_msg"] = str(exception)
        
        level = "ERROR" if result in ("timeout", "exception") else "INFO"
        self.log_event(f"dlp_{command_name}", details, level=level)
    
    def log_stage_command(self, command_name, result="pending", timeout_sec=None, exception=None):
        """Log a stage/axis command attempt."""
        details = {
            "command": command_name,
            "result": result,
        }
        if timeout_sec is not None:
            details["timeout_sec"] = timeout_sec
        if exception is not None:
            details["exception_type"] = type(exception).__name__
            details["exception_msg"] = str(exception)
        
        level = "ERROR" if result in ("timeout", "exception") else "INFO"
        self.log_event(f"stage_{command_name}", details, level=level)
    
    def log_cleanup_start(self, caller_source):
        """Log start of DLP cleanup.
        
        Args:
            caller_source: "stop_button", "print_finally", "on_closing".
        """
        with self.lock:
            self.cleanup_call_count += 1
            call_num = self.cleanup_call_count
        
        self.log_event("cleanup_dlp_start", {
            "caller": caller_source,
            "call_number": call_num
        })
    
    def log_cleanup_end(self, caller_source, success=True, exception=None):
        """Log end of DLP cleanup."""
        if exception:
            self.log_event("cleanup_dlp_end", {
                "caller": caller_source,
                "success": False,
                "exception_type": type(exception).__name__,
                "exception_msg": str(exception),
                "traceback": traceback.format_exc()
            }, level="ERROR")
        else:
            self.log_event("cleanup_dlp_end", {
                "caller": caller_source,
                "success": success
            })
    
    def log_gui_close_start(self):
        """Log start of GUI close sequence."""
        with self.lock:
            self.gui_close_initiated = True
        self.log_event("gui_close_start")
    
    def log_print_thread_join_attempt(self, timeout_sec):
        """Log attempt to join print thread."""
        self.log_event("print_thread_join_attempt", {
            "timeout_sec": timeout_sec
        })
    
    def log_print_thread_join_result(self, success, timeout_sec):
        """Log result of print thread join."""
        with self.lock:
            self.print_thread_joined = success
        
        level = "WARNING" if not success else "INFO"
        self.log_event("print_thread_join_result", {
            "success": success,
            "timeout_sec": timeout_sec
        }, level=level)
    
    def log_callback_guard(self, callback_name, should_skip):
        """Log callback guard decision (whether to skip due to closed window)."""
        if should_skip:
            self.log_event("callback_skipped", {
                "callback": callback_name,
                "reason": "gui_closed"
            }, level="WARNING")
    
    def log_duplicate_cleanup_warning(self):
        """Log warning about duplicate cleanup calls."""
        self.log_event("duplicate_cleanup_detected", {
            "message": "cleanup_dlp called multiple times in close sequence"
        }, level="WARNING")
    
    def export_session_log(self):
        """Write all events to disk and return file path."""
        with self.lock:
            events_copy = list(self.events)
        
        filename = f"lifecycle_{self.session_id}.json"
        filepath = self.log_dir / filename
        
        try:
            with open(filepath, "w") as f:
                json.dump({
                    "session_id": self.session_id,
                    "export_time": datetime.now().isoformat(),
                    "total_events": len(events_copy),
                    "events": events_copy
                }, f, indent=2, default=str)
            return filepath
        except Exception as e:
            print(f"[LifecycleLogger] Failed to export log: {e}")
            return None
    
    def get_summary(self):
        """Return a brief summary of the session for diagnostics."""
        with self.lock:
            total_events = len(self.events)
            gui_closed = self.gui_close_initiated
            thread_joined = self.print_thread_joined
            cleanup_calls = self.cleanup_call_count
        
        summary = {
            "session_id": self.session_id,
            "total_events": total_events,
            "gui_closed": gui_closed,
            "print_thread_joined": thread_joined,
            "cleanup_call_count": cleanup_calls,
            "log_dir": str(self.log_dir)
        }
        return summary


# Global singleton logger
_lifecycle_logger = None


def init_logger(log_dir=None):
    """Initialize global lifecycle logger."""
    global _lifecycle_logger
    if _lifecycle_logger is None:
        _lifecycle_logger = LifecycleLogger(log_dir=log_dir)
    return _lifecycle_logger


def get_logger():
    """Get global lifecycle logger (create if not exists)."""
    global _lifecycle_logger
    if _lifecycle_logger is None:
        _lifecycle_logger = LifecycleLogger()
    return _lifecycle_logger


def export_and_report():
    """Export current session log and print summary to console."""
    logger = get_logger()
    filepath = logger.export_session_log()
    summary = logger.get_summary()
    
    print("\n" + "="*60)
    print("[LifecycleLogger] Session Summary")
    print("="*60)
    for key, val in summary.items():
        print(f"  {key}: {val}")
    if filepath:
        print(f"  exported_to: {filepath}")
    print("="*60 + "\n")
