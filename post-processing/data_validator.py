"""
Data Validator - Quality Control for Batch Processing
======================================================

Validates batch processing results and flags potential data quality issues.

Features:
- Check for physically impossible values
- Outlier detection (>3 sigma from mean)
- Missing data detection
- Generate QC summary report

Usage:
    from data_validator import DataValidator
    
    validator = DataValidator()
    qc_results = validator.validate(master_df)
    validator.generate_qc_report(qc_results, output_path='QC_Report.txt')

Author: Cheng Sun Lab Team
Date: October 29, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class DataValidator:
    """
    Validates data quality and flags issues.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize validator with configuration.
        
        Args:
            config: Dictionary with validation thresholds
        """
        # Default configuration
        self.config = {
            'max_force_N': 5.0,
            'max_work_mJ': 10.0,
            'min_stiffness_N_per_mm': 0.0,
            'outlier_sigma': 3.0,
            'check_negative_force': True,
            'check_missing_data': True,
        }
        
        # Update with user config
        if config:
            self.config.update(config)
    
    def check_negative_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Check for negative values in metrics that should be positive.
        
        Args:
            df: DataFrame to check
            
        Returns:
            DataFrame with flagged rows
        """
        issues = []
        
        # Metrics that should never be negative
        positive_metrics = [
            'peak_force_N',
            'work_of_adhesion_mJ',
            'area_mm2',
            'effective_stiffness_N_per_mm'
        ]
        
        for metric in positive_metrics:
            if metric in df.columns:
                negative_rows = df[df[metric] < 0]
                for idx, row in negative_rows.iterrows():
                    issues.append({
                        'layer_number': row['layer_number'],
                        'condition': row['condition_label'],
                        'issue_type': 'negative_value',
                        'metric': metric,
                        'value': row[metric],
                        'severity': 'HIGH'
                    })
        
        return pd.DataFrame(issues)
    
    def check_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect statistical outliers (>3 sigma from mean).
        
        Args:
            df: DataFrame to check
            
        Returns:
            DataFrame with flagged outliers
        """
        issues = []
        
        # Metrics to check for outliers
        metrics_to_check = [
            'peak_force_N',
            'work_of_adhesion_mJ',
            'peel_distance_mm',
            'effective_stiffness_N_per_mm'
        ]
        
        # Check within each condition separately
        for condition in df['condition_label'].unique():
            condition_data = df[df['condition_label'] == condition]
            
            for metric in metrics_to_check:
                if metric in df.columns:
                    values = condition_data[metric].dropna()
                    
                    if len(values) < 3:
                        continue  # Need at least 3 points for statistics
                    
                    mean = values.mean()
                    std = values.std()
                    
                    # Flag values beyond threshold
                    outliers = condition_data[
                        np.abs(condition_data[metric] - mean) > self.config['outlier_sigma'] * std
                    ]
                    
                    for idx, row in outliers.iterrows():
                        z_score = (row[metric] - mean) / std
                        issues.append({
                            'layer_number': row['layer_number'],
                            'condition': condition,
                            'issue_type': 'outlier',
                            'metric': metric,
                            'value': row[metric],
                            'z_score': z_score,
                            'mean': mean,
                            'std': std,
                            'severity': 'MEDIUM' if abs(z_score) < 4 else 'HIGH'
                        })
        
        return pd.DataFrame(issues)
    
    def check_missing_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Check for missing critical metrics.
        
        Args:
            df: DataFrame to check
            
        Returns:
            DataFrame with missing data issues
        """
        issues = []
        
        # Critical metrics that should always be present
        critical_metrics = [
            'peak_force_N',
            'work_of_adhesion_mJ',
            'area_mm2'
        ]
        
        for idx, row in df.iterrows():
            for metric in critical_metrics:
                if pd.isna(row[metric]):
                    issues.append({
                        'layer_number': row['layer_number'],
                        'condition': row['condition_label'],
                        'issue_type': 'missing_data',
                        'metric': metric,
                        'value': None,
                        'severity': 'HIGH'
                    })
        
        return pd.DataFrame(issues)
    
    def check_physical_limits(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Check if values exceed physically realistic limits.
        
        Args:
            df: DataFrame to check
            
        Returns:
            DataFrame with limit violations
        """
        issues = []
        
        # Check peak force
        if 'peak_force_N' in df.columns:
            excessive_force = df[df['peak_force_N'] > self.config['max_force_N']]
            for idx, row in excessive_force.iterrows():
                issues.append({
                    'layer_number': row['layer_number'],
                    'condition': row['condition_label'],
                    'issue_type': 'exceeds_limit',
                    'metric': 'peak_force_N',
                    'value': row['peak_force_N'],
                    'limit': self.config['max_force_N'],
                    'severity': 'MEDIUM'
                })
        
        # Check work of adhesion
        if 'work_of_adhesion_mJ' in df.columns:
            excessive_work = df[df['work_of_adhesion_mJ'] > self.config['max_work_mJ']]
            for idx, row in excessive_work.iterrows():
                issues.append({
                    'layer_number': row['layer_number'],
                    'condition': row['condition_label'],
                    'issue_type': 'exceeds_limit',
                    'metric': 'work_of_adhesion_mJ',
                    'value': row['work_of_adhesion_mJ'],
                    'limit': self.config['max_work_mJ'],
                    'severity': 'MEDIUM'
                })
        
        return pd.DataFrame(issues)
    
    def validate(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Run all validation checks.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dictionary of issue DataFrames by check type
        """
        print("\n" + "="*60)
        print("Running Data Quality Checks")
        print("="*60 + "\n")
        
        results = {}
        
        if self.config['check_negative_force']:
            print("Checking for negative values...")
            results['negative_values'] = self.check_negative_values(df)
            print(f"  Found {len(results['negative_values'])} issues")
        
        print("Checking for outliers...")
        results['outliers'] = self.check_outliers(df)
        print(f"  Found {len(results['outliers'])} outliers")
        
        if self.config['check_missing_data']:
            print("Checking for missing data...")
            results['missing_data'] = self.check_missing_data(df)
            print(f"  Found {len(results['missing_data'])} missing values")
        
        print("Checking physical limits...")
        results['limit_violations'] = self.check_physical_limits(df)
        print(f"  Found {len(results['limit_violations'])} limit violations")
        
        # Count total issues
        total_issues = sum(len(issues_df) for issues_df in results.values())
        
        print(f"\n{'='*60}")
        print(f"Total Issues Found: {total_issues}")
        print(f"{'='*60}\n")
        
        return results
    
    def generate_qc_report(self, qc_results: Dict[str, pd.DataFrame], 
                           output_path: Path = None) -> str:
        """
        Generate a text summary of QC results.
        
        Args:
            qc_results: Dictionary from validate()
            output_path: Optional path to save report
            
        Returns:
            Report as string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("DATA QUALITY CONTROL REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")
        
        # Summary
        total_issues = sum(len(df) for df in qc_results.values())
        lines.append(f"Total Issues Found: {total_issues}")
        lines.append("")
        
        # Details for each check type
        for check_type, issues_df in qc_results.items():
            lines.append("-" * 70)
            lines.append(f"{check_type.upper().replace('_', ' ')}: {len(issues_df)} issues")
            lines.append("-" * 70)
            
            if len(issues_df) == 0:
                lines.append("  ✓ No issues found")
                lines.append("")
                continue
            
            # Group by severity
            if 'severity' in issues_df.columns:
                for severity in ['HIGH', 'MEDIUM', 'LOW']:
                    severity_issues = issues_df[issues_df['severity'] == severity]
                    if len(severity_issues) > 0:
                        lines.append(f"\n  {severity} Severity ({len(severity_issues)} issues):")
                        
                        # Show first 10 examples
                        for idx, row in severity_issues.head(10).iterrows():
                            if 'z_score' in row:
                                lines.append(
                                    f"    Layer {row['layer_number']} ({row['condition']}): "
                                    f"{row['metric']} = {row['value']:.4f} "
                                    f"(z={row['z_score']:.2f})"
                                )
                            else:
                                lines.append(
                                    f"    Layer {row['layer_number']} ({row['condition']}): "
                                    f"{row['metric']} = {row.get('value', 'N/A')}"
                                )
                        
                        if len(severity_issues) > 10:
                            lines.append(f"    ... and {len(severity_issues) - 10} more")
            else:
                # Show first 10 issues
                for idx, row in issues_df.head(10).iterrows():
                    lines.append(f"  Layer {row['layer_number']} ({row['condition']}): {row.get('metric', 'N/A')}")
                
                if len(issues_df) > 10:
                    lines.append(f"  ... and {len(issues_df) - 10} more")
            
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)
        
        report = "\n".join(lines)
        
        # Save to file if requested
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(report)
            print(f"QC report saved to: {output_path}")
        
        return report


if __name__ == "__main__":
    """Example usage"""
    
    # Load master CSV
    master_csv = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V3\MASTER_steppedcone_metrics.csv")
    
    if master_csv.exists():
        df = pd.read_csv(master_csv)
        
        # Create validator
        validator = DataValidator()
        
        # Run validation
        qc_results = validator.validate(df)
        
        # Generate report
        report = validator.generate_qc_report(qc_results, output_path=master_csv.parent / "QC_Report.txt")
        print(report)
        
    else:
        print(f"Master CSV not found: {master_csv}")
        print("Please run batch processing first.")
