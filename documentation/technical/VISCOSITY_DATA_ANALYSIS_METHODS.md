# Data Analysis and System Identification Methods for In-Situ Viscometry
**Mathematical Formulations, Regression Solvers, and Signal Conditioning Pipeline**

---

**Document Version:** 1.0  
**Date:** September 2026  
**Authors:** Cheng Sun Lab Team  
**System:** Prince Segmented DLP 3D-Printer  

---

## 1. Overview & Data Flow Pipeline

The in-situ squeeze-flow viscometry system operates on synchronized time-series data acquired from the Zaber linear stage position encoder $z(t)$ and the Phidget bridge load cell $F(t)$.

```
[Raw Sensors] ---> [Signal Conditioning] ---> [Regime Gating] ---> [Mathematical Solvers] ---> [Metrics Dashboard]
Zaber: z(t)        - Dynamic Tare             - Cutoff: h > 150µm   - Linearized Stefan        - Viscosity µ (cP)
Phidget: F(t)      - Decimation / S-G Filter  - Compliance reject   - Lumped EHL Fit           - Flow Index n
                   - Velocity verify: v = -ż                        - Multi-Speed Power Law    - Contact z_0 (mm)
                                                                    - Reference Transfer Fn    - Quality R²
```

This document details the signal conditioning algorithms, regression mathematics, regime gating criteria, and failure detection logic implemented in `support_modules/viscosity_analyzer.py`.

---

## 2. Signal Conditioning & Pre-Processing Pipeline

### 2.1 Dynamic Stationary Tare (Buoyancy & Meniscus Removal)
Before the stage begins its downward diagnostic approach, it dwells stationary at the starting height (e.g. $z = 2.0\text{ mm}$ above nominal vat bottom) for $T_{\text{tare}} = 0.5\text{ s}$ ($20-50$ samples):
$$F_{\text{tare}} = \frac{1}{N_{\text{tare}}} \sum_{i=1}^{N_{\text{tare}}} F_{\text{raw}}(t_i)$$
The hydrodynamic force is then zero-referenced:
$$F_{\text{hydro}}(t) = F_{\text{raw}}(t) - F_{\text{tare}}$$
This automatically cancels out the weight of the stage, static liquid buoyancy ($\rho g V_{\text{submerged}}$), cable tension offsets, and thermal zero-drift of the strain gauge.

### 2.2 Velocity Verification & Filtering
Because Stefan's equation assumes steady descent velocity $v = -\frac{dz}{dt}$:
1. The instantaneous velocity is estimated via central finite differences:
   $$v(t_i) = -\frac{z(t_{i+1}) - z(t_{i-1})}{t_{i+1} - t_{i-1}}$$
2. Data points during stage acceleration and deceleration phases are excluded:
   $$\left| \frac{v(t_i) - v_{\text{target}}}{v_{\text{target}}} \right| \le 0.05 \quad (5\%\text{ velocity tolerance})$$

### 2.3 Noise Filtering
The load cell signal is conditioned using a 2nd-order Savitzky-Golay polynomial filter (window length $11-15$ points):
- Smooths 60 Hz electrical pickup and mechanical stage motor vibration.
- Preserves the sharp, non-linear curvature of hydrodynamic force buildup without peak attenuation or phase distortion.

---

## 3. Mathematical Solvers & Regression Formulations

### 3.1 Method 1: Linearized Stefan Transformation ($F^{-1/3}$ vs. $z$)

#### Physical Principle:
Stefan's squeeze equation for a circular disk of diameter $D$:
$$F = \frac{3\pi D^4 \mu v}{32 (z - z_0)^3}$$
where $z$ is the current stage coordinate, and $z_0$ is the virtual zero-gap coordinate (datum).

Defining the transformation:
$$Y_i = F_{\text{hydro}}(t_i)^{-1/3}$$
The governing relation becomes strictly linear in $z$:
$$Y_i = m \cdot z_i + c$$
where:
$$m = \left(\frac{32}{3\pi D^4 \mu v}\right)^{1/3}$$
$$c = -m \cdot z_0$$

#### Analytical Solution via Ordinary Least Squares (OLS):
Given $N$ data points in the valid hydrodynamic regime $(z_i, Y_i)$:
$$\bar{z} = \frac{1}{N} \sum z_i, \quad \bar{Y} = \frac{1}{N} \sum Y_i$$
$$\text{Slope } m = \frac{\sum (z_i - \bar{z})(Y_i - \bar{Y})}{\sum (z_i - \bar{z})^2}$$
$$\text{Intercept } c = \bar{Y} - m \bar{z}$$

From the fitted slope $m$ and intercept $c$, the physical metrics are directly extracted:
$$\text{Virtual Zero-Gap Coordinate: } z_0 = -\frac{c}{m}$$
$$\text{Dynamic Viscosity: } \mu = \frac{32}{3\pi D^4 \cdot v \cdot m^3}$$

#### Goodness-of-Fit Metric:
$$R^2 = 1 - \frac{\sum (Y_i - (m z_i + c))^2}{\sum (Y_i - \bar{Y})^2}$$
An $R^2 \ge 0.985$ indicates excellent agreement with Newtonian squeeze flow without significant membrane interference.

---

### 3.2 Method 2: Lumped Compliance Regression (Simultaneous $\mu$, $z_0$, and $k_{\text{eff}}$)

When the stage approaches closer to the membrane ($h < 100\ \mu\text{m}$), the membrane deflects downward under hydrodynamic pressure by $w \approx F / k_{\text{eff}}$.

The true physical gap is:
$$h_{\text{actual}} = (z - z_0) + \frac{F}{k_{\text{eff}}}$$
Equating to Stefan's equation:
$$\left(\frac{C_{\text{geom}} \mu v}{F}\right)^{1/3} = (z - z_0) + \frac{F}{k_{\text{eff}}}$$
Rearranging for $z$ as the dependent variable:
$$z = z_0 + (C_{\text{geom}} \mu v)^{1/3} \cdot F^{-1/3} - \left(\frac{1}{k_{\text{eff}}}\right) \cdot F$$

#### Multivariate Linear Form:
$$z = \beta_0 + \beta_1 X_1 + \beta_2 X_2$$
where:
* Predictor 1: $X_1 = F^{-1/3}$
* Predictor 2: $X_2 = -F$
* Unknown parameters:
  $$\beta_0 = z_0 \quad (\text{virtual datum})$$
  $$\beta_1 = (C_{\text{geom}} \mu v)^{1/3} \implies \mu = \frac{\beta_1^3}{C_{\text{geom}} v}$$
  $$\beta_2 = \frac{1}{k_{\text{eff}}} = C_{\text{sys}} \quad (\text{effective system compliance in mm/N})$$

Solving via normal equations $\mathbf{\beta} = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{z}$:
This method simultaneously decouples the fluid viscosity $\mu$ from the membrane compliance $k_{\text{eff}}$ without requiring prior knowledge of membrane tension!

---

### 3.3 Method 3: Multi-Speed Probing & Non-Newtonian Power-Law Solver

To test for non-Newtonian behavior, the stage performs two or three consecutive approaches at distinct constant velocities:
$$v_1 < v_2 < v_3 \quad (\text{e.g., } 0.5\text{ mm/s}, 1.0\text{ mm/s}, 2.0\text{ mm/s})$$

#### Flow Behavior Index ($n$):
For power-law fluids ($\tau = K \dot{\gamma}^n$), the squeeze force at identical gap heights $h^*$ scales as:
$$F(h^*, v) = C_K(h^*) \cdot v^n \implies \ln F = \ln C_K + n \ln v$$

Fitting $\ln F$ versus $\ln v$ across the velocities:
$$n = \frac{\sum (\ln v_j - \overline{\ln v})(\ln F_j - \overline{\ln F})}{\sum (\ln v_j - \overline{\ln v})^2}$$

#### Rheological Classification Logic:
1. **$0.95 \le n \le 1.05$:** Confirmed **Newtonian**.
   - Report dynamic viscosity: $\mu$ ($\text{mPa}\cdot\text{s}$ or cP).
2. **$n < 0.95$:** Confirmed **Shear-Thinning (Pseudoplastic)**.
   - Report flow index $n$ and consistency index $K$.
   - Compute apparent viscosity $\eta_{\text{app}}$ at printing shear rate:
     $$\dot{\gamma}_{\text{print}} \approx \frac{3 v_{\text{print}} R}{h_{\text{layer}}^2}$$
     $$\eta_{\text{app}}(\dot{\gamma}_{\text{print}}) = K \dot{\gamma}_{\text{print}}^{n-1}$$
3. **$n > 1.05$:** Dilatant (rare; indicates turbulent drag, particle jamming, or measurement artifact).

---

### 3.4 Method 4: Daily Reference Precalibration Transfer Function

To establish high-accuracy measurements that completely bypass geometric tilt, non-ideal edge geometry, and steady boundary deviations:

1. **Precalibration Scan (Reference Liquid):**
   Run the probe with a known calibration liquid (e.g. PEG 400, Glycerol-water standard, or silicone oil) of certified viscosity $\mu_{\text{ref}}$ at measured temperature $T$:
   $$K_{\text{vat}}(z_i) \equiv \frac{F_{\text{ref}}(z_i)}{v_{\text{ref}} \cdot \mu_{\text{ref}}}$$
   $K_{\text{vat}}(z)$ represents the empirical hydraulic transfer function of the specific vat/membrane configuration.

2. **Resin Measurement:**
   When probing resin at velocity $v_{\text{resin}}$:
   $$\mu_{\text{resin}} = \frac{1}{M} \sum_{i=1}^M \frac{F_{\text{resin}}(z_i)}{v_{\text{resin}} \cdot K_{\text{vat}}(z_i)}$$

Because $K_{\text{vat}}(z_i)$ contains the exact system response under identical boundary conditions, this ratio approach delivers high precision with minimal mathematical modeling overhead.

---

## 4. Pre-Fluid Dry Membrane Touch Detection Algorithm

Before resin is added (or on a dry, cleaned membrane), the pre-fluid check detects the dry mechanical touch point and measures membrane stiffness:

1. **Approach Kinematics:** Stage descends in air at $v_{\text{dry}} = 50\ \mu\text{m/s}$ (slow to avoid impact).
2. **Touch Detection Criterion:**
   $$F(t) - F_{\text{tare}} \ge F_{\text{touch\_thresh}} \quad (\text{default: } 0.03\text{ N})$$
   Stage position at trigger: $z_{\text{dry\_touch}}$.
3. **Stiffness Identification ($k_{\text{membrane}}$):**
   Stage advances an additional $50\ \mu\text{m}$ into the membrane while logging $(z, F)$.
   $$k_{\text{membrane}} = \left| \frac{dF}{dz} \right| = \frac{\sum (z_i - \bar{z})(F_i - \bar{F})}{\sum (z_i - \bar{z})^2} \quad (\text{N/mm})$$
4. **Safety & Abort Limit:**
   If $F \ge 2.0\text{ N}$ during dry touch, the stage immediately halts and retracts $1.0\text{ mm}$ to protect the load cell and membrane.

---

## 5. Regime Gating & Data Integrity Validation

To ensure robust results without user intervention, the analyzer applies an automated 5-step data validation filter:

| Step | Validation Rule | Action if Failed |
| :---: | :--- | :--- |
| **1** | Minimum hydrodynamic force: $F_{\text{hydro}} \ge 0.05\text{ N}$ | Exclude baseline noise points at large gaps ($h > 400\ \mu\text{m}$) |
| **2** | Upper force limit: $F_{\text{hydro}} \le 15.0\text{ N}$ | Truncate descent before mechanical collision or excessive bulging |
| **3** | Squeeze window: $150\ \mu\text{m} \le h \le 350\ \mu\text{m}$ | Focus regression on asymptotic rigid regime |
| **4** | Monotonicity: $\frac{dF}{dt} > 0$ during descent | Discard points affected by bubble escape or mechanical stick-slip |
| **5** | Fit quality: $R^2 \ge 0.95$ on linearized Stefan regression | Flag warning: `"Low confidence fit: check membrane or tilt"` |
