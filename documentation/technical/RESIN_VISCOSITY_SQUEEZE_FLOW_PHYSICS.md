# Theory of In-Situ Squeeze-Flow Viscometry in Vat Photopolymerization
**Research-Grade Hydrodynamic and Elastohydrodynamic Modeling for Prince 3D-Printer**

---

**Document Version:** 1.0  
**Date:** September 2026  
**Authors:** Cheng Sun Lab Team  
**System:** Prince Segmented DLP 3D-Printer  
**Hardware Specifications:** $\varnothing 12.7\text{ mm}$ ($\frac{1}{2}\text{ inch}$) Circular Aluminum Stage, Phidget Bridge Load Cell, Zaber High-Precision Linear Stage  

---

## 1. Executive Summary & Physical Problem Statement

In top-down or bottom-up stereolithography (SLA / DLP / CLIP), measuring the uncured resin's dynamic viscosity $\mu$ directly on the printing apparatus immediately prior to exposure provides a vital quality-control metric. Resins undergo batch-to-batch variation, thermal viscosity shifts (typically $2 - 5\%$ per $^\circ\text{C}$), solvent evaporation, and age-related oligomer degradation.

When the build platform approaches the bottom of the vat containing liquid resin, the fluid is squeezed radially outward. By synchronously recording the vertical stage trajectory $z(t)$, velocity $v(t) = -\dot{z}(t)$, and normal force $F(t)$, the setup acts as an **in-situ squeeze-flow rheometer**.

This document details the rigorous physics governing this measurement:
1. **Classical Stefan squeeze flow** between rigid parallel circular plates.
2. **Elastohydrodynamic Lubrication (EHL)** arising from membrane compliance (FEP / PFA film or PDMS layer).
3. **Boundary conditions** at low-energy fluoropolymer interfaces (Navier slip vs. apparent slip vs. compliance).
4. **Non-Newtonian power-law rheology** and the mechanics of multi-speed probing.
5. **Pre-fluid dry membrane touch mechanics** for establishing true zero-gap ($z_0$) and baseline membrane stiffness ($k_{\text{membrane}}$).
6. **Reference calibration standards** suitable for standard laboratory settings (Glycerol, Glycerol-Water mixtures, PEG 400, Propylene Glycol).

---

## 2. Classical Hydrodynamic Squeeze Flow (Stefan Equation)

### 2.1 Geometric System Definition
* Build Stage: Flat, solid aluminum cylinder of diameter $D = 12.7\text{ mm}$ (radius $R = 6.35\text{ mm} = 6.35 \times 10^{-3}\text{ m}$).
* Surface Area: $A = \pi R^2 \approx 1.2668 \times 10^{-4}\text{ m}^2$ ($126.68\text{ mm}^2$).
* Vat Floor: Flat vat window / membrane.
* Instantaneous Gap: $h(t) \ll R$.
* Coordinate System: Cylindrical coordinates $(r, \theta, z')$, where $z' \in [0, h(t)]$ is the vertical gap coordinate, and $r \in [0, R]$ is the radial position.

```
       Aluminum Build Stage (Radius R = 6.35 mm)
      +-----------------------------------------+
      |                                         |  | v = -dh/dt
      +--------------------+--------------------+  v
                           |
          Fluid Flow  <--- | --->  Fluid Flow
                     ======+======                  Gap h(t)
      -------------------------------------------
               Vat Floor / Elastic Membrane
```

### 2.2 Derivation from Navier-Stokes Equations
Because the gap height is small compared to the plate diameter ($h/R \sim 10^{-2}$ to $10^{-3}$), the flow satisfies the **lubrication approximation** (Reynolds number $Re = \frac{\rho v h}{\mu} \ll 1$ and reduced Reynolds number $Re^* = Re \cdot (h/R) \ll 1$).

Under these conditions:
1. Pressure is uniform across the gap thickness: $\frac{\partial P}{\partial z'} \approx 0 \implies P = P(r, t)$.
2. Inertial terms are negligible compared to viscous forces.
3. Flow is axisymmetric: $\frac{\partial}{\partial \theta} = 0$, $u_\theta = 0$.

The radial momentum equation reduces to:
$$\frac{\partial P}{\partial r} = \mu \frac{\partial^2 u_r}{\partial z'^2}$$

Integrating twice with respect to $z'$ with standard **no-slip boundary conditions** ($u_r(z'=0) = 0$ and $u_r(z'=h) = 0$):
$$u_r(r, z') = \frac{1}{2\mu} \frac{\partial P}{\partial r} z' (z' - h)$$

The local shear rate within the gap is:
$$\dot{\gamma}(r, z') = \left| \frac{\partial u_r}{\partial z'} \right| = \frac{1}{2\mu} \left| \frac{\partial P}{\partial r} \right| |2z' - h|$$
The shear rate is zero at the midplane ($z' = h/2$) and reaches its maximum at the solid boundaries ($z' = 0$ and $z' = h$).

The volumetric radial flow rate $Q(r)$ across a cylindrical surface of radius $r$ is:
$$Q(r) = \int_0^h 2\pi r u_r(r, z') dz' = 2\pi r \frac{1}{2\mu} \frac{\partial P}{\partial r} \left[ \frac{z'^3}{3} - \frac{h z'^2}{2} \right]_0^h = -\frac{\pi r h^3}{6\mu} \frac{\partial P}{\partial r}$$

By conservation of mass for an incompressible fluid, the volume squeezed out per unit time by the circular area $\pi r^2$ descending at speed $v = -\frac{dh}{dt}$ must equal $Q(r)$:
$$Q(r) = \pi r^2 v$$

Equating the two expressions:
$$\pi r^2 v = -\frac{\pi r h^3}{6\mu} \frac{\partial P}{\partial r} \implies \frac{\partial P}{\partial r} = -\frac{6\mu v r}{h^3}$$

Integrating from radial coordinate $r$ out to the rim $R$, where the pressure matches ambient / reservoir pressure ($P(R) = 0$ gauge):
$$P(r) = \int_r^R \frac{6\mu v r'}{h^3} dr' = \frac{3\mu v}{h^3} (R^2 - r^2)$$

#### Maximum Pressure (Center of Stage):
$$P_{max} = P(0) = \frac{3\mu v R^2}{h^3}$$

The total hydrodynamic upward squeeze force $F_{squeeze}$ exerted on the circular build stage is obtained by integrating $P(r)$ over the disk area:
$$F_{squeeze} = \int_0^R P(r) \cdot 2\pi r dr = \frac{6\pi \mu v}{h^3} \int_0^R (R^2 r - r^3) dr = \frac{6\pi \mu v}{h^3} \left[ \frac{R^4}{2} - \frac{R^4}{4} \right] = \frac{3\pi \mu R^4 v}{2 h^3}$$

Expressed in terms of stage diameter $D = 2R = 12.7\text{ mm}$:
$$F_{squeeze} = \frac{3\pi \mu D^4 v}{32 h^3}$$

### 2.3 Numerical Evaluation for the $\varnothing 12.7\text{ mm}$ Stage
$$D = 0.0127\text{ m} \implies D^4 \approx 2.6014 \times 10^{-8}\text{ m}^4$$
$$C_{geom} = \frac{3\pi D^4}{32} \approx 7.662 \times 10^{-9}\text{ m}^4$$

$$F(h, v, \mu) \approx 7.662 \times 10^{-9} \cdot \frac{\mu \cdot v}{h^3} \quad [F\text{ in N, }\mu\text{ in Pa}\cdot\text{s, }v\text{ in m/s, }h\text{ in m}]$$

#### Force and Center Pressure Table ($\mu = 0.5\text{ Pa}\cdot\text{s} = 500\text{ cP}$, $v = 1.0\text{ mm/s} = 10^{-3}\text{ m/s}$):
| Gap $h$ ($\mu\text{m}$) | Squeeze Force $F$ (N) | Center Pressure $P(0)$ (kPa) | Rim Shear Rate $\dot{\gamma}_{rim}$ ($\text{s}^{-1}$) |
| :---: | :---: | :---: | :---: |
| $500\ \mu\text{m}$ | $0.031\text{ N}$ | $0.48\text{ kPa}$ | $76\text{ s}^{-1}$ |
| $300\ \mu\text{m}$ | $0.142\text{ N}$ | $2.24\text{ kPa}$ | $212\text{ s}^{-1}$ |
| $200\ \mu\text{m}$ | $0.479\text{ N}$ | $7.56\text{ kPa}$ | $476\text{ s}^{-1}$ |
| $150\ \mu\text{m}$ | $1.135\text{ N}$ | $17.92\text{ kPa}$ | $847\text{ s}^{-1}$ |
| $100\ \mu\text{m}$ | $3.831\text{ N}$ | $60.48\text{ kPa}$ | $1905\text{ s}^{-1}$ |
| $75\ \mu\text{m}$  | $9.081\text{ N}$ | $143.35\text{ kPa}$ | $3387\text{ s}^{-1}$ |
| $50\ \mu\text{m}$  | $30.648\text{ N}$ | $483.84\text{ kPa}$ | $7620\text{ s}^{-1}$ |

---

## 3. Membrane Compliance & Elastohydrodynamic Lubrication (EHL)

### 3.1 The Physical Mechanism of Membrane Deflection
In practical DLP/SLA printers, the vat floor is not an infinitely rigid glass block. It is either:
1. A **tensioned polymeric membrane** (FEP, PFA, or Teflon AF, typically $50 - 125\ \mu\text{m}$ thick, under pre-tension $T$).
2. A **PDMS silicone elastomeric deadzone layer** (thickness $d \sim 1 - 4\text{ mm}$, Young's modulus $E \sim 1 - 3\text{ MPa}$) adhered to a rigid glass window.
3. An unsupported flexible window with both tension and bending rigidity.

When the build stage descends, positive hydrodynamic pressure develops under the stage, peaking at the center ($r = 0$). This pressure pushes the membrane downward:
$$w(r, t) \ge 0$$
The actual gap profile is therefore **spatially non-uniform**:
$$h(r, t) = h_0(t) + w(r, t)$$
where $h_0(t)$ is the nominal rigid gap at the rim ($r = R$), and $w(r, t)$ is the local downward deflection of the membrane.

```
       Rigid Aluminum Stage
   +---------------------------+
   |                           |  | v
   +-------------+-------------+  v
                 | h_0
        w(r)  \  |  /  Bulging
   ~~~~~~~~~~~~\___/~~~~~~~~~~~~   Compliant Membrane
   =============================   Rigid Window Base
```

### 3.2 Coupling with Reynolds Lubrication
The coupled elastohydrodynamic equation in cylindrical coordinates is:
$$\frac{1}{r} \frac{\partial}{\partial r} \left( r [h_0 + w(r)]^3 \frac{\partial P}{\partial r} \right) = 12 \mu \frac{\partial (h_0 + w)}{\partial t}$$

For a tensioned membrane with tension $T$ (N/m), the mechanical deflection equation is:
$$T \left( \frac{d^2 w}{dr^2} + \frac{1}{r} \frac{dw}{dr} \right) = -P(r)$$

For an elastic PDMS layer on glass, the deflection is locally proportional to pressure (Winkler foundation):
$$w(r) \approx \frac{P(r) \cdot d_{PDMS}}{E_{PDMS}}$$

### 3.3 The Two Regimes of Squeeze Flow
Because the hydraulic resistance scales as $[h_0 + w(r)]^{-3}$, the fluid flow responds nonlinearly to deflection:

1. **The Asymptotic Rigid Regime ($h_0 \ge 150\ \mu\text{m}$):**
   - Hydrodynamic pressures are moderate ($P_{max} < 20\text{ kPa}$).
   - Membrane deflection is tiny: $w(0) \ll h_0$ (typically $w(0) < 3\ \mu\text{m}$ vs $h_0 \ge 150\ \mu\text{m}$, ratio $< 2\%$).
   - In this regime, the rigid Stefan equation holds to within $< 2-4\%$ accuracy!
   - **Crucial engineering conclusion:** Squeeze-flow viscometry does *not* need to be conducted at layer thicknesses ($30-50\ \mu\text{m}$). Conducting the probe in the $150 - 350\ \mu\text{m}$ window allows treating the system as effectively rigid.

2. **The Compliant / EHL Regime ($h_0 < 75\ \mu\text{m}$):**
   - High pressures ($P > 100\text{ kPa}$) cause significant membrane bulging ($w(0) \sim h_0$).
   - Bulging opens an escape channel in the center, dramatically attenuating the pressure peak and flattening the force curve compared to the theoretical $h^{-3}$ singularity.
   - The force departs from the linear $F^{-1/3}$ curve.

### 3.4 Lumped Compliance Model
To account for both membrane compliance and load cell cantilever flexure across the full range, we define an effective total system stiffness $k_{\text{eff}}$:
$$h_{\text{actual}}(t) = h_{\text{nominal}}(t) + \frac{F(t)}{k_{\text{eff}}}$$
where $k_{\text{eff}}^{-1} = k_{\text{membrane}}^{-1} + k_{\text{loadcell}}^{-1} + k_{\text{stage}}^{-1}$.

Substituting $h_{\text{actual}}$ into Stefan's equation:
$$F = \frac{C_{\text{geom}} \mu v}{\left(h_{\text{nom}} + \frac{F}{k_{\text{eff}}}\right)^3}$$
Taking the cube root and rearranging:
$$h_{\text{nom}} = \left(\frac{C_{\text{geom}} \mu v}{F}\right)^{1/3} - \frac{F}{k_{\text{eff}}}$$
Because $h_{\text{nom}} = z - z_0$ (where $z$ is the linear stage coordinate, and $z_0$ is the virtual zero-gap coordinate):
$$z = z_0 + (C_{\text{geom}} \mu v)^{1/3} \cdot F^{-1/3} - \left(\frac{1}{k_{\text{eff}}}\right) F$$

This formulation enables a simultaneous, linear 3-parameter fit ($z_0$, $\mu$, and $k_{\text{eff}}$) from a single experimental squeeze curve!

---

## 4. Boundary Conditions: Navier Slip vs. No-Slip on Fluoropolymers

### 4.1 Molecular Slip (Navier Slip Boundary Condition)
On hydrophobic, low-surface-energy fluoropolymer substrates (such as FEP, PTFE, PFA), fluid molecules can exhibit finite interfacial slip. The Navier slip condition relates the slip velocity $u_{slip}$ to the wall shear rate:
$$u_{slip} = \left. b \frac{\partial u}{\partial z'} \right|_{wall}$$
where $b$ is the **Navier slip length**.

For squeeze flow between parallel plates where the upper plate (aluminum) satisfies no-slip ($b=0$) and the lower plate (membrane) has slip length $b$:
$$F_{slip} = F_{no-slip} \cdot f(b/h)$$

Using the asymptotic derivation by Vinogradova (1995) and Lauga & Brenner (2007) for $h \gg b$:
$$f(b/h) \approx 1 - \frac{3b}{h}$$

### 4.2 Scale Comparison: True Slip vs. Compliance
* For macromolecular polymer systems (SLA acrylate monomers, oligomers, photoinitiators) flowing over smooth FEP:
  $$\text{Molecular slip length } b \approx 10\text{ nm to } 100\text{ nm} = 10^{-8}\text{ to } 10^{-7}\text{ m}$$
* Working gap during viscometry:
  $$h \approx 150\ \mu\text{m} = 1.5 \times 10^{-4}\text{ m}$$
* Relative correction:
  $$\frac{3b}{h} \approx \frac{3 \times 10^{-7}\text{ m}}{1.5 \times 10^{-4}\text{ m}} = 0.002 = 0.2\%$$

**Conclusion:** The effect of true molecular slip on the measured squeeze force is **$< 0.3\%$**, which is well below the experimental measurement uncertainty ($1-2\%$). Therefore, the departure of the force curve from the classical Stefan model at small gaps is overwhelmingly caused by **membrane elastohydrodynamic compliance**, not hydrodynamic slip.

### 4.3 Apparent Slip (Depletion Layer / Micro-Bubbles)
If an apparent slip layer exists—for example, due to a microscopic monomer depletion zone or entrapped micro-bubbles at the FEP surface:
- It acts as a thin, low-viscosity lubricating film of thickness $\delta$ and viscosity $\mu_{wall} < \mu_{bulk}$.
- The effective slip length is $b_{\text{eff}} \approx \delta (\frac{\mu_{bulk}}{\mu_{wall}} - 1)$.
- Because this interface remains constant between runs, its influence is automatically captured and normalized out by the **daily reference precalibration** method.

---

## 5. Non-Newtonian Rheology & Multi-Speed Probing Kinematics

### 5.1 Power-Law (Ostwald-de Waele) Model
While standard unfilled photopolymers are nearly Newtonian, composite, ceramic, or heavily pigmented resins exhibit shear-thinning (pseudoplastic) behavior.
$$\tau = K \dot{\gamma}^n$$
where:
* $K$ is the flow consistency index ($\text{Pa}\cdot\text{s}^n$).
* $n$ is the flow behavior index (dimensionless):
  - $n = 1$: Newtonian fluid ($K = \mu$).
  - $n < 1$: Shear-thinning (pseudoplastic).
  - $n > 1$: Shear-thickening (dilatant).

### 5.2 Squeeze Flow for Power-Law Fluids
Solving the lubrication equations with $\tau_{rz'} = K \left|\frac{\partial u_r}{\partial z'}\right|^{n-1} \frac{\partial u_r}{\partial z'}$ yields the squeeze force equation for a circular disk of radius $R$:
$$F(h, v) = \left( \frac{2n+1}{n} \right)^n \frac{2\pi K R^{n+3}}{(n+3) h^{2n+1}} v^n$$

Notice the key scalings:
1. **Velocity scaling:** $F \propto v^n$ (in contrast to Newtonian $F \propto v^1$).
2. **Gap scaling:** $F \propto h^{-(2n+1)}$ (in contrast to Newtonian $F \propto h^{-3}$).

### 5.3 Decoupling Viscosity from Non-Newtonian Shear-Thinning
By testing at two or three distinct velocities ($v_1, v_2, v_3$) over the same gap window:
$$\frac{F(v_2)}{F(v_1)} = \left(\frac{v_2}{v_1}\right)^n \implies n = \frac{\ln[F(v_2) / F(v_1)]}{\ln(v_2 / v_1)}$$

* **Newtonian Confirmation:** If $n \in [0.96, 1.04]$, the resin is verified to be Newtonian. The dynamic viscosity $\mu$ is extracted directly using the standard Stefan solver.
* **Pseudoplastic Characterization:** If $n < 0.95$, the resin is shear-thinning. The solver reports both the flow index $n$ and the apparent viscosity $\eta_{app}(\dot{\gamma})$ at the relevant printing shear rate.

---

## 6. Pre-Fluid Dry Membrane Touch Mechanics

Before resin is dispensed (or on a clean, dry vat), performing a "dry touch" check provides essential structural baselines that eliminate downstream ambiguities.

```
       Aluminum Stage
      +--------------+
      |              |
      +------+-------+
             | z
             v
   - - - - - - - - - - - - - - -   z_0 (Initial touch point)
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   Membrane Deflection w
   =============================   Glass Backing
```

### 6.1 Mechanics of Dry Contact
When the dry aluminum stage descends into contact with the tensioned membrane in air:
1. **Zero Contact Detection ($z_{dry\_0}$):**
   - In air, hydrodynamic resistance is negligible ($\mu_{air} \approx 1.8 \times 10^{-5}\text{ Pa}\cdot\text{s}$, $F_{air} < 0.1\text{ mN}$).
   - The force gauge remains at its zero baseline until physical contact occurs.
   - Contact is detected when normal compressive force exceeds a sharp threshold (e.g. $\Delta F \ge 0.02\text{ N}$).
   - This defines the true, dry datum position $z_{dry\_0}$.

2. **Membrane Stiffness Measurement ($k_{\text{membrane}}$):**
   - Continuing the descent by a controlled, safe distance ($\Delta z \sim 50 - 100\ \mu\text{m}$) at low speed ($50\ \mu\text{m/s}$):
     $$F(z) = k_{\text{membrane}} \cdot (z_{dry\_0} - z)$$
   - The slope $\frac{dF}{dz}$ directly measures the combined mechanical stiffness of the tensioned membrane and load cell cantilever.

### 6.2 Value of the Pre-Fluid Check
* **Membrane Health & Tension Diagnostics:** Detects loose, sagging, or over-tensioned membranes before wasting expensive resin.
* **Stage Parallelism Check:** If the stage is tilted, the force slope exhibits an initial soft knee (point/edge contact) before transitioning to full-face contact.
* **Anchor for Hydrodynamic Modeling:** Once $z_{dry\_0}$ and $k_{\text{membrane}}$ are known from the dry check, they serve as fixed constraints in the hydrodynamic fitting algorithms, reducing the number of free regression parameters.

---

## 7. Laboratory Reference Calibration Standards

To perform reliable daily precalibration or transfer function calibration, reference fluids must be selected based on safety, cleanability, stability, and signal-to-noise ratio.

### 7.1 The Low-Viscosity Limitation: Water & Ethanol
At $20^\circ\text{C}$:
* Pure Water: $\mu = 1.002\text{ mPa}\cdot\text{s}$ ($1.002\text{ cP}$).
* Ethanol ($99.5\%$): $\mu = 1.20\text{ mPa}\cdot\text{s}$ ($1.20\text{ cP}$).

Under Stefan flow at $v = 1.0\text{ mm/s}$ and $h = 150\ \mu\text{m}$:
$$F_{water} = 7.662 \times 10^{-9} \cdot \frac{(1.002 \times 10^{-3}) \cdot 10^{-3}}{(1.5 \times 10^{-4})^3} \approx 0.0023\text{ N} = 2.3\text{ mN}$$

For standard load cells with $\pm 5 - 10\text{ mN}$ noise floors, a $2.3\text{ mN}$ signal yields poor signal-to-noise ($SNR \sim 1$). To use water or ethanol, the descent speed must be boosted to $v = 5 - 10\text{ mm/s}$ (producing $F \sim 15 - 25\text{ mN}$).

### 7.2 Recommended Laboratory Reference Fluids

The ideal calibration fluid for a vat photopolymerization laboratory should be:
1. **Completely water-soluble** (rinses cleanly off the stage and FEP with deionized water; no toxic solvents required).
2. **Strictly Newtonian** across all relevant shear rates.
3. **Non-volatile** (viscosity does not drift during measurement due to rapid evaporation).
4. **Viscosity in the range of $50 - 1000\text{ cP}$** (producing robust, high-SNR forces of $0.2 - 5.0\text{ N}$).

#### Recommended Fluids:
1. **Glycerol (Glycerin, 99.5%+):**
   - Viscosity: $\approx 1412\text{ mPa}\cdot\text{s}$ at $20^\circ\text{C}$; $\approx 945\text{ mPa}\cdot\text{s}$ at $25^\circ\text{C}$.
   - Non-toxic, food-grade, completely water-soluble.
2. **Glycerol-Water Binary Mixtures:**
   - Handily prepared in the lab to target any viscosity between $5\text{ cP}$ and $1000\text{ cP}$.
   - $80\%\text{ w/w Glycerol}$: $\approx 60.1\text{ cP}$ at $20^\circ\text{C}$.
   - $85\%\text{ w/w Glycerol}$: $\approx 109.0\text{ cP}$ at $20^\circ\text{C}$.
   - $90\%\text{ w/w Glycerol}$: $\approx 219.0\text{ cP}$ at $20^\circ\text{C}$.
3. **Polyethylene Glycol 400 (PEG 400):**
   - Viscosity: $\approx 110\text{ mPa}\cdot\text{s}$ ($110\text{ cP}$) at $20^\circ\text{C}$; $\approx 90\text{ cP}$ at $25^\circ\text{C}$.
   - Non-volatile, non-hazardous, water-soluble. Excellent match for medium-viscosity resins!
4. **Propylene Glycol:**
   - Viscosity: $\approx 56\text{ mPa}\cdot\text{s}$ ($56\text{ cP}$) at $20^\circ\text{C}$; $\approx 42\text{ cP}$ at $25^\circ\text{C}$.
   - Safe, water-soluble, stable.

#### Temperature-Viscosity Reference Lookup Table:
| Liquid | $18^\circ\text{C}$ | $20^\circ\text{C}$ | $22^\circ\text{C}$ | $24^\circ\text{C}$ | $26^\circ\text{C}$ | Cleanability |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Water** | $1.05\text{ cP}$ | $1.00\text{ cP}$ | $0.95\text{ cP}$ | $0.91\text{ cP}$ | $0.87\text{ cP}$ | DI Water Wipe |
| **Ethanol (99.5%)** | $1.25\text{ cP}$ | $1.20\text{ cP}$ | $1.15\text{ cP}$ | $1.10\text{ cP}$ | $1.06\text{ cP}$ | Volatile / Evaporates |
| **Propylene Glycol** | $64.5\text{ cP}$ | $56.0\text{ cP}$ | $49.2\text{ cP}$ | $43.5\text{ cP}$ | $38.7\text{ cP}$ | Water / IPA wipe |
| **PEG 400** | $124.0\text{ cP}$ | $110.0\text{ cP}$ | $99.0\text{ cP}$ | $90.0\text{ cP}$ | $81.5\text{ cP}$ | Water wipe (Recommended) |
| **Glycerol (85% w/w)**| $126.0\text{ cP}$ | $109.0\text{ cP}$ | $94.5\text{ cP}$ | $82.5\text{ cP}$ | $72.5\text{ cP}$ | Water wipe (Recommended) |
| **Pure Glycerol** | $1650\text{ cP}$ | $1412\text{ cP}$ | $1180\text{ cP}$ | $1010\text{ cP}$ | $860\text{ cP}$ | Warm water wipe |

---

## 8. Summary of Physical Equations for Implementation

| Phenomenon | Governing Equation | Primary Use in Software |
| :--- | :--- | :--- |
| **Stefan Squeeze Force** | $F = \frac{3\pi D^4 \mu v}{32 h^3}$ | Direct Newtonian viscosity estimation |
| **Linearized Transformation** | $F^{-1/3} = \left(\frac{32}{3\pi D^4 \mu v}\right)^{1/3}(z - z_0)$ | Simultaneous $\mu$ and $z_0$ extraction |
| **Lumped EHL Compliance** | $z = z_0 + (C\mu v)^{1/3} F^{-1/3} - \frac{F}{k_{\text{eff}}}$ | Compliance-corrected 3-parameter fit |
| **Non-Newtonian Squeeze** | $F = \left(\frac{2n+1}{n}\right)^n \frac{2\pi K R^{n+3}}{(n+3) h^{2n+1}} v^n$ | Multi-speed shear-thinning solver |
| **Dry Membrane Touch** | $F = k_{\text{membrane}} (z_{dry\_0} - z)$ | Pre-fluid dry stiffness & contact baseline |
| **Relative Calibration** | $\mu_{resin} = \mu_{ref} \cdot \frac{F_{resin}(z) / v_{resin}}{F_{ref}(z) / v_{ref}}$ | Daily transfer function precalibration |
