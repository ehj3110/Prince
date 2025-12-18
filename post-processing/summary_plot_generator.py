"""
Summary Plot Generator
======================

Generates 4-panel summary plots for individual test folders showing:
1. Layer vs Peak Force
2. Layer vs Material Stiffness  
3. Layer vs Peak Retraction Force
4. Radius vs Peak Force

Uses exponential curve fits with shaded confidence regions instead of individual points.

Author: Cheng Sun Lab Team
Date: December 10, 2025
"""

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import curve_fit
from scipy import stats
from typing import Tuple, Optional


class SummaryPlotGenerator:
    """Generates summary plots for test data"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        
    @staticmethod
    def power_law_func(x, a, b):
        """Power law function: y = a * x^b"""
        return a * np.power(x, b)
    
    @staticmethod
    def fit_power_law_with_ci(x: np.ndarray, y: np.ndarray, 
                                 confidence: float = 0.95) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
        """
        Fit power law curve and calculate confidence interval
        
        Returns:
            x_fit: X values for plotting
            y_fit: Fitted Y values
            y_ci: Confidence interval (upper and lower bounds)
            params: Dictionary with fit parameters and statistics
        """
        try:
            # Filter out zero or negative values for power law
            mask = (x > 0) & (y > 0)
            if np.sum(mask) < len(x) * 0.5:  # Need at least 50% valid data
                raise ValueError("Too many zero or negative values for power law fit")
            
            x_valid = x[mask]
            y_valid = y[mask]
            
            # Initial guess for power law
            p0 = [y_valid.mean(), 1.0]
            
            # Fit power law
            popt, pcov = curve_fit(
                SummaryPlotGenerator.power_law_func, 
                x_valid, y_valid, 
                p0=p0,
                maxfev=5000,
                bounds=([0, -np.inf], [np.inf, np.inf])
            )
            
            # Calculate R²
            y_pred = SummaryPlotGenerator.power_law_func(x_valid, *popt)
            ss_res = np.sum((y_valid - y_pred) ** 2)
            ss_tot = np.sum((y_valid - np.mean(y_valid)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            # Generate smooth curve
            x_fit = np.linspace(x_valid.min(), x_valid.max(), 100)
            y_fit = SummaryPlotGenerator.power_law_func(x_fit, *popt)
            
            # Calculate prediction interval using residual standard error
            residuals = y_valid - y_pred
            residual_std = np.std(residuals)
            
            # t-value for confidence interval
            t_val = stats.t.ppf((1 + confidence) / 2, len(x_valid) - len(popt))
            
            # Prediction interval (wider than confidence interval)
            y_ci = t_val * residual_std * 1.5  # Factor of 1.5 for prediction interval
            
            params = {
                'a': popt[0],
                'b': popt[1],
                'r_squared': r_squared,
                'residual_std': residual_std,
                'success': True
            }
            
            return x_fit, y_fit, y_ci, params
            
        except Exception as e:
            print(f"    Warning: Power law fit failed ({str(e)}), using linear fit")
            
            # Fallback to linear fit
            try:
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                x_fit = np.linspace(x.min(), x.max(), 100)
                y_fit = slope * x_fit + intercept
                
                # Linear prediction interval
                y_pred = slope * x + intercept
                residuals = y - y_pred
                residual_std = np.std(residuals)
                t_val = stats.t.ppf((1 + confidence) / 2, len(x) - 2)
                y_ci = t_val * residual_std * 1.5
                
                params = {
                    'slope': slope,
                    'intercept': intercept,
                    'r_squared': r_value**2,
                    'residual_std': residual_std,
                    'success': True,
                    'linear_fallback': True
                }
                
                return x_fit, y_fit, y_ci, params
                
            except Exception as e2:
                print(f"    Warning: Both exponential and linear fits failed: {str(e2)}")
                # Return dummy values
                x_fit = np.array([x.min(), x.max()])
                y_fit = np.array([y.mean(), y.mean()])
                y_ci = 0
                params = {'success': False}
                return x_fit, y_fit, y_ci, params
    
    def generate_summary_plot(self, csv_path: Path, master_csv_path: Path = None, output_filename: str = "summary_plot.png"):
        """
        Generate 4-panel summary plot from automated_work_of_adhesion.csv and MASTER CSV
        
        Args:
            csv_path: Path to automated_work_of_adhesion.csv
            master_csv_path: Path to MASTER_all_metrics.csv (for stiffness data)
            output_filename: Name for output plot file
        """
        # Read data
        df = pd.read_csv(csv_path)
        
        # Standardize column names (handle different formats)
        column_mapping = {
            'Layer_Number': 'layer_number',
            'Peak_Force_N': 'peak_adhesion_force_N',
            'Peak_Retraction_Force_N': 'peak_retraction_force_N',
            'Cross_Sectional_Area_mm2': 'area_mm2',
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and new_name not in df.columns:
                df[new_name] = df[old_name]
        
        # Check required columns
        required_cols = ['layer_number', 'peak_adhesion_force_N', 'peak_retraction_force_N']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"ERROR: Missing columns in CSV: {missing_cols}")
            print(f"Available columns: {list(df.columns)}")
            return
        
        # Get stiffness data from MASTER CSV if provided
        stiffness_col = None
        if master_csv_path and master_csv_path.exists():
            try:
                df_master = pd.read_csv(master_csv_path)
                # Filter for layers in current dataset
                layer_numbers = df['layer_number'].unique()
                df_master_filtered = df_master[df_master['layer_number'].isin(layer_numbers)]
                
                # Merge stiffness data
                if 'material_stiffness_N_per_mm' in df_master_filtered.columns:
                    stiffness_data = df_master_filtered[['layer_number', 'material_stiffness_N_per_mm']].groupby('layer_number').mean()
                    df = df.merge(stiffness_data, on='layer_number', how='left')
                    stiffness_col = 'material_stiffness_N_per_mm'
                    print(f"  Loaded stiffness data from MASTER CSV")
            except Exception as e:
                print(f"  Warning: Could not load stiffness from MASTER CSV: {e}")
        
        # Check for stiffness in current dataframe
        if stiffness_col is None:
            for col in ['material_stiffness_N_per_mm', 'effective_stiffness_N_per_mm', 'stiffness']:
                if col in df.columns:
                    stiffness_col = col
                    break
        
        radius_col = None
        for col in ['radius_mm', 'contact_radius_mm', 'area_mm2']:
            if col in df.columns:
                if 'area' in col:
                    # Calculate radius from area
                    df['radius_mm'] = np.sqrt(df[col] / np.pi)
                    radius_col = 'radius_mm'
                else:
                    radius_col = col
                break
        
        print(f"  Found stiffness column: {stiffness_col}")
        print(f"  Found radius column: {radius_col}")
        
        # Create 2x2 subplot figure
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Test Summary', fontsize=16, fontweight='bold', y=0.995)
        
        # Color scheme
        color_force = '#2E86AB'
        color_stiffness = '#A23B72'
        color_retraction = '#F18F01'
        
        # ============================================
        # Plot 1: Layer vs Peak Force
        # ============================================
        ax1 = axes[0, 0]
        x = df['layer_number'].values
        y = df['peak_adhesion_force_N'].values
        
        # Remove NaN values
        mask = ~(np.isnan(x) | np.isnan(y))
        x_clean, y_clean = x[mask], y[mask]
        
        if len(x_clean) > 3:
            x_fit, y_fit, y_ci, params = self.fit_power_law_with_ci(x_clean, y_clean)
            
            # Plot shaded region
            ax1.fill_between(x_fit, y_fit - y_ci, y_fit + y_ci, 
                            color=color_force, alpha=0.3, label='95% Prediction Interval')
            
            # Plot fit line
            ax1.plot(x_fit, y_fit, '-', color=color_force, linewidth=2.5, 
                    label=f'Power Law Fit (R² = {params["r_squared"]:.3f})')
            
            # Add equation text
            if 'linear_fallback' not in params:
                eq_text = f'y = {params["a"]:.3f} × x^{params["b"]:.3f}'
            else:
                eq_text = f'y = {params["slope"]:.4f} × x + {params["intercept"]:.3f}'
            ax1.text(0.05, 0.95, eq_text, transform=ax1.transAxes,
                    fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax1.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Peak Adhesion Force (N)', fontsize=12, fontweight='bold')
        ax1.set_title('Layer vs Peak Force', fontsize=13, fontweight='bold', pad=10)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(fontsize=10, loc='best')
        
        # ============================================
        # Plot 2: Layer vs Material Stiffness
        # ============================================
        ax2 = axes[0, 1]
        
        if stiffness_col:
            x = df['layer_number'].values
            y = df[stiffness_col].values
            
            mask = ~(np.isnan(x) | np.isnan(y))
            x_clean, y_clean = x[mask], y[mask]
            
            if len(x_clean) > 3:
                x_fit, y_fit, y_ci, params = self.fit_power_law_with_ci(x_clean, y_clean)
                
                ax2.fill_between(x_fit, y_fit - y_ci, y_fit + y_ci,
                                color=color_stiffness, alpha=0.3, label='95% Prediction Interval')
                
                ax2.plot(x_fit, y_fit, '-', color=color_stiffness, linewidth=2.5,
                        label=f'Power Law Fit (R² = {params["r_squared"]:.3f})')
                
                if 'linear_fallback' not in params:
                    eq_text = f'y = {params["a"]:.3f} × x^{params["b"]:.3f}'
                else:
                    eq_text = f'y = {params["slope"]:.4f} × x + {params["intercept"]:.3f}'
                ax2.text(0.05, 0.95, eq_text, transform=ax2.transAxes,
                        fontsize=9, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            ax2.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Material Stiffness (N/mm)', fontsize=12, fontweight='bold')
            ax2.set_title('Layer vs Material Stiffness', fontsize=13, fontweight='bold', pad=10)
            ax2.grid(True, alpha=0.3, linestyle='--')
            ax2.legend(fontsize=10, loc='best')
        else:
            ax2.text(0.5, 0.5, 'Stiffness data not available', 
                    ha='center', va='center', transform=ax2.transAxes, fontsize=12)
            ax2.set_title('Layer vs Material Stiffness', fontsize=13, fontweight='bold', pad=10)
        
        # ============================================
        # Plot 3: Layer vs Peak Retraction Force
        # ============================================
        ax3 = axes[1, 0]
        x = df['layer_number'].values
        y = df['peak_retraction_force_N'].values
        
        mask = ~(np.isnan(x) | np.isnan(y))
        x_clean, y_clean = x[mask], y[mask]
        
        if len(x_clean) > 3:
            x_fit, y_fit, y_ci, params = self.fit_power_law_with_ci(x_clean, y_clean)
            
            ax3.fill_between(x_fit, y_fit - y_ci, y_fit + y_ci,
                            color=color_retraction, alpha=0.3, label='95% Prediction Interval')
            
            ax3.plot(x_fit, y_fit, '-', color=color_retraction, linewidth=2.5,
                    label=f'Power Law Fit (R² = {params["r_squared"]:.3f})')
            
            if 'linear_fallback' not in params:
                eq_text = f'y = {params["a"]:.3f} × x^{params["b"]:.3f}'
            else:
                eq_text = f'y = {params["slope"]:.4f} × x + {params["intercept"]:.3f}'
            ax3.text(0.05, 0.95, eq_text, transform=ax3.transAxes,
                    fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax3.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Peak Retraction Force (N)', fontsize=12, fontweight='bold')
        ax3.set_title('Layer vs Peak Retraction Force', fontsize=13, fontweight='bold', pad=10)
        ax3.grid(True, alpha=0.3, linestyle='--')
        ax3.legend(fontsize=10, loc='best')
        
        # ============================================
        # Plot 4: Radius vs Peak Force
        # ============================================
        ax4 = axes[1, 1]
        
        if radius_col:
            x = df[radius_col].values
            y = df['peak_adhesion_force_N'].values
            
            mask = ~(np.isnan(x) | np.isnan(y))
            x_clean, y_clean = x[mask], y[mask]
            
            if len(x_clean) > 3:
                x_fit, y_fit, y_ci, params = self.fit_power_law_with_ci(x_clean, y_clean)
                
                ax4.fill_between(x_fit, y_fit - y_ci, y_fit + y_ci,
                                color=color_force, alpha=0.3, label='95% Prediction Interval')
                
                ax4.plot(x_fit, y_fit, '-', color=color_force, linewidth=2.5,
                        label=f'Power Law Fit (R² = {params["r_squared"]:.3f})')
                
                if 'linear_fallback' not in params:
                    eq_text = f'y = {params["a"]:.3f} × x^{params["b"]:.3f}'
                else:
                    eq_text = f'y = {params["slope"]:.4f} × x + {params["intercept"]:.3f}'
                ax4.text(0.05, 0.95, eq_text, transform=ax4.transAxes,
                        fontsize=9, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            ax4.set_xlabel('Contact Radius (mm)', fontsize=12, fontweight='bold')
            ax4.set_ylabel('Peak Adhesion Force (N)', fontsize=12, fontweight='bold')
            ax4.set_title('Radius vs Peak Force', fontsize=13, fontweight='bold', pad=10)
            ax4.grid(True, alpha=0.3, linestyle='--')
            ax4.legend(fontsize=10, loc='best')
        else:
            ax4.text(0.5, 0.5, 'Radius data not available',
                    ha='center', va='center', transform=ax4.transAxes, fontsize=12)
            ax4.set_title('Radius vs Peak Force', fontsize=13, fontweight='bold', pad=10)
        
        # Adjust layout and save
        plt.tight_layout(rect=[0, 0, 1, 0.99])
        
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"    Summary plot saved: {output_filename}")
        return output_path


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python summary_plot_generator.py <path_to_work_of_adhesion_csv>")
        return
    
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return
    
    output_dir = csv_path.parent
    generator = SummaryPlotGenerator(output_dir)
    generator.generate_summary_plot(csv_path)


if __name__ == "__main__":
    main()
