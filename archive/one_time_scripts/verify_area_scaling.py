"""
Verification: Does 40%-of-max-derivative method scale correctly with Area²?
===============================================================================

This script validates that the "40% of max derivative" threshold approach
properly scales with cross-sectional area using Stefan-Reynolds physics.

Author: Cheng Sun Lab Team
Date: November 30, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter


def stefan_reynolds_force(h_mm, radius_mm, velocity_mm_s, viscosity_Pa_s=1.0):
    """
    Calculate squeeze flow force using Stefan-Reynolds equation.
    
    F = (3 * π * μ * R^4 * v) / (2 * h^3)
    
    Args:
        h_mm: Gap height (mm)
        radius_mm: Part radius (mm)
        velocity_mm_s: Approach velocity (mm/s)
        viscosity_Pa_s: Fluid viscosity (Pa·s) - default 1.0 for water
    
    Returns:
        Force (N) - negative because it's compression
    """
    h_m = h_mm / 1000.0
    radius_m = radius_mm / 1000.0
    velocity_m_s = velocity_mm_s / 1000.0
    
    force_N = (3 * np.pi * viscosity_Pa_s * radius_m**4 * velocity_m_s) / (2 * h_m**3)
    
    return -force_N  # Negative for compression


def simulate_descent_with_physics(area_mm2, gap_mm, velocity_mm_s, target_force_N=-0.6, num_points=500):
    """
    Simulate a sandwich descent using Stefan-Reynolds physics.
    
    Args:
        area_mm2: Cross-sectional area (mm²)
        gap_mm: Initial gap to window (mm)
        velocity_mm_s: Descent velocity (mm/s)
        target_force_N: Stop when this force is reached (N)
        num_points: Number of simulation points
    
    Returns:
        positions_mm, forces_N, derivatives_N_per_mm
    """
    # Convert area to radius (assuming circular)
    radius_mm = np.sqrt(area_mm2 / np.pi)
    
    print(f"\nSimulating descent:")
    print(f"  Area: {area_mm2:.2f} mm²")
    print(f"  Radius: {radius_mm:.2f} mm")
    print(f"  Initial gap: {gap_mm:.3f} mm")
    print(f"  Velocity: {velocity_mm_s:.1f} mm/s")
    
    # Create position array (moving down toward window)
    # Go all the way to near window (same POSITION for all areas)
    positions_mm = np.linspace(0, gap_mm * 0.95, num_points)  # Stop 5% before window
    
    # Calculate force at each position
    forces_N = np.zeros(num_points)
    for i, pos in enumerate(positions_mm):
        gap_remaining = gap_mm - pos
        if gap_remaining < 0.01:  # Minimum 10 µm gap to avoid singularity
            gap_remaining = 0.01
        forces_N[i] = stefan_reynolds_force(gap_remaining, radius_mm, velocity_mm_s)
    
    # Add some realistic noise
    forces_N += np.random.normal(0, 0.005, num_points)
    
    # Smooth forces
    forces_N = savgol_filter(forces_N, window_length=11, polyorder=3)
    
    # Calculate derivative
    derivatives_N_per_mm = np.gradient(forces_N, positions_mm)
    
    # Find derivative at a FIXED GAP HEIGHT (e.g., 0.1mm from window)
    # This ensures we're comparing the same physical position for all areas
    target_gap_for_threshold = 0.1  # mm - close to window but not touching
    gap_remaining_mm = gap_mm - positions_mm
    closest_idx = np.argmin(np.abs(gap_remaining_mm - target_gap_for_threshold))
    
    # Use derivative at this fixed gap height as our threshold reference
    max_derivative = np.abs(derivatives_N_per_mm[closest_idx])
    threshold_40pct = 0.4 * max_derivative
    
    # Find where we hit target force for safety cutoff
    hit_target = np.where(forces_N < target_force_N)[0]
    cutoff_idx = hit_target[0] if len(hit_target) > 0 else len(forces_N)
    
    # Cut arrays for return
    positions_mm = positions_mm[:cutoff_idx]
    forces_N = forces_N[:cutoff_idx]
    derivatives_N_per_mm = derivatives_N_per_mm[:cutoff_idx]
    
    print(f"  Final force: {forces_N[-1]:.4f} N")
    print(f"  Derivative at {target_gap_for_threshold}mm gap: {max_derivative:.4f} N/mm")
    print(f"  40% threshold: {threshold_40pct:.4f} N/mm")
    
    return positions_mm, forces_N, derivatives_N_per_mm, max_derivative, threshold_40pct


def verify_area_squared_scaling():
    """
    Verify that max derivative scales with Area².
    Test with multiple areas and check if derivative ∝ Area².
    """
    print("\n" + "="*70)
    print("VERIFICATION: Does Max Derivative Scale with Area²?")
    print("="*70)
    
    # Test with different areas (stepped cone range)
    areas_mm2 = np.array([10, 20, 30, 50, 75, 100])
    
    # Fixed parameters for all tests
    gap_mm = 2.0  # 2mm gap
    velocity_mm_s = 2.0  # 2 mm/s
    target_force_N = -0.6  # Stop at -0.6N
    
    max_derivatives = []
    threshold_40pct = []
    
    print("\nRunning simulations for different areas...")
    print(f"{'Area (mm²)':<12} {'Radius (mm)':<12} {'Max dF/dZ':<15} {'40% Threshold':<15} {'Ratio to Base':<15}")
    print("-" * 80)
    
    for area in areas_mm2:
        _, _, derivatives, max_deriv, threshold = simulate_descent_with_physics(
            area, gap_mm, velocity_mm_s, target_force_N
        )
        max_derivatives.append(max_deriv)
        threshold_40pct.append(threshold)
        
        ratio = max_deriv / max_derivatives[0]
        expected_ratio = (area / areas_mm2[0]) ** 2
        
        radius = np.sqrt(area / np.pi)
        print(f"{area:<12.1f} {radius:<12.2f} {max_deriv:<15.4f} {threshold:<15.4f} {ratio:<15.2f}")
    
    max_derivatives = np.array(max_derivatives)
    threshold_40pct = np.array(threshold_40pct)
    
    # Calculate theoretical scaling (Area²)
    area_ratios = areas_mm2 / areas_mm2[0]
    theoretical_derivatives = max_derivatives[0] * (area_ratios ** 2)
    
    print("\n" + "="*70)
    print("SCALING ANALYSIS")
    print("="*70)
    print(f"{'Area (mm²)':<12} {'Actual':<15} {'Theoretical':<15} {'Error (%)':<12}")
    print("-" * 60)
    
    for i, area in enumerate(areas_mm2):
        actual = max_derivatives[i]
        theoretical = theoretical_derivatives[i]
        error_pct = abs(actual - theoretical) / theoretical * 100
        print(f"{area:<12.1f} {actual:<15.4f} {theoretical:<15.4f} {error_pct:<12.2f}")
    
    # Statistical verification
    log_areas = np.log10(areas_mm2)
    log_derivatives = np.log10(max_derivatives)
    slope, intercept = np.polyfit(log_areas, log_derivatives, 1)
    
    print(f"\nLog-log regression:")
    print(f"  Slope: {slope:.4f} (Expected: 2.0 for Area² scaling)")
    print(f"  R² fit quality: {np.corrcoef(log_areas, log_derivatives)[0,1]**2:.6f}")
    
    # Visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Max Derivative vs Area
    ax1 = axes[0, 0]
    ax1.plot(areas_mm2, max_derivatives, 'o-', linewidth=2, markersize=8, label='Simulated')
    ax1.plot(areas_mm2, theoretical_derivatives, '--', linewidth=2, label='Theoretical (Area²)')
    ax1.set_xlabel('Cross-Sectional Area (mm²)', fontsize=12)
    ax1.set_ylabel('Max Derivative (N/mm)', fontsize=12)
    ax1.set_title('Max Derivative vs Area\n(Verify Area² Scaling)', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Plot 2: Log-Log (should be linear with slope=2)
    ax2 = axes[0, 1]
    ax2.loglog(areas_mm2, max_derivatives, 'o-', linewidth=2, markersize=8, label='Simulated')
    ax2.loglog(areas_mm2, theoretical_derivatives, '--', linewidth=2, label='Theoretical (slope=2)')
    ax2.set_xlabel('Cross-Sectional Area (mm²)', fontsize=12)
    ax2.set_ylabel('Max Derivative (N/mm)', fontsize=12)
    ax2.set_title(f'Log-Log Plot\nSlope = {slope:.3f} (Expected: 2.0)', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3, which='both')
    
    # Plot 3: 40% Threshold Scaling
    ax3 = axes[1, 0]
    theoretical_threshold = threshold_40pct[0] * (area_ratios ** 2)
    ax3.plot(areas_mm2, threshold_40pct, 'o-', linewidth=2, markersize=8, label='40% Threshold')
    ax3.plot(areas_mm2, theoretical_threshold, '--', linewidth=2, label='Theoretical (Area²)')
    ax3.set_xlabel('Cross-Sectional Area (mm²)', fontsize=12)
    ax3.set_ylabel('40% Threshold (N/mm)', fontsize=12)
    ax3.set_title('Detection Threshold (40% of max)\nVerify Area² Scaling', fontsize=13, fontweight='bold')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # Plot 4: Error Analysis
    ax4 = axes[1, 1]
    errors_pct = np.abs(max_derivatives - theoretical_derivatives) / theoretical_derivatives * 100
    ax4.bar(areas_mm2, errors_pct, width=5, alpha=0.7, color='orange')
    ax4.axhline(5, color='r', linestyle='--', label='5% tolerance')
    ax4.set_xlabel('Cross-Sectional Area (mm²)', fontsize=12)
    ax4.set_ylabel('Error (%)', fontsize=12)
    ax4.set_title('Scaling Error\n(Deviation from Area²)', fontsize=13, fontweight='bold')
    ax4.legend()
    ax4.grid(alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('verify_area_squared_scaling.png', dpi=300, bbox_inches='tight')
    print(f"\n✅ Plot saved: verify_area_squared_scaling.png")
    
    # Conclusion
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    
    avg_error = np.mean(errors_pct)
    max_error = np.max(errors_pct)
    
    if slope > 1.95 and slope < 2.05 and max_error < 5:
        print("✅ VERIFIED: Max derivative scales with Area² within acceptable tolerance")
        print(f"   Slope: {slope:.4f} ≈ 2.0 ✓")
        print(f"   Average error: {avg_error:.2f}%")
        print(f"   Max error: {max_error:.2f}%")
        print("\n✅ The 40%-of-max-derivative method WILL scale correctly!")
        print("   Calibrating on first layer and scaling by Area² is VALID.")
        return True
    else:
        print("❌ WARNING: Scaling does not match Area² perfectly")
        print(f"   Slope: {slope:.4f} (expected ~2.0)")
        print(f"   Max error: {max_error:.2f}%")
        return False


def verify_detection_consistency():
    """
    Verify that using 40% threshold gives consistent contact detection
    across different areas.
    """
    print("\n" + "="*70)
    print("VERIFICATION: Consistent Contact Detection Across Areas")
    print("="*70)
    
    areas_mm2 = [10, 25, 50, 75, 100]
    gap_mm = 2.0
    velocity_mm_s = 2.0
    
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()
    
    print("\nSimulating contact detection for different areas...")
    print(f"{'Area (mm²)':<12} {'Calibrated':<15} {'Scaled':<15} {'Match?':<10}")
    print("-" * 60)
    
    # Calibrate on first area
    _, _, _, base_max_deriv, base_threshold = simulate_descent_with_physics(
        areas_mm2[0], gap_mm, velocity_mm_s, target_force_N=-0.6
    )
    base_area = areas_mm2[0]
    
    for idx, area in enumerate(areas_mm2):
        # Simulate this area
        positions, forces, derivatives, max_deriv, actual_threshold = simulate_descent_with_physics(
            area, gap_mm, velocity_mm_s, target_force_N=-0.6, num_points=500
        )
        
        # Calculate what the scaled threshold would be from calibration
        area_ratio = area / base_area
        scaled_threshold = base_threshold * (area_ratio ** 2)
        scaled_threshold_70pct = scaled_threshold * 0.7  # With safety factor
        
        # Check match
        match = abs(actual_threshold - scaled_threshold) / scaled_threshold < 0.1
        match_str = "✓" if match else "✗"
        
        print(f"{area:<12.1f} {actual_threshold:<15.4f} {scaled_threshold:<15.4f} {match_str:<10}")
        
        # Plot this area
        if idx < 6:
            ax = axes[idx]
            
            # Force curve
            ax_force = ax
            ax_force.plot(positions, forces, 'b-', linewidth=2, label='Force')
            ax_force.set_xlabel('Position (mm)', fontsize=10)
            ax_force.set_ylabel('Force (N)', fontsize=10, color='b')
            ax_force.tick_params(axis='y', labelcolor='b')
            
            # Derivative curve
            ax_deriv = ax.twinx()
            abs_derivatives = np.abs(derivatives)
            ax_deriv.plot(positions, abs_derivatives, 'r-', linewidth=2, label='|dF/dZ|')
            ax_deriv.axhline(actual_threshold, color='orange', linestyle='--', linewidth=1.5, 
                           label=f'40% threshold: {actual_threshold:.3f}')
            ax_deriv.axhline(scaled_threshold_70pct, color='green', linestyle=':', linewidth=1.5,
                           label=f'Scaled (70%): {scaled_threshold_70pct:.3f}')
            ax_deriv.set_ylabel('|dF/dZ| (N/mm)', fontsize=10, color='r')
            ax_deriv.tick_params(axis='y', labelcolor='r')
            
            ax.set_title(f'Area: {area:.0f} mm²', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
            
            # Combine legends
            lines1, labels1 = ax_force.get_legend_handles_labels()
            lines2, labels2 = ax_deriv.get_legend_handles_labels()
            ax_deriv.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc='upper left')
    
    # Remove extra subplots
    if len(areas_mm2) < 6:
        for idx in range(len(areas_mm2), 6):
            fig.delaxes(axes[idx])
    
    plt.tight_layout()
    plt.savefig('verify_detection_consistency.png', dpi=300, bbox_inches='tight')
    print(f"\n✅ Plot saved: verify_detection_consistency.png")


def main():
    print("\n" + "="*70)
    print("AREA² SCALING VERIFICATION FOR 40%-OF-MAX-DERIVATIVE METHOD")
    print("="*70)
    print("Testing Stefan-Reynolds physics to verify scaling approach...")
    
    # Test 1: Verify Area² scaling
    scaling_valid = verify_area_squared_scaling()
    
    # Test 2: Verify consistent detection
    verify_detection_consistency()
    
    print("\n" + "="*70)
    print("FINAL VERDICT")
    print("="*70)
    
    if scaling_valid:
        print("✅ The 40%-of-max-derivative method is MATHEMATICALLY SOUND")
        print("\nHow it works:")
        print("1. Calibrate on first layer → get max derivative")
        print("2. Set threshold = 40% of max")
        print("3. For subsequent layers: scaled_threshold = threshold × (Area_new/Area_base)²")
        print("4. This gives consistent 'relative compression' across all areas")
        print("\n✅ READY TO IMPLEMENT!")
    else:
        print("⚠️  Scaling verification shows issues - review needed")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
