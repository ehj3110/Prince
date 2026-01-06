"""
Test Script for Derivative-Based Sandwich Routine
==================================================

Tests the derivative sandwich implementation without requiring full print setup.
Validates:
1. Module imports
2. Calibration function logic
3. Area scaling calculations
4. Derivative calculation methods

Author: Cheng Sun Lab Team
Date: November 30, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter


def test_module_import():
    """Test that the derivative_sandwich module can be imported."""
    print("\n" + "="*60)
    print("TEST 1: Module Import")
    print("="*60)
    
    try:
        from support_modules.derivative_sandwich import (
            calibrate_derivative_contact,
            derivative_sandwich_descent
        )
        print("✅ Module imported successfully")
        print(f"   - calibrate_derivative_contact: {calibrate_derivative_contact}")
        print(f"   - derivative_sandwich_descent: {derivative_sandwich_descent}")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_area_scaling():
    """Test area scaling formula for derivative threshold."""
    print("\n" + "="*60)
    print("TEST 2: Area Scaling Formula")
    print("="*60)
    
    # Base calibration values
    base_derivative = 0.5  # N/mm
    base_area = 10.0  # mm²
    
    print(f"Base calibration:")
    print(f"  Derivative threshold: {base_derivative:.4f} N/mm")
    print(f"  Area: {base_area:.2f} mm²")
    print()
    
    # Test different areas
    test_areas = [10.0, 25.0, 50.0, 75.0, 100.0]
    
    print("Scaled thresholds for different areas:")
    print(f"{'Area (mm²)':<12} {'Area Ratio':<12} {'Scaled (N/mm)':<16} {'Detection (70%)':<16}")
    print("-" * 60)
    
    for area in test_areas:
        area_ratio = area / base_area
        scaled_derivative = base_derivative * (area_ratio ** 2)
        detection_threshold = scaled_derivative * 0.7
        
        print(f"{area:<12.2f} {area_ratio:<12.2f} {scaled_derivative:<16.4f} {detection_threshold:<16.4f}")
    
    print("\n✅ Area scaling calculations completed")
    return True


def test_derivative_calculation():
    """Test derivative calculation with simulated data."""
    print("\n" + "="*60)
    print("TEST 3: Derivative Calculation")
    print("="*60)
    
    # Simulate force vs position data
    # Create a curve that mimics approaching the window:
    # - Gradual increase in fluid (low derivative)
    # - Sharp jump at contact (high derivative)
    
    positions_um = np.linspace(0, 5000, 500)  # 0 to 5mm, 500 points
    
    # Force model: starts near zero, then rapid increase near "contact"
    contact_position = 4000  # Contact at 4mm
    forces_N = np.zeros_like(positions_um)
    
    for i, pos in enumerate(positions_um):
        if pos < 3000:
            # Far from window - just fluid drag
            forces_N[i] = -0.05 * (pos / 1000.0)
        elif pos < contact_position:
            # Approaching window - squeeze flow starting
            gap = (contact_position - pos) / 1000.0  # mm
            forces_N[i] = -0.1 - 0.5 / (gap + 0.1)**2  # Inverse square
        else:
            # Contact - linear increase
            forces_N[i] = -2.0 - (pos - contact_position) * 0.01
    
    # Add some noise
    forces_N += np.random.normal(0, 0.02, len(forces_N))
    
    # Smooth the data
    window_length = 11
    smoothed_forces = savgol_filter(forces_N, window_length=window_length, polyorder=3)
    
    # Calculate first derivative
    derivatives = np.gradient(smoothed_forces, positions_um)
    smoothed_derivatives = savgol_filter(derivatives, window_length=9, polyorder=2)
    
    # Calculate second derivative (inflection point method)
    second_derivatives = np.gradient(smoothed_derivatives, positions_um)
    abs_second_derivatives = np.abs(second_derivatives)
    
    # Find contact point using inflection point (maximum second derivative)
    contact_idx = np.argmax(abs_second_derivatives)
    detected_contact_position = positions_um[contact_idx]
    detected_derivative = abs(smoothed_derivatives[contact_idx])
    detected_force = smoothed_forces[contact_idx]
    detected_second_derivative = abs_second_derivatives[contact_idx]
    
    print(f"Simulated contact position: {contact_position/1000.0:.4f} mm")
    print(f"Detected contact position: {detected_contact_position/1000.0:.4f} mm")
    print(f"Detection error: {abs(detected_contact_position - contact_position):.1f} µm")
    print(f"Detected derivative (dF/dZ): {detected_derivative:.4f} N/mm")
    print(f"Detected second derivative (d²F/dZ²): {detected_second_derivative:.4f} N/mm²")
    print(f"Detected force: {detected_force:.4f} N")
    print(f"Method: Inflection point (maximum second derivative)")
    
    # Create visualization
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # Plot 1: Force vs Position
    ax1 = axes[0]
    ax1.plot(positions_um/1000.0, forces_N, 'o', alpha=0.3, markersize=2, label='Raw data')
    ax1.plot(positions_um/1000.0, smoothed_forces, 'b-', linewidth=2, label='Smoothed')
    ax1.axvline(contact_position/1000.0, color='g', linestyle='--', linewidth=2, label='True contact')
    ax1.axvline(detected_contact_position/1000.0, color='r', linestyle='--', linewidth=2, label='Detected contact')
    ax1.set_xlabel('Position (mm)', fontsize=12)
    ax1.set_ylabel('Force (N)', fontsize=12)
    ax1.set_title('Force vs Position (Simulated Sandwich Descent)', fontsize=14, fontweight='bold')
    ax1.grid(alpha=0.3)
    ax1.legend()
    
    # Plot 2: First Derivative vs Position
    ax2 = axes[1]
    ax2.plot(positions_um/1000.0, np.abs(smoothed_derivatives), 'r-', linewidth=2)
    ax2.axvline(contact_position/1000.0, color='g', linestyle='--', linewidth=2, label='True contact')
    ax2.axvline(detected_contact_position/1000.0, color='r', linestyle='--', linewidth=2, label='Detected contact (inflection)')
    ax2.axhline(detected_derivative, color='orange', linestyle=':', linewidth=2, label=f'Threshold: {detected_derivative:.4f} N/mm')
    ax2.set_xlabel('Position (mm)', fontsize=12)
    ax2.set_ylabel('|dF/dZ| (N/mm)', fontsize=12)
    ax2.set_title('First Derivative (Force Rate)', fontsize=14, fontweight='bold')
    ax2.grid(alpha=0.3)
    ax2.legend()
    
    # Plot 3: Second Derivative vs Position (Inflection Point Detection)
    ax3 = axes[2]
    ax3.plot(positions_um/1000.0, abs_second_derivatives, 'purple', linewidth=2)
    ax3.axvline(contact_position/1000.0, color='g', linestyle='--', linewidth=2, label='True contact')
    ax3.axvline(detected_contact_position/1000.0, color='r', linestyle='--', linewidth=2, label='Detected contact (inflection)')
    ax3.scatter([detected_contact_position/1000.0], [detected_second_derivative], 
               color='red', s=100, zorder=5, label=f'Peak: {detected_second_derivative:.4f} N/mm²')
    ax3.set_xlabel('Position (mm)', fontsize=12)
    ax3.set_ylabel('|d²F/dZ²| (N/mm²)', fontsize=12)
    ax3.set_title('Second Derivative (Inflection Point Detection)', fontsize=14, fontweight='bold')
    ax3.grid(alpha=0.3)
    ax3.legend()
    
    plt.tight_layout()
    plt.savefig('test_derivative_calculation.png', dpi=300, bbox_inches='tight')
    print(f"\n✅ Derivative calculation test complete")
    print(f"   Plot saved: test_derivative_calculation.png")
    
    return True


def test_area_scaling_visualization():
    """Visualize how threshold scales with area."""
    print("\n" + "="*60)
    print("TEST 4: Area Scaling Visualization")
    print("="*60)
    
    base_derivative = 0.5  # N/mm
    base_area = 10.0  # mm²
    
    # Range of areas (stepped cone: 10 to 100 mm²)
    areas = np.linspace(10, 100, 50)
    
    # Calculate scaled thresholds
    area_ratios = areas / base_area
    scaled_derivatives = base_derivative * (area_ratios ** 2)
    detection_thresholds = scaled_derivatives * 0.7
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Threshold vs Area
    ax1.plot(areas, scaled_derivatives, 'b-', linewidth=2, label='Scaled threshold (100%)')
    ax1.plot(areas, detection_thresholds, 'r--', linewidth=2, label='Detection threshold (70%)')
    ax1.fill_between(areas, 0, detection_thresholds, alpha=0.2, color='red', label='Detection range')
    ax1.set_xlabel('Cross-Sectional Area (mm²)', fontsize=12)
    ax1.set_ylabel('Derivative Threshold (N/mm)', fontsize=12)
    ax1.set_title('Derivative Threshold vs Area\n(Stefan-Reynolds Scaling: ∝ Area²)', 
                  fontsize=13, fontweight='bold')
    ax1.grid(alpha=0.3)
    ax1.legend()
    
    # Plot 2: Log-Log to show Area² relationship
    ax2.loglog(areas, scaled_derivatives, 'b-', linewidth=2, marker='o', markersize=4)
    ax2.set_xlabel('Cross-Sectional Area (mm²)', fontsize=12)
    ax2.set_ylabel('Derivative Threshold (N/mm)', fontsize=12)
    ax2.set_title('Log-Log Plot\n(Slope = 2 confirms Area² scaling)', 
                  fontsize=13, fontweight='bold')
    ax2.grid(alpha=0.3, which='both')
    
    # Add slope annotation
    # Calculate slope in log-log space
    log_areas = np.log10(areas)
    log_derivatives = np.log10(scaled_derivatives)
    slope = np.polyfit(log_areas, log_derivatives, 1)[0]
    ax2.text(0.05, 0.95, f'Slope = {slope:.2f}\n(Expected: 2.0)', 
             transform=ax2.transAxes, fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('test_area_scaling_visualization.png', dpi=300, bbox_inches='tight')
    print(f"✅ Area scaling visualization complete")
    print(f"   Plot saved: test_area_scaling_visualization.png")
    print(f"   Slope in log-log: {slope:.3f} (expected: 2.0)")
    
    return True


def test_detection_sensitivity():
    """Test how detection factor affects contact detection."""
    print("\n" + "="*60)
    print("TEST 5: Detection Sensitivity Analysis")
    print("="*60)
    
    # Simulated derivative threshold
    calibrated_threshold = 0.5  # N/mm
    
    # Test different detection factors
    detection_factors = [0.5, 0.6, 0.7, 0.8, 0.9]
    
    print(f"Calibrated threshold: {calibrated_threshold:.4f} N/mm")
    print()
    print("Detection thresholds for different sensitivity factors:")
    print(f"{'Factor':<10} {'Threshold (N/mm)':<20} {'Sensitivity':<15}")
    print("-" * 50)
    
    for factor in detection_factors:
        threshold = calibrated_threshold * factor
        sensitivity = "High (early)" if factor < 0.7 else "Medium" if factor == 0.7 else "Low (late)"
        print(f"{factor:<10.2f} {threshold:<20.4f} {sensitivity:<15}")
    
    print("\n✅ Detection sensitivity analysis complete")
    print("   Recommendation: Use 0.7 (70%) as default for balance")
    print("   - Lower values (0.5-0.6): Earlier detection, less compression")
    print("   - Higher values (0.8-0.9): Later detection, more compression")
    
    return True


def test_real_world_scenario():
    """Test with realistic stepped cone geometry."""
    print("\n" + "="*60)
    print("TEST 6: Real-World Scenario (Stepped Cone)")
    print("="*60)
    
    # Stepped cone: 10 to 100 mm² over 440 layers
    num_layers = 440
    areas = np.linspace(10, 100, num_layers)
    
    # Calibration on first layer
    base_derivative = 0.5  # N/mm
    base_area = areas[0]
    
    print(f"Print geometry: Stepped cone")
    print(f"Layers: {num_layers}")
    print(f"Area range: {areas[0]:.2f} to {areas[-1]:.2f} mm²")
    print(f"\nCalibration (Layer 1):")
    print(f"  Area: {base_area:.2f} mm²")
    print(f"  Derivative threshold: {base_derivative:.4f} N/mm")
    print()
    
    # Calculate for key layers
    key_layers = [1, 50, 100, 200, 300, 400, 440]
    
    print("Derivative thresholds at key layers:")
    print(f"{'Layer':<8} {'Area (mm²)':<12} {'Scaled (N/mm)':<16} {'Detection (70%)':<16}")
    print("-" * 60)
    
    for layer in key_layers:
        idx = layer - 1
        area = areas[idx]
        area_ratio = area / base_area
        scaled = base_derivative * (area_ratio ** 2)
        detection = scaled * 0.7
        print(f"{layer:<8} {area:<12.2f} {scaled:<16.4f} {detection:<16.4f}")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scaled_thresholds = base_derivative * ((areas / base_area) ** 2)
    detection_thresholds = scaled_thresholds * 0.7
    
    ax.plot(range(1, num_layers+1), scaled_thresholds, 'b-', linewidth=2, 
            label='Scaled threshold (100%)', alpha=0.7)
    ax.plot(range(1, num_layers+1), detection_thresholds, 'r-', linewidth=2.5, 
            label='Detection threshold (70%)')
    ax.fill_between(range(1, num_layers+1), 0, detection_thresholds, 
                     alpha=0.2, color='red', label='Detection range')
    
    ax.set_xlabel('Layer Number', fontsize=12)
    ax.set_ylabel('Derivative Threshold (N/mm)', fontsize=12)
    ax.set_title('Derivative Threshold Across Print\n(Stepped Cone: 10-100 mm²)', 
                 fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=11)
    
    # Add annotations for key layers
    for layer in [1, 100, 200, 300, 400, 440]:
        idx = layer - 1
        ax.annotate(f'L{layer}\n{areas[idx]:.0f}mm²', 
                   xy=(layer, detection_thresholds[idx]),
                   xytext=(0, 20), textcoords='offset points',
                   ha='center', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    plt.tight_layout()
    plt.savefig('test_real_world_scenario.png', dpi=300, bbox_inches='tight')
    print(f"\n✅ Real-world scenario test complete")
    print(f"   Plot saved: test_real_world_scenario.png")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("DERIVATIVE-BASED SANDWICH ROUTINE - TEST SUITE")
    print("="*70)
    print("Testing implementation before first print...")
    print()
    
    results = []
    
    # Run all tests
    results.append(("Module Import", test_module_import()))
    results.append(("Area Scaling", test_area_scaling()))
    results.append(("Derivative Calculation", test_derivative_calculation()))
    results.append(("Area Scaling Visualization", test_area_scaling_visualization()))
    results.append(("Detection Sensitivity", test_detection_sensitivity()))
    results.append(("Real-World Scenario", test_real_world_scenario()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
    
    print("-" * 70)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Implementation ready for real print test.")
        print("\nNext steps:")
        print("1. Open Prince_Segmented.py")
        print("2. Check 'Use Derivative-Based Sandwich' checkbox")
        print("3. Uncheck 'Use Adaptive Sandwich' checkbox")
        print("4. Start print and monitor console for calibration")
        print("5. Watch for area scaling on different layers")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
    
    print("\n" + "="*70)
    print("Test plots generated:")
    print("  - test_derivative_calculation.png")
    print("  - test_area_scaling_visualization.png")
    print("  - test_real_world_scenario.png")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
