"""
Two-Step Baseline Adhesion Analyzer
===================================

This module implements the refined 2-step baseline method developed during
the September 2025 analysis sessions. It provides accurate propagation end
detection using maximum 2nd derivative timing combined with traditional
force averaging for robust baseline measurements.

Key Features:
- Step 1: Propagation end detection using max 2nd derivative timing
- Step 2: Baseline measurement using traditional stabilization averaging
- Comprehensive timing and force analysis
- Production-ready integration with PeakForceLogger

Author: Enhanced Analysis Team
Date: September 17, 2025
"""

import numpy as np
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Try to import scipy - provide fallback if not available
try:
    from scipy.signal import savgol_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available for TwoStepBaselineAnalyzer. Using simple moving average fallback.")
    
    def savgol_filter(data, window_length, polyorder):
        """Fallback function when scipy is not available - simple moving average"""
        if len(data) < window_length:
            return data.copy()
        
        # Simple moving average as fallback
        kernel = np.ones(window_length) / window_length
        # Pad the data to handle edges
        padded = np.pad(data, (window_length//2, window_length//2), mode='edge')
        smoothed = np.convolve(padded, kernel, mode='valid')
        return smoothed[:len(data)]

class AdhesionMetricsCalculatorAdapter:
    """
    Adapter for AdhesionMetricsCalculator to replace TwoStepBaselineAnalyzer.
    """
    def __init__(self, sampling_rate=50, smoothing_window=3, smoothing_order=1):
        self.calculator = AdhesionMetricsCalculator()

    def analyze_peel_data(self, timestamps, positions, forces):
        return self.calculator.calculate_metrics(timestamps, positions, forces)
