"""
Test Hydrodynamic Locking Skip Feature
======================================

Quick test to verify the skip_initial_time_ms parameter works correctly.

Author: Cheng Sun Lab Team
Date: January 11, 2026
"""

import numpy as np
import sys
from pathlib import Path

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator


def create_test_data_with_spike():
    """Create synthetic data with hydrodynamic spike at start"""
    
    # Time: 0 to 1 second, 1000 Hz sampling
    time = np.linspace(0, 1, 1000)
    
    # Position: linear retraction
    position = time * 5  # 5mm/s retraction
    
    # Force: realistic adhesion curve with initial spike
    force = np.zeros_like(time)
    
    # 1. Hydrodynamic spike in first 150ms
    spike_mask = time < 0.15
    force[spike_mask] = 5.0 + 3.0 * np.sin(time[spike_mask] * 20)  # ~8N spike
    
    # 2. True adhesion peak at ~300ms
    true_peak_time = 0.3
    true_peak_force = 4.5
    for i, t in enumerate(time):
        if 0.15 <= t <= 0.5:
            # Smooth adhesion curve
            force[i] = true_peak_force * np.exp(-((t - true_peak_time) / 0.1) ** 2)
    
    # 3. Decay to baseline
    baseline_mask = time > 0.5
    force[baseline_mask] = 0.5 + 0.3 * np.exp(-(time[baseline_mask] - 0.5) / 0.2)
    
    return time, position, force


def test_skip_feature():
    """Test the skip feature with synthetic data"""
    
    print("="*80)
    print("Testing Hydrodynamic Locking Skip Feature")
    print("="*80)
    
    # Create test data
    time, position, force = create_test_data_with_spike()
    
    print("\nTest data:")
    print(f"  Duration: {time[-1]:.2f}s")
    print(f"  Sampling rate: {len(time)}Hz")
    print(f"  True peak: ~4.5N at 0.30s")
    print(f"  False spike: ~8N in first 0.15s")
    
    # Test 1: Without skip (should find false spike)
    print("\n" + "="*80)
    print("Test 1: NO SKIP (Default behavior)")
    print("="*80)
    
    calc_no_skip = AdhesionMetricsCalculator()
    results_no_skip = calc_no_skip.calculate_from_arrays(
        time, position, force, layer_number=1
    )
    
    print(f"Peak force: {results_no_skip['peak_force']:.2f} N")
    print(f"Peak time: {results_no_skip['peak_force_time']:.3f} s")
    print(f"Expected: Should find FALSE spike (~8N at ~0.08s)")
    
    # Test 2: With 150ms skip (should find true peak)
    print("\n" + "="*80)
    print("Test 2: 150ms SKIP (Hydrodynamic mitigation)")
    print("="*80)
    
    calc_with_skip = AdhesionMetricsCalculator(skip_initial_time_ms=150)
    results_with_skip = calc_with_skip.calculate_from_arrays(
        time, position, force, layer_number=1
    )
    
    print(f"Peak force: {results_with_skip['peak_force']:.2f} N")
    print(f"Peak time: {results_with_skip['peak_force_time']:.3f} s")
    print(f"Expected: Should find TRUE peak (~4.5N at ~0.30s)")
    
    # Verify results
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    # Test 1: Without skip should find spike
    if results_no_skip['peak_force'] > 7.0 and results_no_skip['peak_force_time'] < 0.15:
        print("✅ Test 1 PASSED: Found false spike as expected")
    else:
        print("❌ Test 1 FAILED: Did not find false spike")
    
    # Test 2: With skip should find true peak
    if 4.0 < results_with_skip['peak_force'] < 5.0 and 0.25 < results_with_skip['peak_force_time'] < 0.35:
        print("✅ Test 2 PASSED: Found true peak after skip")
    else:
        print("❌ Test 2 FAILED: Did not find true peak")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    improvement = ((results_no_skip['peak_force'] - results_with_skip['peak_force']) / 
                   results_no_skip['peak_force'] * 100)
    
    print(f"Peak force reduction: {improvement:.1f}%")
    print(f"Time delay: {(results_with_skip['peak_force_time'] - results_no_skip['peak_force_time'])*1000:.0f}ms")
    
    if improvement > 30:
        print("\n✅ FEATURE WORKING: Skip successfully avoided hydrodynamic spike!")
    else:
        print("\n⚠️  WARNING: Skip may not be working as expected")
    
    print("\n✓ Test complete!")


if __name__ == "__main__":
    test_skip_feature()
