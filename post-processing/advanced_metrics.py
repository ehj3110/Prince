"""
Advanced Metrics Calculator
============================

Calculates normalized metrics and scaling analysis from batch processing results.

Features:
- Adhesion intensity (force/area, work/area)
- Power-law scaling analysis
- Area-independent comparisons

Usage:
    from advanced_metrics import AdvancedMetricsCalculator
    
    calculator = AdvancedMetricsCalculator()
    enhanced_df = calculator.calculate_all_metrics(master_df)
    
    # Get scaling law results
    scaling_results = calculator.fit_scaling_laws(master_df)

Author: Cheng Sun Lab Team
Date: October 29, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
from scipy import stats


class AdvancedMetricsCalculator:
    """
    Calculates advanced metrics from batch processing results.
    """
    
    def __init__(self):
        """Initialize the calculator"""
        pass
    
    def calculate_normalized_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate area-normalized (intensity) metrics.
        
        These metrics are independent of contact area and represent
        intrinsic material properties.
        
        Args:
            df: DataFrame with batch processing results
            
        Returns:
            DataFrame with additional normalized columns
        """
        df = df.copy()
        
        # Adhesion strength (force per unit area)
        df['adhesion_strength_kPa'] = (df['peak_force_N'] / df['area_mm2']) * 1000
        
        # Work of adhesion per unit area
        df['work_per_area_mJ_per_mm2'] = df['work_of_adhesion_mJ'] / df['area_mm2']
        
        # Stiffness per unit area
        df['stiffness_per_area_MPa'] = df['effective_stiffness_N_per_mm'] / df['area_mm2']
        
        # Distance metrics (already independent of area, but useful to confirm)
        df['peel_distance_per_area_mm_per_mm2'] = df['peel_distance_mm'] / df['area_mm2']
        
        # Retraction force per unit area
        df['retraction_strength_kPa'] = (df['peak_retraction_force_N'] / df['area_mm2']) * 1000
        
        print("✓ Calculated normalized metrics:")
        print("  - adhesion_strength_kPa")
        print("  - work_per_area_mJ_per_mm2")
        print("  - stiffness_per_area_MPa")
        print("  - retraction_strength_kPa")
        
        return df
    
    def fit_scaling_law(self, df: pd.DataFrame, 
                       y_metric: str = 'peak_force_N',
                       x_metric: str = 'area_mm2',
                       condition: Optional[str] = None) -> Dict:
        """
        Fit power-law scaling: y = k * x^n
        
        Theory predicts:
        - Perfect scaling: Force = constant * Area^1
        - Edge-dominated: Force ~ Area^0.5 (perimeter effect)
        - Cooperative failure: Force ~ Area^>1
        
        Args:
            df: DataFrame with data
            y_metric: Dependent variable (e.g., 'peak_force_N')
            x_metric: Independent variable (e.g., 'area_mm2')
            condition: Filter to specific condition (e.g., 'Water_1mm_1000um_s')
            
        Returns:
            Dictionary with fit results
        """
        # Filter data if condition specified
        if condition:
            data = df[df['condition_label'] == condition].copy()
            label = condition
        else:
            data = df.copy()
            label = "All data"
        
        # Remove NaN values
        data = data.dropna(subset=[x_metric, y_metric])
        
        if len(data) < 3:
            return {
                'condition': label,
                'n_points': len(data),
                'exponent': np.nan,
                'coefficient': np.nan,
                'r_squared': np.nan,
                'error': 'Insufficient data points'
            }
        
        # Log-transform for linear fit
        log_x = np.log(data[x_metric])
        log_y = np.log(data[y_metric])
        
        # Linear regression in log space
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
        
        # Convert back: y = k * x^n
        # log(y) = log(k) + n*log(x)
        # slope = n (exponent)
        # intercept = log(k) → k = exp(intercept)
        exponent = slope
        coefficient = np.exp(intercept)
        r_squared = r_value ** 2
        
        # Theoretical prediction check
        if abs(exponent - 1.0) < 0.1:
            interpretation = "Linear scaling (as expected for uniform adhesion)"
        elif exponent < 0.9:
            interpretation = "Sub-linear scaling (edge effects or size-dependent weakening)"
        else:
            interpretation = "Super-linear scaling (cooperative failure or size-dependent strengthening)"
        
        return {
            'condition': label,
            'n_points': len(data),
            'exponent': exponent,
            'exponent_stderr': std_err,
            'coefficient': coefficient,
            'r_squared': r_squared,
            'p_value': p_value,
            'interpretation': interpretation,
            'formula': f"{y_metric} = {coefficient:.4f} * {x_metric}^{exponent:.3f}"
        }
    
    def fit_scaling_laws_by_condition(self, df: pd.DataFrame,
                                      y_metric: str = 'peak_force_N',
                                      x_metric: str = 'area_mm2') -> pd.DataFrame:
        """
        Fit scaling laws for each condition separately.
        
        Args:
            df: DataFrame with data
            y_metric: Dependent variable
            x_metric: Independent variable
            
        Returns:
            DataFrame with scaling law parameters for each condition
        """
        results = []
        
        for condition in sorted(df['condition_label'].unique()):
            result = self.fit_scaling_law(df, y_metric, x_metric, condition)
            results.append(result)
        
        # Also fit overall (all conditions combined)
        overall = self.fit_scaling_law(df, y_metric, x_metric, condition=None)
        results.append(overall)
        
        results_df = pd.DataFrame(results)
        
        print(f"\n{'='*60}")
        print(f"Scaling Law Analysis: {y_metric} vs {x_metric}")
        print(f"{'='*60}")
        print(results_df.to_string(index=False))
        print(f"{'='*60}\n")
        
        return results_df
    
    def plot_scaling_analysis(self, df: pd.DataFrame,
                             y_metric: str = 'peak_force_N',
                             x_metric: str = 'area_mm2',
                             output_path: Optional[Path] = None):
        """
        Create scaling analysis plot with log-log axes.
        
        Args:
            df: DataFrame with data
            y_metric: Dependent variable
            x_metric: Independent variable
            output_path: Where to save plot
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Get unique conditions and colors
        conditions = sorted(df['condition_label'].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
        
        # Left plot: Linear scale
        ax = axes[0]
        for condition, color in zip(conditions, colors):
            data = df[df['condition_label'] == condition]
            ax.scatter(data[x_metric], data[y_metric], 
                      color=color, alpha=0.6, label=condition, s=30)
            
            # Fit and plot scaling law
            result = self.fit_scaling_law(df, y_metric, x_metric, condition)
            if not np.isnan(result['exponent']):
                x_fit = np.linspace(data[x_metric].min(), data[x_metric].max(), 100)
                y_fit = result['coefficient'] * x_fit ** result['exponent']
                ax.plot(x_fit, y_fit, '--', color=color, alpha=0.8, linewidth=1.5,
                       label=f"n={result['exponent']:.2f}")
        
        ax.set_xlabel(x_metric.replace('_', ' ').title())
        ax.set_ylabel(y_metric.replace('_', ' ').title())
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_title('Linear Scale')
        
        # Right plot: Log-log scale
        ax = axes[1]
        for condition, color in zip(conditions, colors):
            data = df[df['condition_label'] == condition]
            ax.scatter(data[x_metric], data[y_metric], 
                      color=color, alpha=0.6, label=condition, s=30)
            
            # Fit and plot scaling law
            result = self.fit_scaling_law(df, y_metric, x_metric, condition)
            if not np.isnan(result['exponent']):
                x_fit = np.linspace(data[x_metric].min(), data[x_metric].max(), 100)
                y_fit = result['coefficient'] * x_fit ** result['exponent']
                ax.plot(x_fit, y_fit, '--', color=color, alpha=0.8, linewidth=1.5,
                       label=f"n={result['exponent']:.2f}")
        
        ax.set_xlabel(x_metric.replace('_', ' ').title())
        ax.set_ylabel(y_metric.replace('_', ' ').title())
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3, which='both')
        ax.set_title('Log-Log Scale (Power Law)')
        
        plt.suptitle(f'Scaling Analysis: {y_metric} vs {x_metric}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Saved scaling analysis plot: {output_path}")
        
        plt.close()
    
    def calculate_all_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all advanced metrics.
        
        Args:
            df: DataFrame from batch processing
            
        Returns:
            Enhanced DataFrame with normalized metrics
        """
        print("\n" + "="*60)
        print("Calculating Advanced Metrics")
        print("="*60 + "\n")
        
        df = self.calculate_normalized_metrics(df)
        
        return df
    
    def generate_scaling_report(self, df: pd.DataFrame, 
                                output_dir: Path,
                                metrics_to_analyze: List[str] = None):
        """
        Generate comprehensive scaling analysis report.
        
        Args:
            df: DataFrame with data
            output_dir: Directory to save outputs
            metrics_to_analyze: List of metrics to analyze (default: force and work)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        if metrics_to_analyze is None:
            metrics_to_analyze = ['peak_force_N', 'work_of_adhesion_mJ']
        
        print("\n" + "="*60)
        print("Generating Scaling Analysis Report")
        print("="*60 + "\n")
        
        all_results = []
        
        for metric in metrics_to_analyze:
            # Fit scaling laws
            results_df = self.fit_scaling_laws_by_condition(df, y_metric=metric, x_metric='area_mm2')
            results_df['metric'] = metric
            all_results.append(results_df)
            
            # Generate plot
            plot_path = output_dir / f"scaling_analysis_{metric}.png"
            self.plot_scaling_analysis(df, y_metric=metric, x_metric='area_mm2', output_path=plot_path)
        
        # Combine all results
        combined_results = pd.concat(all_results, ignore_index=True)
        
        # Save to CSV
        csv_path = output_dir / "scaling_analysis_results.csv"
        combined_results.to_csv(csv_path, index=False)
        print(f"Saved scaling analysis results: {csv_path}")
        
        return combined_results


if __name__ == "__main__":
    """Example usage"""
    
    # Load master CSV
    master_csv = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V3\MASTER_steppedcone_metrics.csv")
    
    if master_csv.exists():
        df = pd.read_csv(master_csv)
        
        # Create calculator
        calc = AdvancedMetricsCalculator()
        
        # Calculate normalized metrics
        df_enhanced = calc.calculate_all_metrics(df)
        
        # Save enhanced CSV
        output_path = master_csv.parent / "MASTER_steppedcone_metrics_enhanced.csv"
        df_enhanced.to_csv(output_path, index=False)
        print(f"\nSaved enhanced metrics: {output_path}")
        
        # Generate scaling analysis report
        calc.generate_scaling_report(df_enhanced, master_csv.parent)
        
    else:
        print(f"Master CSV not found: {master_csv}")
        print("Please run batch processing first.")
