"""
Enhanced Adhesion Metrics Calculator
====================================

This module provides advanced analysis methods for adhesion measurements during
resin 3D printing peeling operations. It enhances the basic PeakForceLogger
with more sophisticated timing, force gradient, and work calculations.

Author: Enhanced by Claude for improved adhesion analysis
Date: September 15, 2025
"""

import numpy as np
import warnings
import sys
import os

# Replace legacy EnhancedAdhesionAnalyzer with AdhesionMetricsCalculator
from adhesion_metrics_calculator import AdhesionMetricsCalculator

class EnhancedAdhesionAnalyzerAdapter:
    """
    Adapter for AdhesionMetricsCalculator to replace EnhancedAdhesionAnalyzer.
    """
    def __init__(self, smoothing_sigma=0.5, noise_threshold=0.005):
        self.calculator = AdhesionMetricsCalculator(
            smoothing_sigma=smoothing_sigma,
            noise_threshold=noise_threshold
        )

    def analyze_peel_data(self, timestamps, positions, forces):
        return self.calculator.calculate_metrics(timestamps, positions, forces)
    
    def format_results_for_csv(self, results):
        """Format results for CSV output with proper precision."""
        formatted = {}
        
        # Define precision for different metric types
        time_precision = 4      # seconds
        force_precision = 4     # Newtons
        position_precision = 4  # mm
        energy_precision = 4    # mJ
        rate_precision = 3      # N/s
        freq_precision = 2      # Hz
        
        # Format each result with appropriate precision
        for key, value in results.items():
            if np.isnan(value) or np.isinf(value):
                formatted[key] = "NaN"
            elif 'time' in key.lower() or 'duration' in key.lower():
                formatted[key] = f"{value:.{time_precision}f}"
            elif 'force' in key.lower() and 'rate' not in key.lower():
                formatted[key] = f"{value:.{force_precision}f}"
            elif 'position' in key.lower():
                formatted[key] = f"{value:.{position_precision}f}"
            elif 'energy' in key.lower() or 'work' in key.lower() or '_mJ' in key:
                formatted[key] = f"{value:.{energy_precision}f}"
            elif 'rate' in key.lower():
                formatted[key] = f"{value:.{rate_precision}f}"
            elif 'frequency' in key.lower() or '_hz' in key.lower():
                formatted[key] = f"{value:.{freq_precision}f}"
            else:
                formatted[key] = f"{value:.4f}"
                
        return formatted


# Test function for development
if __name__ == "__main__":
    # Test the analyzer with simulated data
    analyzer = EnhancedAdhesionAnalyzerAdapter()
    
    # Create test data
    t = np.linspace(0, 2.0, 100)  # 2 seconds
    pos = 10 + t * 2  # Moving from 10mm to 14mm
    
    # Simulate realistic peeling force curve
    force = np.zeros_like(t)
    
    # Add noise
    noise = np.random.normal(0, 0.01, len(t))
    
    # Create force profile: gradual increase, peak, then decay
    for i, time in enumerate(t):
        if time < 0.5:
            force[i] = 0.02 * time  # Gradual increase
        elif time < 1.0:
            force[i] = 0.01 + 0.3 * (time - 0.5)  # Rapid increase to peak
        elif time < 1.5:
            force[i] = 0.16 - 0.2 * (time - 1.0)  # Decay from peak
        else:
            force[i] = 0.06 - 0.1 * (time - 1.5)  # Return to baseline
    
    force = np.maximum(force + noise, 0)  # Add noise and ensure non-negative
    
    # Analyze
    results = analyzer.analyze_peel_data(t, pos, force)
    
    # Display results
    print("Enhanced Adhesion Analysis Results:")
    print("=" * 40)
    formatted_results = analyzer.format_results_for_csv(results)
    for key, value in formatted_results.items():
        print(f"{key}: {value}")
