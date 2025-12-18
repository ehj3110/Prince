"""
Stiffness Scaling Analysis
===========================

Analyzes how membrane material stiffness scales with contact area and radius.

Key Questions:
1. Does stiffness depend on contact area? (Geometric confinement effects)
2. How does stiffness scale with radius? (Edge effects)
3. Are there differences between membrane types?

Expected Behaviors:
- Intrinsic material property: Stiffness should be independent of size
- Geometric effects: Stiffness could scale with perimeter (radius) or area
- Composite behavior: Water-filled membrane may show size-dependent stiffness

Author: Cheng Sun Lab Team
Date: December 3, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats, optimize
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class StiffnessScalingAnalyzer:
    """
    Analyze scaling relationships between stiffness and geometry.
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize analyzer.
        
        Args:
            output_dir: Directory for saving plots (if None, uses current directory)
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def analyze_stiffness_scaling(self,
                                  df: pd.DataFrame,
                                  stiffness_col: str = 'material_stiffness_N_per_mm',
                                  area_col: str = 'area_mm2',
                                  condition_col: str = 'detailed_condition',
                                  min_r_squared: float = 0.5) -> Dict:
        """
        Complete stiffness scaling analysis.
        
        Args:
            df: DataFrame with stiffness and geometry data
            stiffness_col: Column name for stiffness values
            area_col: Column name for contact area
            condition_col: Column name for grouping conditions
            min_r_squared: Minimum R² to include data point
            
        Returns:
            Dictionary with scaling results for each condition
        """
        # Filter for valid data
        df_valid = df.copy()
        
        # Filter by R² if available
        if f'{stiffness_col.replace("_N_per_mm", "")}_r_squared' in df_valid.columns:
            r_sq_col = f'{stiffness_col.replace("_N_per_mm", "")}_r_squared'
            initial_count = len(df_valid)
            df_valid = df_valid[df_valid[r_sq_col] >= min_r_squared]
            filtered_count = initial_count - len(df_valid)
            if filtered_count > 0:
                print(f"Filtered out {filtered_count} measurements with R² < {min_r_squared}")
        
        # Remove zero/NaN stiffness values
        df_valid = df_valid[(df_valid[stiffness_col] > 0) & (df_valid[stiffness_col].notna())]
        df_valid = df_valid[(df_valid[area_col] > 0) & (df_valid[area_col].notna())]
        
        if len(df_valid) == 0:
            print("ERROR: No valid data after filtering")
            return {}
        
        # Calculate radius
        df_valid['radius_mm'] = np.sqrt(df_valid[area_col] / np.pi)
        
        # Analyze by condition
        results = {}
        conditions = df_valid[condition_col].unique()
        
        print(f"\n{'='*70}")
        print(f"STIFFNESS SCALING ANALYSIS")
        print(f"{'='*70}")
        print(f"Total measurements: {len(df_valid)}")
        print(f"Conditions: {len(conditions)}")
        
        for condition in conditions:
            df_cond = df_valid[df_valid[condition_col] == condition]
            
            if len(df_cond) < 5:
                print(f"\n{condition}: Insufficient data (n={len(df_cond)})")
                continue
            
            print(f"\n{condition}:")
            print(f"  n = {len(df_cond)} measurements")
            
            # Extract data
            areas = df_cond[area_col].values
            radii = df_cond['radius_mm'].values
            stiffness = df_cond[stiffness_col].values
            
            # Power law fits: k = a * x^n
            
            # 1. Stiffness vs Area
            area_fit = self._fit_power_law(areas, stiffness, "Area (mm²)")
            print(f"  Area scaling: k = {area_fit['a']:.4f} × A^{area_fit['n']:.3f} (R² = {area_fit['r_squared']:.3f})")
            
            # 2. Stiffness vs Radius
            radius_fit = self._fit_power_law(radii, stiffness, "Radius (mm)")
            print(f"  Radius scaling: k = {radius_fit['a']:.4f} × r^{radius_fit['n']:.3f} (R² = {radius_fit['r_squared']:.3f})")
            
            # Interpretation
            if abs(area_fit['n']) < 0.15:
                area_interp = "independent of area (intrinsic material property)"
            elif area_fit['n'] > 0.15:
                area_interp = "increases with area (composite/geometric effect)"
            else:
                area_interp = "decreases with area (edge/confinement effect)"
            
            if abs(radius_fit['n']) < 0.15:
                radius_interp = "independent of radius"
            elif radius_fit['n'] > 0.15:
                radius_interp = "increases with radius"
            else:
                radius_interp = "decreases with radius"
            
            print(f"  Interpretation: Stiffness {area_interp}")
            print(f"                  Stiffness {radius_interp}")
            
            # Store results
            results[condition] = {
                'n_measurements': len(df_cond),
                'area_range_mm2': (areas.min(), areas.max()),
                'radius_range_mm': (radii.min(), radii.max()),
                'stiffness_range_N_per_mm': (stiffness.min(), stiffness.max()),
                'stiffness_mean_N_per_mm': stiffness.mean(),
                'stiffness_std_N_per_mm': stiffness.std(),
                'area_scaling': area_fit,
                'radius_scaling': radius_fit,
                'data': df_cond
            }
        
        return results
    
    def _fit_power_law(self, x: np.ndarray, y: np.ndarray, x_label: str) -> Dict:
        """
        Fit power law: y = a * x^n
        
        Uses log-log linear regression for initial fit, then refines with nonlinear optimization.
        """
        try:
            # Remove any zeros for log transform
            valid_idx = (x > 0) & (y > 0)
            x_valid = x[valid_idx]
            y_valid = y[valid_idx]
            
            if len(x_valid) < 3:
                return {'success': False, 'error': 'Insufficient valid data'}
            
            # Log-log linear regression
            log_x = np.log(x_valid)
            log_y = np.log(y_valid)
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
            
            n = slope
            a = np.exp(intercept)
            r_squared = r_value ** 2
            
            # Calculate confidence intervals using bootstrap
            n_bootstrap = 1000
            n_samples = len(x_valid)
            n_values = []
            
            for _ in range(n_bootstrap):
                # Resample with replacement
                indices = np.random.choice(n_samples, n_samples, replace=True)
                x_boot = x_valid[indices]
                y_boot = y_valid[indices]
                
                # Fit
                try:
                    log_x_boot = np.log(x_boot)
                    log_y_boot = np.log(y_boot)
                    slope_boot, _, _, _, _ = stats.linregress(log_x_boot, log_y_boot)
                    n_values.append(slope_boot)
                except:
                    continue
            
            if len(n_values) > 0:
                n_ci_low, n_ci_high = np.percentile(n_values, [2.5, 97.5])
            else:
                n_ci_low, n_ci_high = n, n
            
            return {
                'success': True,
                'model': f'k = a × {x_label}^n',
                'a': a,
                'n': n,
                'n_ci_95': (n_ci_low, n_ci_high),
                'r_squared': r_squared,
                'p_value': p_value,
                'std_err': std_err
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def plot_stiffness_vs_area(self,
                               results: Dict,
                               stiffness_col: str = 'material_stiffness_N_per_mm',
                               filename: str = 'stiffness_vs_area_scaling.png'):
        """
        Generate stiffness vs area scaling plot with power law fits.
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Define colors for each condition
        colors = plt.cm.Set2(np.linspace(0, 1, len(results)))
        
        for idx, (condition, data) in enumerate(results.items()):
            if not data['area_scaling']['success']:
                continue
            
            df_cond = data['data']
            areas = df_cond['area_mm2'].values
            stiffness = df_cond[stiffness_col].values
            
            color = colors[idx]
            
            # Left plot: Linear scale
            axes[0].scatter(areas, stiffness, alpha=0.6, s=50, color=color, label=condition)
            
            # Plot fit line
            x_fit = np.linspace(areas.min(), areas.max(), 100)
            y_fit = data['area_scaling']['a'] * x_fit ** data['area_scaling']['n']
            axes[0].plot(x_fit, y_fit, '--', color=color, linewidth=2)
            
            # Right plot: Log-log scale
            axes[1].scatter(areas, stiffness, alpha=0.6, s=50, color=color, label=condition)
            axes[1].plot(x_fit, y_fit, '--', color=color, linewidth=2)
        
        # Left plot formatting
        axes[0].set_xlabel('Contact Area (mm²)', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Material Stiffness (N/mm)', fontsize=12, fontweight='bold')
        axes[0].set_title('Stiffness vs Area Scaling\n(Linear Scale)', fontsize=13, fontweight='bold')
        axes[0].legend(fontsize=9)
        axes[0].grid(True, alpha=0.3)
        
        # Right plot formatting
        axes[1].set_xlabel('Contact Area (mm²)', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Material Stiffness (N/mm)', fontsize=12, fontweight='bold')
        axes[1].set_title('Stiffness vs Area Scaling\n(Log-Log Scale)', fontsize=13, fontweight='bold')
        axes[1].set_xscale('log')
        axes[1].set_yscale('log')
        axes[1].legend(fontsize=9)
        axes[1].grid(True, alpha=0.3, which='both')
        
        plt.tight_layout()
        
        # Save
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"\nSaved: {output_path}")
        return output_path
    
    def plot_stiffness_vs_radius(self,
                                 results: Dict,
                                 stiffness_col: str = 'material_stiffness_N_per_mm',
                                 filename: str = 'stiffness_vs_radius_scaling.png'):
        """
        Generate stiffness vs radius scaling plot with power law fits.
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Define colors for each condition
        colors = plt.cm.Set2(np.linspace(0, 1, len(results)))
        
        for idx, (condition, data) in enumerate(results.items()):
            if not data['radius_scaling']['success']:
                continue
            
            df_cond = data['data']
            radii = df_cond['radius_mm'].values
            stiffness = df_cond[stiffness_col].values
            
            color = colors[idx]
            
            # Left plot: Linear scale
            axes[0].scatter(radii, stiffness, alpha=0.6, s=50, color=color, label=condition)
            
            # Plot fit line
            x_fit = np.linspace(radii.min(), radii.max(), 100)
            y_fit = data['radius_scaling']['a'] * x_fit ** data['radius_scaling']['n']
            axes[0].plot(x_fit, y_fit, '--', color=color, linewidth=2)
            
            # Right plot: Log-log scale
            axes[1].scatter(radii, stiffness, alpha=0.6, s=50, color=color, label=condition)
            axes[1].plot(x_fit, y_fit, '--', color=color, linewidth=2)
        
        # Left plot formatting
        axes[0].set_xlabel('Contact Radius (mm)', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Material Stiffness (N/mm)', fontsize=12, fontweight='bold')
        axes[0].set_title('Stiffness vs Radius Scaling\n(Linear Scale)', fontsize=13, fontweight='bold')
        axes[0].legend(fontsize=9)
        axes[0].grid(True, alpha=0.3)
        
        # Right plot formatting
        axes[1].set_xlabel('Contact Radius (mm)', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Material Stiffness (N/mm)', fontsize=12, fontweight='bold')
        axes[1].set_title('Stiffness vs Radius Scaling\n(Log-Log Scale)', fontsize=13, fontweight='bold')
        axes[1].set_xscale('log')
        axes[1].set_yscale('log')
        axes[1].legend(fontsize=9)
        axes[1].grid(True, alpha=0.3, which='both')
        
        plt.tight_layout()
        
        # Save
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved: {output_path}")
        return output_path
    
    def plot_stiffness_vs_radius_with_r2_bands(self,
                                                results: Dict,
                                                stiffness_col: str = 'material_stiffness_N_per_mm',
                                                r_squared_col: str = 'material_stiffness_r_squared',
                                                filename: str = 'stiffness_vs_radius_r2_bands.png'):
        """
        Generate stiffness vs radius plot with shaded error bands based on R² values.
        
        Higher R² values get narrower bands, lower R² values get wider bands.
        This shows both the trend and the reliability of the stiffness measurements.
        
        Args:
            results: Results dictionary from analyze_stiffness_scaling
            stiffness_col: Column name for stiffness values
            r_squared_col: Column name for R² values
            filename: Output filename
            
        Returns:
            Path to saved plot
        """
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Define colors for each condition
        colors = plt.cm.Set2(np.linspace(0, 1, len(results)))
        
        for idx, (condition, data) in enumerate(results.items()):
            df_cond = data['data']
            
            # Get radius, stiffness, and R² values
            radii = df_cond['radius_mm'].values
            stiffness = df_cond[stiffness_col].values
            r_squared = df_cond[r_squared_col].values
            
            color = colors[idx]
            
            # Sort by radius for proper shading
            sort_idx = np.argsort(radii)
            radii_sorted = radii[sort_idx]
            stiffness_sorted = stiffness[sort_idx]
            r_squared_sorted = r_squared[sort_idx]
            
            # Group by radius and calculate statistics
            unique_radii = np.unique(radii_sorted)
            means = []
            mean_r2 = []
            lower_bounds = []
            upper_bounds = []
            
            for r in unique_radii:
                mask = radii_sorted == r
                stiff_vals = stiffness_sorted[mask]
                r2_vals = r_squared_sorted[mask]
                
                mean_stiff = np.mean(stiff_vals)
                mean_r2_val = np.mean(r2_vals)
                
                # Error band width inversely proportional to R²
                # High R² (e.g., 0.95) → small band
                # Low R² (e.g., 0.50) → large band
                # Use (1 - R²) as the uncertainty factor
                uncertainty_factor = (1 - mean_r2_val) if mean_r2_val > 0 else 1.0
                
                # Scale the uncertainty by the standard deviation
                std_stiff = np.std(stiff_vals) if len(stiff_vals) > 1 else 0
                
                # Band width: base uncertainty scaled by (1 - R²)
                # If R² = 1.0, band_width = 0
                # If R² = 0.5, band_width = 0.5 * std
                # If R² = 0.0, band_width = 1.0 * std
                band_width = uncertainty_factor * max(std_stiff, mean_stiff * 0.1)  # At least 10% of mean
                
                means.append(mean_stiff)
                mean_r2.append(mean_r2_val)
                lower_bounds.append(mean_stiff - band_width)
                upper_bounds.append(mean_stiff + band_width)
            
            unique_radii = np.array(unique_radii)
            means = np.array(means)
            mean_r2 = np.array(mean_r2)
            lower_bounds = np.array(lower_bounds)
            upper_bounds = np.array(upper_bounds)
            
            # Plot shaded error band
            ax.fill_between(unique_radii, lower_bounds, upper_bounds, 
                           color=color, alpha=0.2, label=f'{condition} (uncertainty band)')
            
            # Plot mean line
            ax.plot(unique_radii, means, '-', color=color, linewidth=2.5, 
                   label=f'{condition} (mean)', zorder=10)
            
            # Plot individual data points with transparency based on R²
            # High R² → more opaque, low R² → more transparent
            alphas = r_squared_sorted * 0.8 + 0.2  # Range from 0.2 to 1.0
            for i in range(len(radii_sorted)):
                ax.scatter(radii_sorted[i], stiffness_sorted[i], 
                          color=color, s=30, alpha=alphas[i], zorder=5)
        
        # Formatting
        ax.set_xlabel('Contact Radius (mm)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Material Stiffness (N/mm)', fontsize=14, fontweight='bold')
        ax.set_title('Material Stiffness vs Contact Radius\n(Uncertainty Bands from R² Values)', 
                    fontsize=15, fontweight='bold', pad=20)
        ax.legend(fontsize=10, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        # Add explanation text
        textstr = ('Shaded bands show measurement uncertainty:\n'
                  '• Narrow bands = High R² (reliable fits)\n'
                  '• Wide bands = Low R² (uncertain fits)\n'
                  '• Point opacity also reflects R² (darker = better fit)')
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', bbox=dict(boxstyle='round', 
               facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Save
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"\nSaved: {output_path}")
        return output_path
    
    def generate_summary_report(self, 
                               results: Dict,
                               filename: str = 'stiffness_scaling_report.txt') -> Path:
        """
        Generate text summary of scaling analysis.
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("MATERIAL STIFFNESS SCALING ANALYSIS REPORT\n")
            f.write("="*70 + "\n\n")
            
            for condition, data in results.items():
                f.write(f"\n{condition}\n")
                f.write("-" * len(condition) + "\n\n")
                
                f.write(f"Sample Size: {data['n_measurements']} measurements\n")
                f.write(f"Area Range: {data['area_range_mm2'][0]:.2f} - {data['area_range_mm2'][1]:.2f} mm²\n")
                f.write(f"Radius Range: {data['radius_range_mm'][0]:.2f} - {data['radius_range_mm'][1]:.2f} mm\n")
                f.write(f"Stiffness: {data['stiffness_mean_N_per_mm']:.4f} ± {data['stiffness_std_N_per_mm']:.4f} N/mm\n\n")
                
                # Area scaling
                area_fit = data['area_scaling']
                if area_fit['success']:
                    f.write(f"Area Scaling:\n")
                    f.write(f"  k = {area_fit['a']:.4f} × Area^{area_fit['n']:.3f}\n")
                    f.write(f"  Exponent 95% CI: [{area_fit['n_ci_95'][0]:.3f}, {area_fit['n_ci_95'][1]:.3f}]\n")
                    f.write(f"  R² = {area_fit['r_squared']:.3f}\n")
                    f.write(f"  p-value = {area_fit['p_value']:.4e}\n\n")
                
                # Radius scaling
                radius_fit = data['radius_scaling']
                if radius_fit['success']:
                    f.write(f"Radius Scaling:\n")
                    f.write(f"  k = {radius_fit['a']:.4f} × Radius^{radius_fit['n']:.3f}\n")
                    f.write(f"  Exponent 95% CI: [{radius_fit['n_ci_95'][0]:.3f}, {radius_fit['n_ci_95'][1]:.3f}]\n")
                    f.write(f"  R² = {radius_fit['r_squared']:.3f}\n")
                    f.write(f"  p-value = {radius_fit['p_value']:.4e}\n\n")
                
                # Interpretation
                f.write("Interpretation:\n")
                if abs(area_fit['n']) < 0.15:
                    f.write("  • Stiffness is independent of contact area (intrinsic material property)\n")
                elif area_fit['n'] > 0.15:
                    f.write("  • Stiffness increases with area (composite/geometric stiffening)\n")
                else:
                    f.write("  • Stiffness decreases with area (edge/confinement effects)\n")
                
                f.write("\n")
        
        print(f"\nSaved report: {output_path}")
        return output_path


# Example usage
if __name__ == "__main__":
    print("Stiffness Scaling Analyzer - Test Mode")
    print("="*60)
    print("\nThis module requires actual data from batch processing.")
    print("Run batch_process_universal.py first to generate MASTER_all_metrics.csv")
    print("\nExample usage:")
    print("""
    import pandas as pd
    from stiffness_scaling_analyzer import StiffnessScalingAnalyzer
    
    # Load data
    df = pd.read_csv('V6/MASTER_all_metrics.csv')
    
    # Analyze
    analyzer = StiffnessScalingAnalyzer(output_dir='V6')
    results = analyzer.analyze_stiffness_scaling(df)
    
    # Generate plots
    analyzer.plot_stiffness_vs_area(results)
    analyzer.plot_stiffness_vs_radius(results)
    analyzer.generate_summary_report(results)
    """)
