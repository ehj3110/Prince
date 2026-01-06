"""
Derivative-Based Sandwich Routine
==================================

Uses force derivative (dF/dZ) to detect window contact instead of absolute force threshold.
Scales detection threshold based on cross-sectional area using Stefan-Reynolds equation.

Author: Cheng Sun Lab Team
Date: November 30, 2025
"""

import time
import numpy as np
from scipy.signal import savgol_filter


def calibrate_derivative_contact(axis, force_gauge, first_layer_area_mm2, 
                                 calibration_speed_um_s=2000.0, 
                                 max_force_N=-2.0,
                                 sampling_rate_hz=100):
    """
    Calibrate derivative threshold by moving down slowly and detecting contact.
    
    Args:
        axis: Stage axis object
        force_gauge: Force gauge manager object
        first_layer_area_mm2: Cross-sectional area of first layer (mm²)
        calibration_speed_um_s: Descent speed during calibration (µm/s)
        max_force_N: Safety force limit (N, negative = compression)
        sampling_rate_hz: Force sampling rate (Hz)
    
    Returns:
        tuple: (derivative_threshold_N_per_mm, contact_position_um, contact_force_N)
               or (None, None, None) if calibration failed
    """
    from zaber_motion import Units
    
    print(f"\n{'='*60}")
    print("DERIVATIVE CALIBRATION - Window Contact Detection")
    print(f"{'='*60}")
    print(f"First layer area: {first_layer_area_mm2:.2f} mm²")
    print(f"Calibration speed: {calibration_speed_um_s:.0f} µm/s")
    print(f"Safety limit: {max_force_N:.2f} N")
    
    positions_um = []
    forces_N = []
    timestamps = []
    
    start_pos_um = axis.get_position(Units.LENGTH_MICROMETRES)
    start_time = time.time()
    
    print(f"Starting position: {start_pos_um/1000.0:.4f} mm")
    print("Moving down to detect contact...")
    
    # Start moving down
    # Move to a far position to ensure continuous motion
    target_pos_um = start_pos_um + 10000.0  # 10mm below (won't reach due to force stop)
    
    axis.move_absolute(
        position=target_pos_um,
        unit=Units.LENGTH_MICROMETRES,
        wait_until_idle=False,
        velocity=calibration_speed_um_s / 1000.0,
        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
        acceleration=1000.0,
        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
    )
    
    sample_period = 1.0 / sampling_rate_hz
    
    # Collect data while moving
    try:
        while axis.is_busy():
            current_pos_um = axis.get_position(Units.LENGTH_MICROMETRES)
            current_force_N = force_gauge.get_latest_calibrated_force()
            current_time = time.time()
            
            positions_um.append(current_pos_um)
            forces_N.append(current_force_N)
            timestamps.append(current_time - start_time)
            
            # Safety check
            if current_force_N < max_force_N:
                print(f"Safety limit reached: {current_force_N:.3f} N")
                axis.stop()
                break
            
            time.sleep(sample_period)
    
    except KeyboardInterrupt:
        axis.stop()
        print("Calibration interrupted by user")
        return None, None, None
    
    if len(positions_um) < 20:
        print("ERROR: Insufficient data collected for calibration")
        return None, None, None
    
    # Convert to numpy arrays
    positions_um = np.array(positions_um)
    forces_N = np.array(forces_N)
    timestamps = np.array(timestamps)
    
    print(f"\nData collected: {len(positions_um)} samples over {timestamps[-1]:.2f} seconds")
    print(f"Position range: {positions_um[0]/1000.0:.4f} to {positions_um[-1]/1000.0:.4f} mm")
    print(f"Force range: {forces_N.max():.4f} to {forces_N.min():.4f} N")
    
    # Smooth forces to reduce noise
    try:
        window_length = min(11, len(forces_N) if len(forces_N) % 2 == 1 else len(forces_N) - 1)
        if window_length < 5:
            window_length = 5
        smoothed_forces = savgol_filter(forces_N, window_length=window_length, polyorder=3)
    except Exception as e:
        print(f"Warning: Could not smooth data: {e}")
        smoothed_forces = forces_N
    
    # Calculate spatial derivative dF/dZ
    # Note: positions increase as we move down, forces decrease (become more negative)
    derivatives = np.gradient(smoothed_forces, positions_um)
    
    # Smooth derivatives for second derivative calculation
    try:
        window_length_deriv = min(9, len(derivatives) if len(derivatives) % 2 == 1 else len(derivatives) - 1)
        if window_length_deriv < 5:
            window_length_deriv = 5
        smoothed_derivatives = savgol_filter(derivatives, window_length=window_length_deriv, polyorder=2)
    except Exception as e:
        print(f"Warning: Could not smooth derivatives: {e}")
        smoothed_derivatives = derivatives
    
    # Calculate second derivative (d²F/dZ²) to find inflection point
    # Inflection point = where derivative changes most rapidly = contact initiation
    second_derivatives = np.gradient(smoothed_derivatives, positions_um)
    abs_second_derivatives = np.abs(second_derivatives)
    
    # Find inflection point (maximum second derivative magnitude)
    inflection_idx = np.argmax(abs_second_derivatives)
    
    # The derivative at the inflection point is our threshold
    # This captures "moment of contact" rather than "maximum compression"
    derivative_threshold = abs(smoothed_derivatives[inflection_idx])
    contact_position_um = positions_um[inflection_idx]
    contact_force_N = smoothed_forces[inflection_idx]
    
    print(f"\nContact detected (inflection point method):")
    print(f"  Position: {contact_position_um/1000.0:.4f} mm")
    print(f"  Force: {contact_force_N:.4f} N")
    print(f"  Derivative (dF/dZ): {derivative_threshold:.4f} N/mm")
    print(f"  Second derivative peak: {abs_second_derivatives[inflection_idx]:.4f} N/mm²")
    print(f"  (Using inflection point - moment of contact initiation)")
    
    # Save calibration data for later plotting
    calibration_data = {
        'positions_um': positions_um,
        'forces_N': forces_N,
        'smoothed_forces': smoothed_forces,
        'derivatives': derivatives,
        'smoothed_derivatives': smoothed_derivatives,
        'second_derivatives': second_derivatives,
        'contact_idx': inflection_idx,
        'timestamps': timestamps
    }
    
    print(f"{'='*60}\n")
    
    return derivative_threshold, contact_position_um, contact_force_N, calibration_data


def derivative_sandwich_descent(axis, force_gauge, current_layer_area_mm2,
                                base_derivative_N_per_mm, base_area_mm2,
                                sandwich_speed_um_s, target_position_um,
                                max_force_N=-2.0, detection_factor=0.7,
                                sampling_rate_hz=100):
    """
    Perform sandwich descent using derivative-based contact detection.
    
    Args:
        axis: Stage axis object
        force_gauge: Force gauge manager object
        current_layer_area_mm2: Cross-sectional area of current layer (mm²)
        base_derivative_N_per_mm: Calibrated derivative threshold (N/mm)
        base_area_mm2: Area used for calibration (mm²)
        sandwich_speed_um_s: Descent speed (µm/s)
        target_position_um: Target position (µm) - layer height
        max_force_N: Safety force limit (N, negative = compression)
        detection_factor: Multiplier for threshold (default 0.7 = 70% of calibrated value)
        sampling_rate_hz: Force sampling rate (Hz)
    
    Returns:
        tuple: (contact_position_um, contact_force_N, stopped_early)
    """
    from zaber_motion import Units
    
    # Scale derivative threshold based on area
    # Stefan equation: F ∝ R^4, and R² ∝ Area, so F ∝ Area²
    # Therefore dF/dZ ∝ Area²
    area_ratio = current_layer_area_mm2 / base_area_mm2
    scaled_derivative = base_derivative_N_per_mm * (area_ratio ** 2)
    detection_threshold = scaled_derivative * detection_factor
    
    print(f"Derivative-based descent:")
    print(f"  Current area: {current_layer_area_mm2:.2f} mm²")
    print(f"  Base derivative: {base_derivative_N_per_mm:.4f} N/mm")
    print(f"  Scaled derivative: {scaled_derivative:.4f} N/mm")
    print(f"  Detection threshold (70%): {detection_threshold:.4f} N/mm")
    print(f"  Speed: {sandwich_speed_um_s:.0f} µm/s")
    
    start_pos_um = axis.get_position(Units.LENGTH_MICROMETRES)
    
    # Start moving down toward target
    # Calculate a position beyond target to ensure continuous motion
    overshoot_target_um = target_position_um + 2000.0  # 2mm beyond
    
    axis.move_absolute(
        position=overshoot_target_um,
        unit=Units.LENGTH_MICROMETRES,
        wait_until_idle=False,
        velocity=sandwich_speed_um_s / 1000.0,
        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
        acceleration=1000.0,
        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
    )
    
    last_pos_um = start_pos_um
    last_force_N = force_gauge.get_latest_calibrated_force()
    sample_period = 1.0 / sampling_rate_hz
    stopped_early = False
    
    print("Monitoring derivative...")
    
    try:
        while axis.is_busy():
            time.sleep(sample_period)
            
            current_pos_um = axis.get_position(Units.LENGTH_MICROMETRES)
            current_force_N = force_gauge.get_latest_calibrated_force()
            
            # Calculate spatial derivative
            dZ = current_pos_um - last_pos_um
            dF = current_force_N - last_force_N
            
            if abs(dZ) > 1e-6:  # Avoid division by zero
                dF_dZ = abs(dF / dZ)  # Use absolute value for comparison
                
                # Check if derivative threshold exceeded
                if dF_dZ > detection_threshold:
                    print(f"  Contact detected: dF/dZ = {dF_dZ:.4f} N/mm (threshold: {detection_threshold:.4f})")
                    axis.stop()
                    stopped_early = True
                    break
            
            # Safety check
            if current_force_N < max_force_N:
                print(f"  Safety limit reached: {current_force_N:.3f} N")
                axis.stop()
                stopped_early = True
                break
            
            # Update for next iteration
            last_pos_um = current_pos_um
            last_force_N = current_force_N
    
    except KeyboardInterrupt:
        axis.stop()
        print("Sandwich interrupted by user")
        stopped_early = True
    
    final_pos_um = axis.get_position(Units.LENGTH_MICROMETRES)
    final_force_N = force_gauge.get_latest_calibrated_force()
    
    print(f"Descent complete:")
    print(f"  Final position: {final_pos_um/1000.0:.4f} mm")
    print(f"  Final force: {final_force_N:.4f} N")
    print(f"  Stopped early: {stopped_early}")
    
    return final_pos_um, final_force_N, stopped_early
