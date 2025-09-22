"""
USB Communication Coordinator

This module helps coordinate USB communications between the DLP projector
and Phidget force gauge to prevent resource contention and timing conflicts.
"""

import threading
import time
import queue
from contextlib import contextmanager

class USBCoordinator:
    """
    Manages USB communication priority and timing to prevent conflicts
    between DLP and Phidget devices.
    """
    
    def __init__(self):
        self._dlp_lock = threading.Lock()
        self._phidget_lock = threading.Lock()
        self._priority_lock = threading.Lock()
        
        # DLP operations get higher priority
        self._dlp_active = False
        self._dlp_operation_queue = queue.Queue()
        
        # Timing controls
        self.min_dlp_operation_gap = 0.1  # 100ms minimum between DLP operations
        self.last_dlp_operation = 0
        
        # Statistics
        self.dlp_operations_count = 0
        self.phidget_operations_count = 0
        self.conflicts_prevented = 0
    
    @contextmanager
    def dlp_operation(self, operation_name="unknown"):
        """
        Context manager for DLP operations. Ensures exclusive access
        and prevents conflicts with high-frequency Phidget data.
        
        Usage:
            with usb_coordinator.dlp_operation("power_on"):
                controller.power(current=255)
        """
        start_time = time.time()
        
        # Wait for minimum gap since last DLP operation
        time_since_last = start_time - self.last_dlp_operation
        if time_since_last < self.min_dlp_operation_gap:
            time.sleep(self.min_dlp_operation_gap - time_since_last)
        
        try:
            with self._priority_lock:
                self._dlp_active = True
            
            with self._dlp_lock:
                self.dlp_operations_count += 1
                print(f"USB Coordinator: Starting DLP operation '{operation_name}'")
                yield
                self.last_dlp_operation = time.time()
                print(f"USB Coordinator: Completed DLP operation '{operation_name}' in {time.time() - start_time:.3f}s")
                
        finally:
            with self._priority_lock:
                self._dlp_active = False
    
    @contextmanager 
    def phidget_batch_operation(self, operation_name="batch_read"):
        """
        Context manager for batch Phidget operations that need
        to coordinate with DLP timing.
        """
        start_time = time.time()
        
        # Check if DLP operation is active
        with self._priority_lock:
            if self._dlp_active:
                self.conflicts_prevented += 1
                print(f"USB Coordinator: Deferring Phidget '{operation_name}' due to active DLP operation")
                # Brief yield to allow DLP to complete
                time.sleep(0.001)
        
        try:
            with self._phidget_lock:
                self.phidget_operations_count += 1
                yield
                
        finally:
            pass  # Quick cleanup
    
    def is_dlp_safe_for_high_freq_operations(self):
        """
        Returns True if it's safe to perform high-frequency Phidget operations.
        """
        with self._priority_lock:
            return not self._dlp_active and (time.time() - self.last_dlp_operation > 0.05)
    
    def get_stats(self):
        """Return coordination statistics."""
        return {
            "dlp_operations": self.dlp_operations_count,
            "phidget_operations": self.phidget_operations_count,
            "conflicts_prevented": self.conflicts_prevented,
            "last_dlp_operation": self.last_dlp_operation,
            "dlp_currently_active": self._dlp_active
        }
    
    def reset_stats(self):
        """Reset operation counters."""
        self.dlp_operations_count = 0
        self.phidget_operations_count = 0
        self.conflicts_prevented = 0


# Global coordinator instance
usb_coordinator = USBCoordinator()
