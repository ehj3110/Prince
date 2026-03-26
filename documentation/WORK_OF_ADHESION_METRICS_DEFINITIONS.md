# Work of Adhesion Metrics Definitions
**Research-Grade DLP Resin 3D-Printer Force Analysis**

---

**Document Version:** 1.1  
**Date Created:** September 17, 2025  
**Date Updated:** September 19, 2025  
**Authors:** Cheng Sun Lab Team  
**System:** Prince Segmented DLP 3D-Printer  

---

## Overview

This document defines all metrics used in the work of adhesion calculations for resin 3D printing characterization. These metrics are collected during layer peeling operations using the integrated Phidget force gauge and analyzed through the PeakForceLogger and enhanced adhesion analysis systems.

---

## Printing Process Stages

### **DLP Printing Process Phases**

#### **Exposure Stage**
- **Definition:** The DLP projector is actively curing resin with UV light
- **System State:** DLP ON, Linear stage STATIONARY
- **Duration:** Defined by exposure time parameter for current layer
- **Physical Process:** Photopolymerization of liquid resin into solid layer
- **Force Characteristics:** Minimal force variation, baseline level measurements

#### **Lifting Stage**
- **Definition:** Linear stage moves upward to separate the newly cured layer
- **System State:** DLP OFF, Linear stage MOVING UPWARD
- **Distance:** Determined by overstep distance parameter
- **Physical Process:** Layer separation from vat window/previous layer
- **Force Characteristics:** Contains the complete peel force profile (sawtooth pattern)

#### **Retraction Stage**
- **Definition:** Linear stage moves downward to position for next layer
- **System State:** DLP OFF, Linear stage MOVING DOWNWARD
- **End Position:** New layer height (previous height + layer thickness)
- **Physical Process:** Part repositioning in resin vat
- **Force Characteristics:** Generally minimal forces, possible resin flow effects

#### **Pause Stage**
- **Definition:** Stationary period between retraction and next exposure
- **System State:** DLP OFF, Linear stage STATIONARY
- **Duration:** Defined by pause duration parameter
- **Physical Process:** Resin settling and flow around part geometry
- **Force Characteristics:** Baseline level, potential settling dynamics

---

## Force Analysis Stages

### **Adhesion Force Phases (Sawtooth Pattern)**

#### **Pre-Initiation Phase**
- **Definition:** Force buildup period during lifting stage onset
- **Time Span:** From dynamic baseline crossing to peak force
- **Physical Process:** Elastic deformation and stress concentration buildup
- **Force Behavior:** Gradual force increase as adhesive bonds stretch
- **Mechanical Significance:** Represents elastic energy storage before crack initiation
- **Detection Criteria:** Force exceeds dynamic baseline threshold

#### **Initiation (Critical Moment)**
- **Definition:** Instantaneous moment of peak force when crack initiation occurs
- **Time Span:** Single point in time (peak force instant)
- **Physical Process:** Crack nucleation and initial bond failure
- **Force Behavior:** Maximum force value in the peel sequence
- **Mechanical Significance:** Critical stress threshold for adhesive failure
- **Detection Criteria:** Local maximum in force profile during lifting

#### **Propagation Phase**
- **Definition:** Rapid crack propagation and complete layer separation
- **Time Span:** From initiation to return to dynamic baseline
- **Physical Process:** Fast crack growth and progressive bond failure
- **Force Behavior:** Rapid force decrease back to baseline level
- **Mechanical Significance:** Energy release during catastrophic separation
- **Detection Criteria:** Force decay from peak back to baseline threshold

### **Complete Sawtooth Cycle**
- **Pattern:** Pre-initiation (gradual rise) → Initiation (peak) → Propagation (rapid fall)
- **Repetition:** Occurs once per layer during lifting stage
- **Duration:** Typically completes within the lifting stage timeframe
- **Energy Content:** Total work of adhesion captured in complete cycle

---

## Propagation End Detection Methods

### **Current Approach: Second Derivative Maximum Detection**

#### **Method: Second Derivative Maximum After Peak Force**
- **Principle:** Find the maximum value of the second derivative (d²F/dt²) after peak force and before stage motion stops
- **Calculation:** 
  1. Apply current smoothing method: `smoothed_force = savgol_filter(force_data, window_length=11, polyorder=2)`
  2. Calculate first derivative: `dF/dt = np.gradient(smoothed_force, time_data)`
  3. Calculate second derivative: `d²F/dt² = np.gradient(dF/dt, time_data)`
  4. Find peak force index: `peak_idx = np.argmax(smoothed_force)`
  5. Search region: from `peak_idx` to end of stage motion
  6. Find maximum second derivative: `prop_end_idx = peak_idx + np.argmax(d²F/dt²[peak_idx:motion_end])`
- **Physical Meaning:** Maximum curvature in force decay indicates the point of fastest deceleration in force change
- **Advantages:** Captures the inflection point where rapid force decrease begins to level off
- **Implementation Notes:** 
  - Use current smoothing method (Savitzky-Golay filter) before derivative calculations
  - Ensure search region excludes post-motion data
  - Handle edge cases where motion ends before clear propagation completion

#### **Smoothing Integration:**
- **Current Method:** Savitzky-Golay filter (window_length=11, polyorder=2)
- **Application:** Apply smoothing to force data before derivative calculations
- **Rationale:** Reduces noise amplification in derivative computations while preserving signal characteristics
- **Implementation:** 
  ```python
  # Apply current smoothing method
  smoothed_force = savgol_filter(force_data, window_length=11, polyorder=2)
  
  # Calculate derivatives on smoothed data
  first_derivative = np.gradient(smoothed_force, time_data)
  second_derivative = np.gradient(first_derivative, time_data)
  
  # Find propagation end using second derivative maximum
  peak_idx = np.argmax(smoothed_force)
  search_region = second_derivative[peak_idx:motion_end_idx]
  prop_end_idx = peak_idx + np.argmax(search_region)
  ```

#### **Alternative Methods (Historical Context):**

**Previous Relative Methods (Deprecated):**
- **Gradient Threshold Detection:** `dF/dt < 0.02 * max_propagation_gradient`
- **Baseline Convergence:** `|F(t) - F_baseline| < 0.05 * (F_peak - F_baseline)`
- **Combined Relative Approach:** Gradient + convergence confirmation
- **Statistical Change Point:** CUSUM with adaptive threshold
- **Moving Window Variance:** Variance-based detection
- **Exponential Moving Average:** EMA slope tracking

**Reasons for Method Change:**
- Second derivative maximum provides more consistent detection across varying signal characteristics
- Reduces dependency on baseline estimation accuracy
- Better handles underdamped oscillations and signal artifacts
- More robust to noise when combined with current smoothing approach

---

## Core Force Metrics

### **Peak Peel Force (N)**
- **Definition:** Highest peak force measured during the lifting stage
- **Symbol:** F_peak
- **Units:** Newtons (N)
- **Physical Meaning:** Maximum adhesive resistance at the initiation moment when crack formation begins
- **Calculation:** `F_peak = max(force_data[lifting_stage])` during sawtooth pattern
- **Stage Association:** Occurs at the **Initiation** moment (peak of sawtooth)
- **Research Significance:** Critical stress threshold for adhesive bond failure; indicates layer adhesion strength

### **Peak Retraction Force (N)**
- **Definition:** Minimum (most negative) force measured during the retraction stage
- **Symbol:** F_retraction
- **Units:** Newtons (N)
- **Physical Meaning:** Maximum resistance as part pushes resin out of the way during downward movement
- **Calculation:** `F_retraction = min(force_data[retraction_stage])` (most negative value)
- **Stage Association:** Occurs during **Retraction Stage** when part moves back into resin
- **Research Significance:** Indicates resin viscosity effects and geometric interaction forces

---

## Baseline and Reference Metrics

### **Dynamic Baseline Force (N)**
- **Definition:** Reference force level measured immediately after propagation phase completion when part fully separates
- **Symbol:** F_baseline
- **Units:** Newtons (N)
- **Calculation Methods:**
  - **Post-Propagation Baseline:** `F_baseline = mean(force_data[post_propagation_stable_region])`
  - **Pre-Exposure Baseline:** `F_baseline = mean(force_data[exposure_stage_stable_region])`
- **Physical Meaning:** True equilibrium force accounting for sensor offset, thermal drift, and residual system forces
- **Research Significance:** Critical reference for accurate work calculations and force normalization
- **Detection Criteria:** Stable force region after sharp propagation completion (using second derivative maximum detection)

### **Baseline-Corrected Peak Force (N)**
- **Definition:** Peak force with baseline offset removed
- **Symbol:** F_peak_corrected
- **Units:** Newtons (N)
- **Calculation:** `F_peak_corrected = F_peak - F_baseline`
- **Physical Meaning:** True adhesion force above equilibrium/rest state
- **Research Significance:** More accurate representation of actual adhesion strength

---

## Work and Energy Metrics

### **Work of Adhesion (mJ)**
- **Definition:** Energy required for complete layer separation during the sawtooth pattern
- **Symbol:** W_adhesion
- **Units:** Millijoules (mJ)
- **Calculation:** `W_adhesion = ∫ F(z) dz` from Pre-Initiation start to Propagation end
- **Integration Bounds:** Pre-Initiation threshold crossing to Propagation completion (detected via second derivative maximum)
- **Integration Methods:**
  - **Trapezoidal Rule:** Standard numerical integration
  - **Simpson's Rule:** Higher accuracy for smooth data
- **Physical Meaning:** Total mechanical energy input required for complete layer separation
- **Research Significance:** Fundamental material property capturing full adhesion energy content
- **Noise Avoidance:** Integration bounds exclude exposure/pause stages to minimize noise contribution

### **Baseline-Corrected Work of Adhesion (mJ)**
- **Definition:** Work calculation using baseline-corrected force data
- **Symbol:** W_adhesion_corrected
- **Units:** Millijoules (mJ)
- **Calculation:** `W_adhesion_corrected = ∫ (F(z) - F_baseline) dz`
- **Physical Meaning:** Energy purely attributable to adhesion forces
- **Research Significance:** Removes systematic biases for more accurate material comparisons

### **Energy Dissipation (mJ)**
- **Definition:** Energy lost during the separation process (negative work regions)
- **Symbol:** W_dissipation
- **Units:** Millijoules (mJ)
- **Calculation:** `W_dissipation = ∫ min(0, F(z)) dz` (negative portions only)
- **Physical Meaning:** Energy lost to damping, friction, or elastic rebound
- **Research Significance:** Indicates viscoelastic behavior and energy loss mechanisms

### **Total Energy (mJ)**
- **Definition:** Sum of all energy components (positive and negative work)
- **Symbol:** W_total
- **Units:** Millijoules (mJ)
- **Calculation:** `W_total = W_adhesion + |W_dissipation|`
- **Physical Meaning:** Total energy involved in the separation process
- **Research Significance:** Complete energy balance for the peeling event

### **Energy Density (mJ/mm)**
- **Definition:** Work of adhesion normalized by travel distance
- **Symbol:** ρ_energy
- **Units:** Millijoules per millimeter (mJ/mm)
- **Calculation:** `ρ_energy = W_adhesion / (z_end - z_start)`
- **Physical Meaning:** Energy required per unit of separation distance
- **Research Significance:** Allows comparison across different layer thicknesses and peel distances

---

## Temporal Analysis Metrics

### **Pre-Initiation Time (s)**
- **Definition:** Duration of the Pre-Initiation phase (force buildup period)
- **Symbol:** t_pre_initiation
- **Units:** Seconds (s)
- **Calculation:** `t_pre_initiation = t_initiation - t_baseline_crossing`
- **Physical Meaning:** Time scale for elastic deformation and stress concentration buildup
- **Research Significance:** Characterizes adhesion loading dynamics and material response time
- **Stage Association:** Corresponds to **Pre-Initiation Phase** of sawtooth pattern

### **Peel Time (s)**
- **Definition:** Duration of the Propagation phase (crack propagation period)
- **Symbol:** t_propagation
- **Units:** Seconds (s)
- **Calculation:** `t_propagation = t_propagation_end - t_initiation`
- **Physical Meaning:** Time scale for rapid crack growth and complete bond failure
- **Research Significance:** Indicates separation dynamics and catastrophic failure characteristics
- **Stage Association:** Corresponds to **Propagation Phase** of sawtooth pattern

### **Total Peel Time (s)**
- **Definition:** Complete duration of the adhesion separation event
- **Symbol:** t_total_peel
- **Units:** Seconds (s)
- **Calculation:** `t_total_peel = t_pre_initiation + t_propagation`
- **Physical Meaning:** Overall time scale for complete layer separation process
- **Research Significance:** Process efficiency metric and temporal characterization
- **Stage Association:** Covers **Pre-Initiation + Propagation** phases (complete sawtooth)

---

## Spatial Analysis Metrics

### **Distance to Peel Start (mm)**
- **Definition:** Z-axis travel distance during the Pre-Initiation phase
- **Symbol:** Δz_pre_initiation
- **Units:** Millimeters (mm)
- **Calculation:** `Δz_pre_initiation = z_initiation - z_baseline_crossing`
- **Physical Meaning:** Spatial distance over which elastic deformation and stress buildup occurs
- **Research Significance:** Characterizes the geometric scale of adhesion loading
- **Stage Association:** Corresponds to **Pre-Initiation Phase** spatial extent

### **Peak Force Position (mm)**
- **Definition:** Z-axis position at maximum force
- **Symbol:** z_peak
- **Units:** Millimeters (mm)
- **Physical Meaning:** Location of maximum adhesive resistance
- **Research Significance:** Characterizes spatial distribution of adhesion

### **Peel Completion Position (mm)**
- **Definition:** Z-axis position where separation is complete (detected via second derivative maximum)
- **Symbol:** z_completion
- **Units:** Millimeters (mm)
- **Physical Meaning:** Spatial endpoint of the separation process
- **Research Significance:** Total separation distance measurement

### **Peel Distance (mm)**
- **Definition:** Total Z-axis travel during peeling
- **Symbol:** Δz_peel
- **Units:** Millimeters (mm)
- **Calculation:** `Δz_peel = z_completion - z_initiation`
- **Physical Meaning:** Physical distance over which separation occurs
- **Research Significance:** Geometric characterization of the peel process

---

## Dynamic Analysis Metrics

### **Maximum Loading Rate (N/s)**
- **Definition:** Fastest rate of force increase during peel initiation
- **Symbol:** dF/dt_max_loading
- **Units:** Newtons per second (N/s)
- **Calculation:** `max(diff(force_data) / diff(time_data))` during loading phase
- **Physical Meaning:** Rate of adhesion buildup or applied loading
- **Research Significance:** Characterizes adhesion dynamics and loading sensitivity

### **Maximum Unloading Rate (N/s)**
- **Definition:** Fastest rate of force decrease after peak
- **Symbol:** dF/dt_max_unloading
- **Units:** Newtons per second (N/s)
- **Calculation:** `min(diff(force_data) / diff(time_data))` during unloading phase
- **Physical Meaning:** Rate of adhesion release or separation speed
- **Research Significance:** Indicates bond failure dynamics and release mechanisms

### **Adhesion Stiffness (N/mm)**
- **Definition:** Force-displacement slope during initial adhesion loading
- **Symbol:** k_adhesion
- **Units:** Newtons per millimeter (N/mm)
- **Calculation:** `slope(force_data, position_data)` in linear loading region
- **Physical Meaning:** Mechanical stiffness of the adhesive interface
- **Research Significance:** Material property indicating adhesion rigidity

---

## Data Quality Metrics

### **Force Signal-to-Noise Ratio**
- **Definition:** Ratio of peak force signal to background noise level
- **Symbol:** SNR_force
- **Units:** Dimensionless (dB optional)
- **Calculation:** `SNR = (F_peak - F_baseline) / σ_noise`
- **Physical Meaning:** Quality indicator for force measurements
- **Research Significance:** Validates measurement reliability and sensor performance

### **Measurement Confidence Level**
- **Definition:** Statistical confidence in the measured values
- **Symbol:** CI
- **Units:** Percentage (%)
- **Calculation:** Based on signal quality, noise level, and data consistency
- **Physical Meaning:** Reliability estimate for the measurements
- **Research Significance:** Data quality assurance for research conclusions

---

## Environmental and System Metrics

### **Temperature Drift Correction**
- **Definition:** Compensation for thermal effects on force measurements
- **Symbol:** ΔF_thermal
- **Units:** Newtons (N)
- **Calculation:** Linear or polynomial drift correction over time
- **Physical Meaning:** Accounts for thermal expansion and sensor drift
- **Research Significance:** Ensures measurement accuracy across extended experiments

### **System Timestamp (s)**
- **Definition:** Absolute time reference for all measurements
- **Symbol:** t_system
- **Units:** Seconds (s) since experiment start
- **Physical Meaning:** Temporal correlation with other system events
- **Research Significance:** Enables correlation with DLP exposure, stage movement, and other processes

---

## Layer-Specific Metrics

### **Layer Number**
- **Definition:** Sequential layer identifier in the print sequence
- **Symbol:** L
- **Units:** Dimensionless integer
- **Physical Meaning:** Position in the vertical build sequence
- **Research Significance:** Enables layer-by-layer analysis and build progression tracking

### **Cumulative Build Height (mm)**
- **Definition:** Total build height at the time of this layer's analysis
- **Symbol:** h_cumulative
- **Units:** Millimeters (mm)
- **Calculation:** Sum of all previous layer thicknesses
- **Physical Meaning:** Absolute position in the printed part
- **Research Significance:** Correlates adhesion behavior with build progression

---

## Usage Notes

### **Data Collection Requirements**
- Minimum sampling rate: 25 Hz (40 ms intervals)
- Recommended sampling rate: 50 Hz (20 ms intervals)
- Force resolution: ±0.001 N or better
- Position resolution: ±0.001 mm or better

### **Calculation Sequence**
1. Load raw force and position data
2. Apply current smoothing method (Savitzky-Golay filter)
3. Identify peel initiation and peak events
4. Detect propagation end using second derivative maximum
5. Apply baseline correction
6. Calculate temporal metrics
7. Calculate spatial metrics
8. Compute work and energy values
9. Analyze dynamic properties
10. Assess data quality

### **Quality Control Checks**
- Verify SNR > 10 for reliable measurements
- Check for data completeness (no missing samples during peel)
- Validate temporal sequence (initiation < peak < completion)
- Confirm positive work values for adhesion
- Review baseline stability
- Verify second derivative calculation validity

---

## Future Enhancements

### **Planned Additions**
- **Frequency Domain Analysis:** FFT-based oscillation characterization
- **Viscoelastic Modeling:** Time-dependent adhesion behavior
- **Multi-Layer Correlation:** Cross-layer adhesion pattern analysis
- **Process Parameter Integration:** Correlation with exposure time, intensity, etc.

### **Advanced Metrics Under Development**
- **Adhesion Fatigue Index:** Layer-to-layer degradation measure
- **Spatial Adhesion Mapping:** Position-dependent adhesion characterization
- **Dynamic Baseline Tracking:** Real-time baseline adaptation
- **Predictive Quality Metrics:** Early failure detection indicators

---

**Document Status:** Living document - updated as new metrics are developed and validated  
**Review Schedule:** Monthly review and updates as research progresses  
**Contact:** Cheng Sun Lab for questions or metric definition clarifications