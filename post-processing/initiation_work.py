"""
Initiation Work Calculator
==========================

Separates work of adhesion into:
1. Initiation work: Energy to nucleate crack (baseline to peak)
2. Propagation work: Energy to propagate crack (peak to detachment)

This addresses the question: How much energy is needed to START
crack formation vs. CONTINUE crack propagation?

Usage:
    from initiation_work import InitiationWorkCalculator
    
    calculator = InitiationWorkCalculator()
    initiation_work, propagation_work = calculator.calculate(force, distance, 
                                                              baseline_idx, peak_idx, end_idx)

Author: Cheng Sun Lab Team
Date: October 29, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Optional


class InitiationWorkCalculator:
    """
    Calculates initiation and propagation work from force-displacement curves.
    """
    
    def __init__(self):
        """Initialize calculator."""
        pass
    
    def calculate_work(self, force: np.ndarray, displacement: np.ndarray,
                      start_idx: int, end_idx: int) -> float:
        """
        Calculate work using trapezoidal integration.
        
        Args:
            force: Force array (N)
            displacement: Displacement array (mm)
            start_idx: Start index for integration
            end_idx: End index for integration
            
        Returns:
            Work in mJ (millijoules)
        """
        # Extract segment
        force_segment = force[start_idx:end_idx]
        disp_segment = displacement[start_idx:end_idx]
        
        # Ensure displacement is monotonically increasing
        if len(disp_segment) < 2:
            return 0.0
        
        # Trapezoidal integration: W = ∫F·dx
        work_J = np.trapz(force_segment, disp_segment / 1000.0)  # Convert mm to m
        
        work_mJ = work_J * 1000.0  # Convert J to mJ
        
        return work_mJ
    
    def calculate_initiation_work(self, force: np.ndarray, displacement: np.ndarray,
                                 baseline_idx: int, peak_idx: int) -> float:
        """
        Calculate work from baseline to peak (crack initiation).
        
        Args:
            force: Force array (N)
            displacement: Displacement array (mm)
            baseline_idx: Index where adhesion baseline starts
            peak_idx: Index where peak force occurs
            
        Returns:
            Initiation work in mJ
        """
        return self.calculate_work(force, displacement, baseline_idx, peak_idx)
    
    def calculate_propagation_work(self, force: np.ndarray, displacement: np.ndarray,
                                  peak_idx: int, end_idx: int) -> float:
        """
        Calculate work from peak to detachment (crack propagation).
        
        Args:
            force: Force array (N)
            displacement: Displacement array (mm)
            peak_idx: Index where peak force occurs
            end_idx: Index where adhesion ends (propagation end)
            
        Returns:
            Propagation work in mJ
        """
        return self.calculate_work(force, displacement, peak_idx, end_idx)
    
    def calculate_all(self, force: np.ndarray, displacement: np.ndarray,
                     baseline_idx: int, peak_idx: int, end_idx: int) -> Dict[str, float]:
        """
        Calculate all work components.
        
        Args:
            force: Force array (N)
            displacement: Displacement array (mm)
            baseline_idx: Index where adhesion baseline starts
            peak_idx: Index where peak force occurs
            end_idx: Index where adhesion ends
            
        Returns:
            Dictionary with work components
        """
        # Initiation work
        initiation_work = self.calculate_initiation_work(force, displacement, 
                                                         baseline_idx, peak_idx)
        
        # Propagation work
        propagation_work = self.calculate_propagation_work(force, displacement,
                                                           peak_idx, end_idx)
        
        # Total work (should match existing work_of_adhesion_mJ)
        total_work = self.calculate_work(force, displacement, baseline_idx, end_idx)
        
        # Fraction of work in initiation
        if total_work > 0:
            initiation_fraction = initiation_work / total_work
        else:
            initiation_fraction = np.nan
        
        return {
            'initiation_work_mJ': initiation_work,
            'propagation_work_mJ': propagation_work,
            'total_work_mJ': total_work,
            'initiation_fraction': initiation_fraction,
            'propagation_fraction': 1.0 - initiation_fraction if not np.isnan(initiation_fraction) else np.nan
        }
    
    def add_to_dataframe(self, df: pd.DataFrame, 
                        force_col: str = 'force_array',
                        disp_col: str = 'displacement_array',
                        baseline_col: str = 'baseline_idx',
                        peak_col: str = 'peak_idx',
                        end_col: str = 'propagation_end_idx') -> pd.DataFrame:
        """
        Add initiation/propagation work columns to existing DataFrame.
        
        NOTE: This requires DataFrame to have array columns with raw data.
        
        Args:
            df: DataFrame with layer metrics
            force_col: Name of column containing force arrays
            disp_col: Name of column containing displacement arrays
            baseline_col: Name of column with baseline indices
            peak_col: Name of column with peak indices
            end_col: Name of column with propagation end indices
            
        Returns:
            DataFrame with new columns added
        """
        results = []
        
        for idx, row in df.iterrows():
            if all(col in row for col in [force_col, disp_col, baseline_col, peak_col, end_col]):
                work_dict = self.calculate_all(
                    row[force_col],
                    row[disp_col],
                    row[baseline_col],
                    row[peak_col],
                    row[end_col]
                )
                results.append(work_dict)
            else:
                # Missing data
                results.append({
                    'initiation_work_mJ': np.nan,
                    'propagation_work_mJ': np.nan,
                    'total_work_mJ': np.nan,
                    'initiation_fraction': np.nan,
                    'propagation_fraction': np.nan
                })
        
        # Add columns to DataFrame
        results_df = pd.DataFrame(results)
        for col in results_df.columns:
            df[col] = results_df[col]
        
        return df
    
    def analyze_by_condition(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean initiation/propagation work by condition.
        
        Args:
            df: DataFrame with initiation_work_mJ and propagation_work_mJ columns
            
        Returns:
            Summary DataFrame by condition
        """
        if 'condition_label' not in df.columns:
            print("Warning: No condition_label column found")
            return pd.DataFrame()
        
        required_cols = ['initiation_work_mJ', 'propagation_work_mJ', 'initiation_fraction']
        
        if not all(col in df.columns for col in required_cols):
            print("Warning: Missing required work columns. Run calculate_all() first.")
            return pd.DataFrame()
        
        summary = df.groupby('condition_label').agg({
            'initiation_work_mJ': ['mean', 'std', 'count'],
            'propagation_work_mJ': ['mean', 'std'],
            'initiation_fraction': ['mean', 'std'],
            'total_work_mJ': ['mean', 'std']
        }).round(4)
        
        return summary
    
    def generate_report(self, df: pd.DataFrame, output_path: Optional[Path] = None) -> str:
        """
        Generate text report of initiation vs propagation work.
        
        Args:
            df: DataFrame with work columns
            output_path: Optional path to save report
            
        Returns:
            Report as string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("INITIATION VS PROPAGATION WORK ANALYSIS")
        lines.append("=" * 70)
        lines.append("")
        lines.append("This analysis separates the work of adhesion into two components:")
        lines.append("  1. INITIATION WORK: Energy to nucleate crack (baseline → peak)")
        lines.append("  2. PROPAGATION WORK: Energy to propagate crack (peak → detachment)")
        lines.append("")
        lines.append("-" * 70)
        
        # Summary by condition
        summary = self.analyze_by_condition(df)
        
        if len(summary) == 0:
            lines.append("ERROR: Could not generate summary. Check data.")
            report = "\n".join(lines)
            return report
        
        lines.append("SUMMARY BY CONDITION")
        lines.append("-" * 70)
        lines.append("")
        
        for condition in summary.index:
            lines.append(f"Condition: {condition}")
            lines.append(f"  Sample Size: {int(summary.loc[condition, ('initiation_work_mJ', 'count')])}")
            
            init_mean = summary.loc[condition, ('initiation_work_mJ', 'mean')]
            init_std = summary.loc[condition, ('initiation_work_mJ', 'std')]
            lines.append(f"  Initiation Work: {init_mean:.4f} ± {init_std:.4f} mJ")
            
            prop_mean = summary.loc[condition, ('propagation_work_mJ', 'mean')]
            prop_std = summary.loc[condition, ('propagation_work_mJ', 'std')]
            lines.append(f"  Propagation Work: {prop_mean:.4f} ± {prop_std:.4f} mJ")
            
            total_mean = summary.loc[condition, ('total_work_mJ', 'mean')]
            total_std = summary.loc[condition, ('total_work_mJ', 'std')]
            lines.append(f"  Total Work: {total_mean:.4f} ± {total_std:.4f} mJ")
            
            frac_mean = summary.loc[condition, ('initiation_fraction', 'mean')]
            frac_std = summary.loc[condition, ('initiation_fraction', 'std')]
            lines.append(f"  Initiation Fraction: {frac_mean:.2%} ± {frac_std:.2%}")
            
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("INTERPRETATION GUIDE")
        lines.append("-" * 70)
        lines.append("High initiation fraction (>50%):")
        lines.append("  - Significant energy barrier to crack nucleation")
        lines.append("  - Strong interfacial adhesion")
        lines.append("  - Once crack starts, propagation is relatively easy")
        lines.append("")
        lines.append("Low initiation fraction (<30%):")
        lines.append("  - Easy crack nucleation")
        lines.append("  - Most energy goes into crack propagation")
        lines.append("  - May indicate viscous dissipation or interfacial toughness")
        lines.append("=" * 70)
        
        report = "\n".join(lines)
        
        # Save to file if requested
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(report)
            print(f"Initiation work report saved to: {output_path}")
        
        return report


if __name__ == "__main__":
    """Example usage with synthetic data"""
    
    print("Demonstrating initiation work calculation...")
    print("="*60)
    
    # Create synthetic force-displacement curve
    # Simulate: rising to peak, then decaying
    
    # Baseline region (small force)
    baseline_disp = np.linspace(0, 1, 50)  # mm
    baseline_force = np.ones(50) * 0.01  # N
    
    # Rising to peak
    rising_disp = np.linspace(1, 2, 100)
    rising_force = 0.01 + (rising_disp - 1) * 0.5  # Linear rise to 0.51 N
    
    # Peak
    peak_disp = np.array([2.0])
    peak_force = np.array([0.51])
    
    # Decay (propagation)
    decay_disp = np.linspace(2, 5, 150)
    decay_force = 0.51 * np.exp(-(decay_disp - 2) / 1.5)  # Exponential decay
    
    # Combine
    displacement = np.concatenate([baseline_disp, rising_disp, peak_disp, decay_disp])
    force = np.concatenate([baseline_force, rising_force, peak_force, decay_force])
    
    # Indices
    baseline_idx = 50  # Start of rising
    peak_idx = 150     # Peak location
    end_idx = 300      # End of decay
    
    # Calculate
    calculator = InitiationWorkCalculator()
    results = calculator.calculate_all(force, displacement, baseline_idx, peak_idx, end_idx)
    
    # Print results
    print("\nSynthetic Data Results:")
    print("-"*60)
    for key, value in results.items():
        if 'fraction' in key:
            print(f"{key:30s}: {value:.2%}")
        else:
            print(f"{key:30s}: {value:.4f} mJ")
    
    print("\n" + "="*60)
    print("\nNOTE: To use with real data:")
    print("  1. Load raw force and displacement arrays")
    print("  2. Identify baseline_idx, peak_idx, end_idx from metrics")
    print("  3. Call calculate_all() to get work breakdown")
