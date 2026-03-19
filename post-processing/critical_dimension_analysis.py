"""
Critical Dimension Analysis for FEP Membrane
=============================================

Analyzes critical dimensions and forces for FEP membrane peeling based on
fracture mechanics principles.

The model uses the equation:
P_z = sqrt(6*pi*t^3 * G * E_FEP * R / ((1-v_FEP^2) * alpha^2 * w))

Where:
- P_z: Critical peeling force (N)
- t: Membrane thickness (m)
- G: Energy release rate (J/m^2)
- E_FEP: Young's modulus of FEP (Pa)
- R: Radius of peeled region (m)
- v_FEP: Poisson's ratio
- alpha: Geometric factor
- w: Characteristic dimension (width or length)

Author: Cheng Sun Lab
Date: December 11, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import pandas as pd


# Physical properties of FEP membrane
E_FEP = 0.5e9      # Young's modulus (Pa) - 0.5 GPa
v_FEP = 0.46       # Poisson's ratio
t = 100e-6         # Membrane thickness (m) - 150 micrometers
width = 30e-3      # Tank width (m) - 30 mm
length = 40e-3     # Tank length (m) - 40 mm
G = 10            # Energy release rate approximation (J/m^2)
alpha = 0.0775     # Geometric factor

# Stefan adhesion parameters
viscosity = 650e-3   # Resin viscosity (Pa·s) - 650 mPa·s
v = 200e-6           # Velocity of part (m/s) - 200 μm/s
gap = 50e-6          # Channel height for resin flow (m) - 50 μm

# Membrane deflection parameters
stiffness = 850      # Membrane stiffness (N/m)


def calculate_critical_force(R, t, G, E, v_poisson, alpha, width_membrane):
    """
    Calculate critical peeling force based on fracture mechanics.
    
    This is the force needed before the part peels off.
    P_z = sqrt(6*pi*t^3*G*E*R / ((1-v^2)*alpha^2*width))
    
    Parameters:
    -----------
    R : float or array
        Radius of peeled region (m)
    t : float
        Membrane thickness (m)
    G : float
        Energy release rate (J/m^2)
    E : float
        Young's modulus (Pa)
    v_poisson : float
        Poisson's ratio
    alpha : float
        Geometric factor
    width_membrane : float
        Width of the membrane (m)
    
    Returns:
    --------
    P_z : float or array
        Critical peeling force (N)
    """
    numerator = 6 * np.pi * t**3 * G * E * R
    denominator = (1 - v_poisson**2) * alpha**2 * width_membrane
    
    P_z = np.sqrt(numerator / denominator)
    
    return P_z


def calculate_stefan_adhesion(r, viscosity, velocity, gap):
    """
    Calculate Stefan adhesion force for viscous flow.
    
    F = 3*pi*viscosity*r^4*v / (2*gap^3)
    
    Parameters:
    -----------
    r : float or array
        Part radius (m)
    viscosity : float
        Resin viscosity (Pa·s)
    velocity : float
        Velocity of part separation (m/s)
    gap : float
        Channel height for resin flow (m)
    
    Returns:
    --------
    F : float or array
        Stefan adhesion force (N)
    """
    F = 3 * np.pi * viscosity * r**4 * velocity / (2 * gap**3)
    
    return F


def calculate_membrane_deflection_force(x, stiffness):
    """
    Calculate force required to deflect membrane by distance x.
    
    p_FEP = stiffness * x
    
    Parameters:
    -----------
    x : float or array
        Membrane displacement/deflection (m)
    stiffness : float
        Membrane stiffness (N/m)
    
    Returns:
    --------
    p_FEP : float or array
        Force required to deflect membrane (N)
    """
    p_FEP = stiffness * x
    
    return p_FEP


def calculate_critical_radius(x, stiffness, t, G, E, v_poisson, alpha, width_membrane):
    """
    Calculate critical radius as a function of deflection.
    
    Derived by setting P_z = p_FEP and solving for R:
    R = (stiffness * x)² * (1-v²) * α² * width / (6*π*t³*G*E)
    
    This gives the radius at which the membrane deflection force equals
    the critical peeling force.
    
    Parameters:
    -----------
    x : float or array
        Membrane displacement/deflection (m)
    stiffness : float
        Membrane stiffness (N/m)
    t : float
        Membrane thickness (m)
    G : float
        Energy release rate (J/m²)
    E : float
        Young's modulus (Pa)
    v_poisson : float
        Poisson's ratio
    alpha : float
        Geometric factor
    width_membrane : float
        Width of the membrane (m)
    
    Returns:
    --------
    R : float or array
        Critical radius (m)
    """
    numerator = (stiffness * x)**2 * (1 - v_poisson**2) * alpha**2 * width_membrane
    denominator = 6 * np.pi * t**3 * G * E
    
    R = numerator / denominator
    
    return R


def calculate_critical_radius_experimental(x, area_ref=10e-6, force_ref=0.5, distance_ref=0.8e-3, stiffness=850):
    """
    Calculate critical radius using experimental interpolation.
    
    Based on experimental observation that force scales with sqrt(radius).
    This is consistent with fracture mechanics: F ∝ √r
    
    Method:
    1. At deflection x, calculate the deflection force: F_deflect = stiffness * x
    2. Use sqrt scaling to find critical radius:
       F / F_ref = √(r / r_ref)
       r = r_ref × (F / F_ref)²
    
    Parameters:
    -----------
    x : float or array
        Membrane displacement/deflection (m)
    area_ref : float
        Reference cross-sectional area from experiment (m²), default 10 mm² = 10e-6 m²
    force_ref : float
        Peak force at reference area (N), default 0.5 N
    distance_ref : float
        Distance needed to reach peak force at reference (m), default 0.8 mm = 0.8e-3 m
        (Note: This parameter is kept for reference but not used as a constraint)
    stiffness : float
        Membrane stiffness (N/m), default 850 N/m
    
    Returns:
    --------
    R : float or array
        Critical radius (m)
    """
    # Calculate deflection force at distance x
    F_deflect = stiffness * x
    
    # Calculate reference radius from area
    r_ref = np.sqrt(area_ref / np.pi)
    
    # Scale radius based on force ratio (assuming F ∝ √r)
    # F / F_ref = √(r / r_ref)
    # Square both sides: (F / F_ref)² = r / r_ref
    # Solve for r: r = r_ref × (F / F_ref)²
    R = r_ref * (F_deflect / force_ref)**2
    
    return R


def plot_force_vs_radius(output_dir=None):
    """
    Plot critical force and Stefan adhesion as a function of radius.
    """
    # Generate radius values from 0.1 mm to 10 mm
    R_mm = np.linspace(0.1, 10, 100)
    R_m = R_mm * 1e-3  # Convert to meters
    
    # Calculate critical force (fracture mechanics)
    P_z = calculate_critical_force(R_m, t, G, E_FEP, v_FEP, alpha, width)
    
    # Calculate Stefan adhesion force
    F_stefan = calculate_stefan_adhesion(R_m, viscosity, v, gap)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 7))
    
    ax.plot(R_mm, P_z, 'b-', linewidth=2.5, label='Fracture Mechanics (Membrane)')
    ax.plot(R_mm, F_stefan, 'r-', linewidth=2.5, label='Stefan Adhesion (Viscous)')
    ax.plot(R_mm, P_z + F_stefan, 'g--', linewidth=2.5, label='Total Force')
    
    ax.set_xlabel('Radius (mm)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Force (N)', fontsize=13, fontweight='bold')
    ax.set_title('Adhesion Forces vs Radius', 
                 fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='best')
    
    # Add parameter text box
    param_text = f'Membrane Parameters:\n'
    param_text += f'E_FEP = {E_FEP/1e9:.1f} GPa\n'
    param_text += f'v_FEP = {v_FEP:.2f}\n'
    param_text += f't = {t*1e6:.1f} μm\n'
    param_text += f'G = {G} J/m²\n'
    param_text += f'α = {alpha:.4f}\n'
    param_text += f'w = {width*1e3:.1f} mm\n\n'
    param_text += f'Stefan Parameters:\n'
    param_text += f'η = {viscosity*1e3:.0f} mPa·s\n'
    param_text += f'v = {v*1e6:.0f} μm/s\n'
    param_text += f'gap = {gap*1e6:.0f} μm'
    
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, param_text, transform=ax.transAxes, fontsize=8,
            verticalalignment='top', bbox=props, family='monospace')
    
    plt.tight_layout()
    
    if output_dir:
        output_path = Path(output_dir) / 'adhesion_forces_vs_radius.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f'✓ Saved: {output_path}')
    else:
        plt.show()
    
    plt.close()
    
    return R_mm, P_z, F_stefan


def plot_force_vs_parameters(output_dir=None):
    """
    Plot critical force sensitivity to different parameters.
    Creates a multi-panel plot showing how force varies with:
    - Membrane thickness
    - Energy release rate
    - Young's modulus
    - Geometric factor alpha
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    fig.suptitle('Critical Force Sensitivity to Parameters', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Fix radius at 5mm for parameter sweep
    R_fixed = 5e-3  # 5 mm
    
    # Panel 1: Vary thickness
    ax = axes[0, 0]
    t_range = np.linspace(0.5e-6, 5e-6, 100)  # 0.5 to 5 micrometers
    P_z_t = calculate_critical_force(R_fixed, t_range, G, E_FEP, v_FEP, alpha, width)
    ax.plot(t_range * 1e6, P_z_t, 'r-', linewidth=2.5)
    ax.axvline(t * 1e6, color='k', linestyle='--', alpha=0.5, label=f'Current: {t*1e6:.1f} μm')
    ax.set_xlabel('Membrane Thickness (μm)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Critical Force (N)', fontsize=11, fontweight='bold')
    ax.set_title('Effect of Membrane Thickness', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Panel 2: Vary energy release rate
    ax = axes[0, 1]
    G_range = np.linspace(10, 500, 100)  # 10 to 500 J/m²
    P_z_G = calculate_critical_force(R_fixed, t, G_range, E_FEP, v_FEP, alpha, width)
    ax.plot(G_range, P_z_G, 'g-', linewidth=2.5)
    ax.axvline(G, color='k', linestyle='--', alpha=0.5, label=f'Current: {G} J/m²')
    ax.set_xlabel('Energy Release Rate, G (J/m²)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Critical Force (N)', fontsize=11, fontweight='bold')
    ax.set_title('Effect of Energy Release Rate', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Panel 3: Vary Young's modulus
    ax = axes[1, 0]
    E_range = np.linspace(0.1e9, 2e9, 100)  # 0.1 to 2 GPa
    P_z_E = calculate_critical_force(R_fixed, t, G, E_range, v_FEP, alpha, width)
    ax.plot(E_range / 1e9, P_z_E, 'b-', linewidth=2.5)
    ax.axvline(E_FEP / 1e9, color='k', linestyle='--', alpha=0.5, label=f'Current: {E_FEP/1e9:.1f} GPa')
    ax.set_xlabel('Young\'s Modulus, E (GPa)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Critical Force (N)', fontsize=11, fontweight='bold')
    ax.set_title('Effect of Young\'s Modulus', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Panel 4: Vary geometric factor alpha
    ax = axes[1, 1]
    alpha_range = np.linspace(0.5, 3.0, 100)
    P_z_alpha = calculate_critical_force(R_fixed, t, G, E_FEP, v_FEP, alpha_range, width)
    ax.plot(alpha_range, P_z_alpha, 'm-', linewidth=2.5)
    ax.axvline(alpha, color='k', linestyle='--', alpha=0.5, label=f'Current: {alpha:.1f}')
    ax.set_xlabel('Geometric Factor, α', fontsize=11, fontweight='bold')
    ax.set_ylabel('Critical Force (N)', fontsize=11, fontweight='bold')
    ax.set_title('Effect of Geometric Factor', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    if output_dir:
        output_path = Path(output_dir) / 'critical_force_parameter_sensitivity.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f'✓ Saved: {output_path}')
    else:
        plt.show()
    
    plt.close()


def generate_summary_table(output_dir=None):
    """
    Generate a summary table of forces for various radii.
    """
    # Radius values to evaluate
    radii_mm = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    radii_m = [r * 1e-3 for r in radii_mm]
    
    # Calculate forces
    fracture_forces = [calculate_critical_force(r, t, G, E_FEP, v_FEP, alpha, width) for r in radii_m]
    stefan_forces = [calculate_stefan_adhesion(r, viscosity, v, gap) for r in radii_m]
    total_forces = [f + s for f, s in zip(fracture_forces, stefan_forces)]
    
    # Create DataFrame
    df = pd.DataFrame({
        'Radius (mm)': radii_mm,
        'Fracture Force (N)': fracture_forces,
        'Stefan Force (N)': stefan_forces,
        'Total Force (N)': total_forces,
        'Stefan/Total (%)': [100 * s / t for s, t in zip(stefan_forces, total_forces)]
    })
    
    print("\n" + "="*80)
    print("ADHESION FORCES SUMMARY TABLE")
    print("="*80)
    print(df.to_string(index=False))
    print("="*80)
    
    if output_dir:
        output_path = Path(output_dir) / 'adhesion_forces_summary.csv'
        df.to_csv(output_path, index=False)
        print(f'\n✓ Saved: {output_path}')
    
    return df


def generate_critical_radius_table(output_dir=None):
    """
    Generate a summary table of critical radii for various deflections.
    Includes both theoretical (fracture mechanics) and experimental interpolation methods.
    """
    # Deflection values to evaluate (in micrometers) - up to 200 μm only
    deflections_um = [10, 25, 50, 100, 200]
    deflections_m = [d * 1e-6 for d in deflections_um]
    
    # Calculate critical radii using theoretical method (fracture mechanics)
    critical_radii_theoretical_m = [calculate_critical_radius(x, stiffness, t, G, E_FEP, v_FEP, alpha, width) 
                                    for x in deflections_m]
    critical_radii_theoretical_mm = [r * 1e3 for r in critical_radii_theoretical_m]
    
    # Calculate critical radii using experimental interpolation
    critical_radii_experimental_m = [calculate_critical_radius_experimental(x, stiffness=stiffness) 
                                     for x in deflections_m]
    critical_radii_experimental_mm = [r * 1e3 if not np.isnan(r) else np.nan 
                                      for r in critical_radii_experimental_m]
    
    # Calculate corresponding forces
    deflection_forces = [calculate_membrane_deflection_force(x, stiffness) for x in deflections_m]
    
    # Create DataFrame
    df = pd.DataFrame({
        'Deflection (μm)': deflections_um,
        'Deflection (m)': deflections_m,
        'R_theoretical (mm)': critical_radii_theoretical_mm,
        'R_experimental (mm)': critical_radii_experimental_mm,
        'Deflection Force (N)': deflection_forces
    })
    
    print("\n" + "="*80)
    print("CRITICAL RADIUS vs DEFLECTION TABLE")
    print("="*80)
    print(df.to_string(index=False))
    print("="*80)
    
    if output_dir:
        output_path = Path(output_dir) / 'critical_radius_summary.csv'
        df.to_csv(output_path, index=False)
        print(f'\n✓ Saved: {output_path}')
    
    return df


def plot_stiffness_vs_critical_radius(output_dir=None):
    """
    Plot membrane stiffness vs critical radius vs force as 3D surface.
    Uses experimental interpolation method only.
    Moderate extension to show crossover with Stefan adhesion.
    Creates interactive HTML plot for rotation.
    """
    # Extended range of stiffness values to evaluate (N/m)
    stiffness_range = np.linspace(100, 10000, 100)
    
    # Deflection values up to 200 μm only
    deflections_um = np.linspace(10, 200, 40)
    deflections_m = deflections_um * 1e-6
    
    # Create meshgrid for 3D surface
    K_mesh, X_mesh = np.meshgrid(stiffness_range, deflections_m)
    
    # Calculate critical radius and force for each point using experimental interpolation
    R_mesh = np.zeros_like(K_mesh)
    F_mesh = np.zeros_like(K_mesh)
    
    for i in range(K_mesh.shape[0]):
        for j in range(K_mesh.shape[1]):
            k = K_mesh[i, j]
            x = X_mesh[i, j]
            R_mesh[i, j] = calculate_critical_radius_experimental(x, stiffness=k) * 1e3  # mm
            F_mesh[i, j] = calculate_membrane_deflection_force(x, k)  # N
    
    # Calculate Stefan adhesion forces (independent of stiffness)
    # For each radius in R_mesh, calculate Stefan force
    F_stefan_mesh = np.zeros_like(R_mesh)
    for i in range(R_mesh.shape[0]):
        for j in range(R_mesh.shape[1]):
            r_m = R_mesh[i, j] * 1e-3  # Convert mm to m
            F_stefan_mesh[i, j] = calculate_stefan_adhesion(r_m, viscosity, v, gap)
    
    # Create 3D plot
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot membrane deflection force surface (solid)
    surf = ax.plot_surface(K_mesh, R_mesh, F_mesh, cmap='viridis', 
                          alpha=0.7, edgecolor='none', label='Membrane Deflection')
    
    # Plot Stefan adhesion force wireframe (independent of stiffness)
    wire = ax.plot_wireframe(K_mesh, R_mesh, F_stefan_mesh, color='red', 
                             linewidth=1.5, alpha=0.8, label='Stefan Adhesion')
    
    # Add colorbar for membrane force
    cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
    cbar.set_label('Membrane Force (N)', fontsize=12, fontweight='bold')
    
    # Add legend
    ax.plot([], [], color='red', linewidth=2, label='Stefan Adhesion (Wireframe)')
    ax.legend(loc='upper left', fontsize=10)
    
    ax.set_xlabel('Membrane Stiffness (N/m)', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('Critical Radius (mm)', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_zlabel('Force (N)', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_title('3D Surface: Membrane vs Stefan Adhesion Forces\n(Stiffness vs Critical Radius)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    if output_dir:
        output_path = Path(output_dir) / 'stiffness_vs_critical_radius.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f'✓ Saved: {output_path}')
    else:
        plt.show()
    
    plt.close()
    
    # Create interactive plotly version
    try:
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Add membrane deflection force surface
        fig.add_trace(go.Surface(
            x=K_mesh,
            y=R_mesh,
            z=F_mesh,
            colorscale='Viridis',
            name='Membrane Deflection',
            opacity=0.8,
            showscale=True,
            colorbar=dict(title='Membrane Force (N)')
        ))
        
        # Add Stefan adhesion wireframe
        fig.add_trace(go.Surface(
            x=K_mesh,
            y=R_mesh,
            z=F_stefan_mesh,
            colorscale=[[0, 'red'], [1, 'red']],
            name='Stefan Adhesion',
            opacity=0.6,
            showscale=False,
            contours=dict(
                x=dict(show=True, color='red', width=2),
                y=dict(show=True, color='red', width=2)
            )
        ))
        
        fig.update_layout(
            title='Interactive 3D: Membrane vs Stefan Adhesion Forces<br>(Rotate and zoom to inspect)',
            scene=dict(
                xaxis_title='Membrane Stiffness (N/m)',
                yaxis_title='Critical Radius (mm)',
                zaxis_title='Force (N)',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.3))
            ),
            width=1000,
            height=800
        )
        
        if output_dir:
            output_path_html = Path(output_dir) / 'stiffness_vs_critical_radius_interactive.html'
            fig.write_html(output_path_html)
            print(f'✓ Saved interactive plot: {output_path_html}')
    except ImportError:
        print('  (Plotly not available - skipping interactive plot)')
    
    return


if __name__ == "__main__":
    import sys
    
    # Use current directory if no argument provided
    output_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    output_dir = Path(output_dir)
    
    print("="*60)
    print("FEP MEMBRANE CRITICAL DIMENSION ANALYSIS")
    print("="*60)
    print(f"\nMembrane Parameters:")
    print(f"  E_FEP = {E_FEP/1e9:.2f} GPa")
    print(f"  v_FEP = {v_FEP:.2f}")
    print(f"  t = {t*1e6:.2f} μm")
    print(f"  width = {width*1e3:.1f} mm")
    print(f"  length = {length*1e3:.1f} mm")
    print(f"  G = {G} J/m²")
    print(f"  α = {alpha:.4f}")
    print(f"\nStefan Adhesion Parameters:")
    print(f"  viscosity = {viscosity*1e3:.0f} mPa·s")
    print(f"  velocity = {v*1e6:.0f} μm/s")
    print(f"  gap = {gap*1e6:.0f} μm")
    
    # Generate plots
    print(f"\n{'='*60}")
    print("GENERATING PLOTS")
    print("="*60)
    
    R_mm, P_z, F_stefan = plot_force_vs_radius(output_dir)
    plot_force_vs_parameters(output_dir)
    plot_stiffness_vs_critical_radius(output_dir)
    
    # Generate summary tables
    df_forces = generate_summary_table(output_dir)
    df_critical = generate_critical_radius_table(output_dir)
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
