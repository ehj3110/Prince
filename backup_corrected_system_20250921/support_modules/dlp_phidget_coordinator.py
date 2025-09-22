"""
DLP Integration Helper

This module provides utilities to manage DLP and Phidget coexistence,
preventing USB resource conflicts that can interfere with DLP projection.
"""

import time
import threading

class DLPPhidgetCoordinator:
    """
    Coordinates DLP and Phidget operations to prevent resource conflicts.
    """
    
    def __init__(self, force_gauge_manager=None):
        self.force_gauge_manager = force_gauge_manager
        self.dlp_mode_active = False
        self.original_data_rate = None
        
    def prepare_for_dlp_operation(self):
        """
        Prepare system for DLP operation by reducing Phidget resource usage.
        Call this before starting DLP projection.
        """
        if not self.force_gauge_manager:
            print("No ForceGaugeManager available - DLP preparation skipped")
            return
            
        print("Preparing for DLP operation...")
        
        # Store original settings
        if hasattr(self.force_gauge_manager, 'current_data_rate_hz'):
            self.original_data_rate = self.force_gauge_manager.current_data_rate_hz
        
        # Enable DLP-friendly mode
        self.force_gauge_manager.enable_dlp_friendly_mode()
        
        # Reduce data rate to DLP-safe levels (100 Hz max)
        self.force_gauge_manager.set_data_rate_limit(100)
        
        # Small delay to let changes take effect
        time.sleep(0.1)
        
        self.dlp_mode_active = True
        print("System prepared for DLP operation (reduced Phidget data rate)")
        
    def restore_after_dlp_operation(self):
        """
        Restore full Phidget performance after DLP operation.
        Call this after DLP projection is complete.
        """
        if not self.force_gauge_manager or not self.dlp_mode_active:
            return
            
        print("Restoring full Phidget performance...")
        
        # Disable DLP-friendly mode
        self.force_gauge_manager.disable_dlp_friendly_mode()
        
        # Restore original data rate if available
        if self.original_data_rate:
            target_interval = max(1, 1000 // self.original_data_rate)
            self.force_gauge_manager.set_data_interval(target_interval)
        
        self.dlp_mode_active = False
        print("Full Phidget performance restored")
        
    def get_status(self):
        """Get current coordination status"""
        if not self.force_gauge_manager:
            return {"status": "No ForceGaugeManager", "dlp_mode": False}
            
        usage = self.force_gauge_manager.get_current_resource_usage()
        return {
            "dlp_mode_active": self.dlp_mode_active,
            "dlp_friendly_mode": usage.get('dlp_friendly_mode', False),
            "current_data_rate": usage.get('current_data_rate', 0),
            "queue_usage": {
                "critical": usage.get('critical_queue_size', 0),
                "gui": usage.get('gui_queue_size', 0)
            }
        }

# Convenience functions for direct use
_global_coordinator = None

def initialize_coordinator(force_gauge_manager):
    """Initialize the global DLP coordinator"""
    global _global_coordinator
    _global_coordinator = DLPPhidgetCoordinator(force_gauge_manager)
    return _global_coordinator

def prepare_for_dlp():
    """Prepare system for DLP operation"""
    if _global_coordinator:
        _global_coordinator.prepare_for_dlp_operation()
    else:
        print("DLP coordinator not initialized")

def restore_after_dlp():
    """Restore full performance after DLP operation"""
    if _global_coordinator:
        _global_coordinator.restore_after_dlp_operation()
    else:
        print("DLP coordinator not initialized")

def get_coordination_status():
    """Get current coordination status"""
    if _global_coordinator:
        return _global_coordinator.get_status()
    else:
        return {"status": "Not initialized"}

# Context manager for automatic DLP coordination
class DLPOperationContext:
    """
    Context manager for DLP operations.
    
    Usage:
        with DLPOperationContext():
            # Perform DLP operations
            controller.pattern_mode()
            controller.project_pattern()
    """
    
    def __enter__(self):
        prepare_for_dlp()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        restore_after_dlp()
        return False  # Don't suppress exceptions
