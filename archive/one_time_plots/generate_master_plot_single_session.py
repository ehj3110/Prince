"""
Generate master overview plots for a single print session using work of adhesion data.
This creates summary plots showing trends across all layers in one session.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import argparse

def generate_master_plots(session_dir):
    """
    Generate master plots for a single session using work of adhesion data.
    
    Args:
        session_dir: Path to the print session directory containing automated_work_of_adhesion.csv
    """
    session_path = Path(session_dir)
    woa_file = session_path / "automated_work_of_adhesion.csv"
    
    if not woa_file.exists():
        print(f"❌ ERROR: Work of adhesion file not found at: {woa_file}")
        return False
    
    print(f"Loading work of adhesion data from: {woa_file}")
    df = pd.read_csv(woa_file)
    
    print(f"Columns available: {df.columns.tolist()}")
    print(f"Total layers: {len(df)}")
    
    # Extract data
    layers = df['Layer_Number'].values
    peak_force = df['Peak_Force_N'].values
    work_of_adhesion = df['Work_of_Adhesion_mJ'].values
    peak_retraction = df['Peak_Retraction_Force_N'].values
    cross_section = df['Cross_Sectional_Area_mm2'].values
    
    # Calculate normalized metrics
    peak_force_normalized = peak_force / cross_section * 100  # N per cm²
    woa_normalized = work_of_adhesion / cross_section * 100   # mJ per cm²
    
    # Create figure with 2x2 subplots
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # === Plot 1: Peak Adhesion Force ===
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(layers, peak_force, 'o-', color='tab:blue', linewidth=2, markersize=4, label='Peak Force')
    ax1.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Peak Adhesion Force (N)', fontsize=12, fontweight='bold')
    ax1.set_title('Peak Adhesion Force vs Layer', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    
    # Add trend line
    z = np.polyfit(layers, peak_force, 1)
    p = np.poly1d(z)
    ax1.plot(layers, p(layers), "--", color='red', alpha=0.5, linewidth=2, label=f'Trend: {z[0]:.4f}x + {z[1]:.4f}')
    ax1.legend(fontsize=10)
    
    # === Plot 2: Work of Adhesion ===
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(layers, work_of_adhesion, 'o-', color='tab:green', linewidth=2, markersize=4, label='Work of Adhesion')
    ax2.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Work of Adhesion (mJ)', fontsize=12, fontweight='bold')
    ax2.set_title('Work of Adhesion vs Layer', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)
    
    # Add trend line
    z = np.polyfit(layers, work_of_adhesion, 1)
    p = np.poly1d(z)
    ax2.plot(layers, p(layers), "--", color='red', alpha=0.5, linewidth=2, label=f'Trend: {z[0]:.4f}x + {z[1]:.4f}')
    ax2.legend(fontsize=10)
    
    # === Plot 3: Normalized Peak Force (per unit area) ===
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(layers, peak_force_normalized, 'o-', color='tab:purple', linewidth=2, markersize=4, label='Peak Force / Area')
    ax3.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Peak Force per Area (N/cm²)', fontsize=12, fontweight='bold')
    ax3.set_title('Normalized Peak Adhesion Force vs Layer', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=10)
    
    # Add trend line
    z = np.polyfit(layers, peak_force_normalized, 1)
    p = np.poly1d(z)
    ax3.plot(layers, p(layers), "--", color='red', alpha=0.5, linewidth=2, label=f'Trend: {z[0]:.4f}x + {z[1]:.4f}')
    ax3.legend(fontsize=10)
    
    # === Plot 4: Peak Retraction Force ===
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(layers, peak_retraction, 'o-', color='tab:orange', linewidth=2, markersize=4, label='Peak Retraction Force')
    ax4.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Peak Retraction Force (N)', fontsize=12, fontweight='bold')
    ax4.set_title('Peak Retraction Force vs Layer', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=10)
    
    # Add trend line
    z = np.polyfit(layers, peak_retraction, 1)
    p = np.poly1d(z)
    ax4.plot(layers, p(layers), "--", color='red', alpha=0.5, linewidth=2, label=f'Trend: {z[0]:.4f}x + {z[1]:.4f}')
    ax4.legend(fontsize=10)
    
    # Add overall title
    session_name = session_path.name
    fig.suptitle(f'Master Overview Plot: {session_name}\n{len(df)} Layers Analyzed', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Save plot
    output_path = session_path / "MASTER_PLOT_overview.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Master plot saved to: {output_path}")
    
    # Print statistics
    print("\n" + "="*70)
    print("SESSION STATISTICS")
    print("="*70)
    print(f"Session: {session_name}")
    print(f"Total layers analyzed: {len(df)}")
    print(f"Layer range: {layers[0]} to {layers[-1]}")
    print()
    print("Peak Adhesion Force:")
    print(f"  Mean: {np.mean(peak_force):.4f} N")
    print(f"  Min:  {np.min(peak_force):.4f} N (Layer {layers[np.argmin(peak_force)]})")
    print(f"  Max:  {np.max(peak_force):.4f} N (Layer {layers[np.argmax(peak_force)]})")
    print(f"  Std:  {np.std(peak_force):.4f} N")
    print()
    print("Work of Adhesion:")
    print(f"  Mean: {np.mean(work_of_adhesion):.4f} mJ")
    print(f"  Min:  {np.min(work_of_adhesion):.4f} mJ (Layer {layers[np.argmin(work_of_adhesion)]})")
    print(f"  Max:  {np.max(work_of_adhesion):.4f} mJ (Layer {layers[np.argmax(work_of_adhesion)]})")
    print(f"  Std:  {np.std(work_of_adhesion):.4f} mJ")
    print()
    print("Normalized Peak Force (N/cm²):")
    print(f"  Mean: {np.mean(peak_force_normalized):.4f} N/cm²")
    print(f"  Min:  {np.min(peak_force_normalized):.4f} N/cm²")
    print(f"  Max:  {np.max(peak_force_normalized):.4f} N/cm²")
    print()
    print("Peak Retraction Force:")
    print(f"  Mean: {np.mean(peak_retraction):.4f} N")
    print(f"  Min:  {np.min(peak_retraction):.4f} N (Layer {layers[np.argmin(peak_retraction)]})")
    print(f"  Max:  {np.max(peak_retraction):.4f} N (Layer {layers[np.argmax(peak_retraction)]})")
    print(f"  Std:  {np.std(peak_retraction):.4f} N")
    print("="*70)
    
    # Create a second figure with additional plots
    fig2 = plt.figure(figsize=(20, 12))
    gs2 = fig2.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # === Additional Plot 1: Cross-Sectional Area ===
    ax5 = fig2.add_subplot(gs2[0, 0])
    ax5.plot(layers, cross_section, 'o-', color='tab:cyan', linewidth=2, markersize=4, label='Cross-Section')
    ax5.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Cross-Sectional Area (mm²)', fontsize=12, fontweight='bold')
    ax5.set_title('Cross-Sectional Area vs Layer', fontsize=14, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    ax5.legend(fontsize=10)
    
    # === Additional Plot 2: Normalized Work of Adhesion ===
    ax6 = fig2.add_subplot(gs2[0, 1])
    ax6.plot(layers, woa_normalized, 'o-', color='tab:brown', linewidth=2, markersize=4, label='WoA / Area')
    ax6.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
    ax6.set_ylabel('Work of Adhesion per Area (mJ/cm²)', fontsize=12, fontweight='bold')
    ax6.set_title('Normalized Work of Adhesion vs Layer', fontsize=14, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    ax6.legend(fontsize=10)
    
    # Add trend line
    z = np.polyfit(layers, woa_normalized, 1)
    p = np.poly1d(z)
    ax6.plot(layers, p(layers), "--", color='red', alpha=0.5, linewidth=2, label=f'Trend: {z[0]:.4f}x + {z[1]:.4f}')
    ax6.legend(fontsize=10)
    
    # === Additional Plot 3: Peak Force vs Work of Adhesion (Correlation) ===
    ax7 = fig2.add_subplot(gs2[1, 0])
    scatter = ax7.scatter(peak_force, work_of_adhesion, c=layers, cmap='viridis', s=50, alpha=0.6)
    ax7.set_xlabel('Peak Adhesion Force (N)', fontsize=12, fontweight='bold')
    ax7.set_ylabel('Work of Adhesion (mJ)', fontsize=12, fontweight='bold')
    ax7.set_title('Peak Force vs Work of Adhesion', fontsize=14, fontweight='bold')
    ax7.grid(True, alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax7)
    cbar.set_label('Layer Number', fontsize=10)
    
    # Add trend line
    z = np.polyfit(peak_force, work_of_adhesion, 1)
    p = np.poly1d(z)
    ax7.plot(peak_force, p(peak_force), "--", color='red', alpha=0.7, linewidth=2)
    correlation = np.corrcoef(peak_force, work_of_adhesion)[0, 1]
    ax7.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
             transform=ax7.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # === Additional Plot 4: Force Ratio (Peak/Retraction) ===
    ax8 = fig2.add_subplot(gs2[1, 1])
    force_ratio = peak_force / peak_retraction
    ax8.plot(layers, force_ratio, 'o-', color='tab:pink', linewidth=2, markersize=4, label='Peak/Retraction Ratio')
    ax8.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
    ax8.set_ylabel('Force Ratio (Peak/Retraction)', fontsize=12, fontweight='bold')
    ax8.set_title('Adhesion to Retraction Force Ratio vs Layer', fontsize=14, fontweight='bold')
    ax8.grid(True, alpha=0.3)
    ax8.legend(fontsize=10)
    
    # Add trend line
    z = np.polyfit(layers, force_ratio, 1)
    p = np.poly1d(z)
    ax8.plot(layers, p(layers), "--", color='red', alpha=0.5, linewidth=2, label=f'Trend: {z[0]:.4f}x + {z[1]:.4f}')
    ax8.legend(fontsize=10)
    
    # Add overall title
    fig2.suptitle(f'Master Overview Plot (Extended): {session_name}\n{len(df)} Layers Analyzed', 
                  fontsize=16, fontweight='bold', y=0.98)
    
    # Save second plot
    output_path2 = session_path / "MASTER_PLOT_extended.png"
    plt.savefig(output_path2, dpi=150, bbox_inches='tight')
    print(f"✅ Extended master plot saved to: {output_path2}")
    
    plt.show()
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate master overview plots for a single print session')
    parser.add_argument('session_dir', nargs='?', 
                       default=r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\SteppedCone_V1_10mm2to100mm2_50umLayers_V2\Printing_Logs\2025-11-29\Print 2 - Complete",
                       help='Path to the print session directory')
    
    args = parser.parse_args()
    
    print("="*70)
    print("MASTER PLOT GENERATOR - Single Session")
    print("="*70)
    print(f"Session: {args.session_dir}")
    print()
    
    success = generate_master_plots(args.session_dir)
    
    if success:
        print("\n" + "="*70)
        print("✅ COMPLETE - Master plots generated successfully!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ FAILED - Could not generate master plots")
        print("="*70)
