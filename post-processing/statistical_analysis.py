"""
Statistical Analysis - ANOVA and Pairwise Comparisons
=====================================================

Performs statistical tests to identify significant differences between conditions.

Features:
- One-way ANOVA across all conditions
- Pairwise t-tests with multiple comparison correction
- Effect size calculations (Cohen's d)
- Statistical summary reports

Usage:
    from statistical_analysis import StatisticalAnalyzer
    
    analyzer = StatisticalAnalyzer()
    results = analyzer.analyze(master_df)
    analyzer.generate_report(results, output_path='Statistical_Analysis.txt')

Author: Cheng Sun Lab Team
Date: October 29, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from scipy import stats
from itertools import combinations
from datetime import datetime


class StatisticalAnalyzer:
    """
    Performs statistical analysis on batch processing results.
    """
    
    def __init__(self, alpha: float = 0.05):
        """
        Initialize analyzer.
        
        Args:
            alpha: Significance level (default 0.05)
        """
        self.alpha = alpha
    
    def cohen_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """
        Calculate Cohen's d effect size.
        
        Args:
            group1: First group data
            group2: Second group data
            
        Returns:
            Cohen's d value
        """
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        # Effect size
        d = (np.mean(group1) - np.mean(group2)) / pooled_std
        
        return d
    
    def interpret_effect_size(self, d: float) -> str:
        """
        Interpret Cohen's d effect size.
        
        Args:
            d: Cohen's d value
            
        Returns:
            Interpretation string
        """
        abs_d = abs(d)
        
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"
    
    def run_anova(self, df: pd.DataFrame, metric: str) -> Dict:
        """
        Perform one-way ANOVA across all conditions.
        
        Args:
            df: DataFrame with data
            metric: Metric to analyze
            
        Returns:
            Dictionary with ANOVA results
        """
        # Get groups
        groups = []
        condition_labels = []
        
        for condition in df['condition_label'].unique():
            condition_data = df[df['condition_label'] == condition][metric].dropna()
            if len(condition_data) > 0:
                groups.append(condition_data.values)
                condition_labels.append(condition)
        
        if len(groups) < 2:
            return {
                'metric': metric,
                'n_groups': len(groups),
                'error': 'Need at least 2 groups for ANOVA'
            }
        
        # Run ANOVA
        f_stat, p_value = stats.f_oneway(*groups)
        
        # Calculate group statistics
        group_stats = []
        for label, data in zip(condition_labels, groups):
            group_stats.append({
                'condition': label,
                'n': len(data),
                'mean': np.mean(data),
                'std': np.std(data, ddof=1),
                'sem': stats.sem(data)
            })
        
        return {
            'metric': metric,
            'n_groups': len(groups),
            'f_statistic': f_stat,
            'p_value': p_value,
            'significant': p_value < self.alpha,
            'group_stats': group_stats
        }
    
    def pairwise_comparisons(self, df: pd.DataFrame, metric: str, 
                            correction: str = 'bonferroni') -> pd.DataFrame:
        """
        Perform pairwise t-tests with multiple comparison correction.
        
        Args:
            df: DataFrame with data
            metric: Metric to analyze
            correction: 'bonferroni' or 'none'
            
        Returns:
            DataFrame with comparison results
        """
        conditions = df['condition_label'].unique()
        
        results = []
        
        # All pairwise combinations
        for cond1, cond2 in combinations(conditions, 2):
            data1 = df[df['condition_label'] == cond1][metric].dropna().values
            data2 = df[df['condition_label'] == cond2][metric].dropna().values
            
            if len(data1) < 2 or len(data2) < 2:
                continue
            
            # Independent samples t-test
            t_stat, p_value = stats.ttest_ind(data1, data2)
            
            # Effect size
            d = self.cohen_d(data1, data2)
            
            results.append({
                'condition_1': cond1,
                'condition_2': cond2,
                'n_1': len(data1),
                'n_2': len(data2),
                'mean_1': np.mean(data1),
                'mean_2': np.mean(data2),
                't_statistic': t_stat,
                'p_value': p_value,
                'cohens_d': d,
                'effect_size': self.interpret_effect_size(d)
            })
        
        results_df = pd.DataFrame(results)
        
        # Apply multiple comparison correction
        if correction == 'bonferroni' and len(results_df) > 0:
            results_df['p_adjusted'] = results_df['p_value'] * len(results_df)
            results_df['p_adjusted'] = results_df['p_adjusted'].clip(upper=1.0)
            results_df['significant'] = results_df['p_adjusted'] < self.alpha
        else:
            results_df['p_adjusted'] = results_df['p_value']
            results_df['significant'] = results_df['p_value'] < self.alpha
        
        return results_df
    
    def analyze_all_metrics(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Run complete statistical analysis on all metrics.
        
        Args:
            df: DataFrame with data
            
        Returns:
            Dictionary with results for each metric
        """
        metrics = [
            'peak_force_N',
            'work_of_adhesion_mJ',
            'peel_distance_mm',
            'effective_stiffness_N_per_mm',
            'retraction_force_N'
        ]
        
        results = {}
        
        print("\n" + "="*60)
        print("Statistical Analysis")
        print("="*60 + "\n")
        
        for metric in metrics:
            if metric not in df.columns:
                continue
            
            print(f"Analyzing {metric}...")
            
            # ANOVA
            anova_results = self.run_anova(df, metric)
            
            # Pairwise comparisons
            pairwise_results = self.pairwise_comparisons(df, metric)
            
            results[metric] = {
                'anova': anova_results,
                'pairwise': pairwise_results
            }
            
            print(f"  ANOVA: F={anova_results.get('f_statistic', 'N/A'):.2f}, "
                  f"p={anova_results.get('p_value', 'N/A'):.4f}")
            
            if pairwise_results is not None and len(pairwise_results) > 0:
                n_significant = pairwise_results['significant'].sum()
                print(f"  Pairwise: {n_significant}/{len(pairwise_results)} significant")
        
        print(f"\n{'='*60}\n")
        
        return results
    
    def generate_report(self, results: Dict, output_path: Path = None) -> str:
        """
        Generate text report of statistical analysis.
        
        Args:
            results: Dictionary from analyze_all_metrics()
            output_path: Optional path to save report
            
        Returns:
            Report as string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("STATISTICAL ANALYSIS REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Significance Level: α = {self.alpha}")
        lines.append("=" * 70)
        lines.append("")
        
        for metric, metric_results in results.items():
            lines.append("-" * 70)
            lines.append(f"METRIC: {metric}")
            lines.append("-" * 70)
            lines.append("")
            
            # ANOVA results
            anova = metric_results['anova']
            
            if 'error' in anova:
                lines.append(f"ANOVA: {anova['error']}")
                lines.append("")
                continue
            
            lines.append("ONE-WAY ANOVA")
            lines.append(f"  F-statistic: {anova['f_statistic']:.4f}")
            lines.append(f"  p-value: {anova['p_value']:.6f}")
            lines.append(f"  Significant: {'YES' if anova['significant'] else 'NO'}")
            lines.append(f"  Number of groups: {anova['n_groups']}")
            lines.append("")
            
            # Group statistics
            lines.append("GROUP STATISTICS")
            for stat in anova['group_stats']:
                lines.append(f"  {stat['condition']}:")
                lines.append(f"    n = {stat['n']}")
                lines.append(f"    Mean ± SEM = {stat['mean']:.4f} ± {stat['sem']:.4f}")
                lines.append(f"    Std Dev = {stat['std']:.4f}")
            lines.append("")
            
            # Pairwise comparisons
            pairwise = metric_results['pairwise']
            
            if pairwise is not None and len(pairwise) > 0:
                lines.append("PAIRWISE COMPARISONS (Bonferroni corrected)")
                lines.append("")
                
                # Show significant comparisons first
                significant = pairwise[pairwise['significant'] == True]
                
                if len(significant) > 0:
                    lines.append(f"  SIGNIFICANT DIFFERENCES ({len(significant)}):")
                    for idx, row in significant.iterrows():
                        lines.append(f"    {row['condition_1']} vs {row['condition_2']}:")
                        lines.append(f"      Mean difference: {row['mean_1'] - row['mean_2']:.4f}")
                        lines.append(f"      p-value (adj): {row['p_adjusted']:.6f}")
                        lines.append(f"      Cohen's d: {row['cohens_d']:.3f} ({row['effect_size']})")
                        lines.append("")
                else:
                    lines.append("  No significant pairwise differences found.")
                    lines.append("")
                
                # Show non-significant comparisons
                non_significant = pairwise[pairwise['significant'] == False]
                
                if len(non_significant) > 0:
                    lines.append(f"  NON-SIGNIFICANT COMPARISONS ({len(non_significant)}):")
                    for idx, row in non_significant.head(5).iterrows():
                        lines.append(f"    {row['condition_1']} vs {row['condition_2']}: "
                                   f"p={row['p_adjusted']:.4f}, d={row['cohens_d']:.3f}")
                    
                    if len(non_significant) > 5:
                        lines.append(f"    ... and {len(non_significant) - 5} more")
                    lines.append("")
            
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("NOTES:")
        lines.append("  - ANOVA tests if at least one group differs from others")
        lines.append("  - Pairwise t-tests identify which specific groups differ")
        lines.append("  - Bonferroni correction controls family-wise error rate")
        lines.append("  - Cohen's d: <0.2=negligible, 0.2-0.5=small, 0.5-0.8=medium, >0.8=large")
        lines.append("=" * 70)
        
        report = "\n".join(lines)
        
        # Save to file if requested
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(report)
            print(f"Statistical analysis report saved to: {output_path}")
        
        return report
    
    def save_results_csv(self, results: Dict, output_dir: Path):
        """
        Save detailed results to CSV files.
        
        Args:
            results: Dictionary from analyze_all_metrics()
            output_dir: Directory to save CSV files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save ANOVA results
        anova_rows = []
        for metric, metric_results in results.items():
            anova = metric_results['anova']
            if 'error' not in anova:
                anova_rows.append({
                    'metric': metric,
                    'f_statistic': anova['f_statistic'],
                    'p_value': anova['p_value'],
                    'significant': anova['significant'],
                    'n_groups': anova['n_groups']
                })
        
        if anova_rows:
            anova_df = pd.DataFrame(anova_rows)
            anova_path = output_dir / "ANOVA_results.csv"
            anova_df.to_csv(anova_path, index=False)
            print(f"ANOVA results saved to: {anova_path}")
        
        # Save pairwise results
        for metric, metric_results in results.items():
            pairwise = metric_results['pairwise']
            if pairwise is not None and len(pairwise) > 0:
                pairwise_path = output_dir / f"pairwise_{metric}.csv"
                pairwise.to_csv(pairwise_path, index=False)
                print(f"Pairwise comparisons saved to: {pairwise_path}")


if __name__ == "__main__":
    """Example usage"""
    
    # Load master CSV
    master_csv = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V3\MASTER_steppedcone_metrics.csv")
    
    if master_csv.exists():
        df = pd.read_csv(master_csv)
        
        # Create analyzer
        analyzer = StatisticalAnalyzer(alpha=0.05)
        
        # Run analysis
        results = analyzer.analyze_all_metrics(df)
        
        # Generate report
        report = analyzer.generate_report(results, output_path=master_csv.parent / "Statistical_Analysis_Report.txt")
        
        # Save detailed results
        analyzer.save_results_csv(results, output_dir=master_csv.parent)
        
        print(report)
        
    else:
        print(f"Master CSV not found: {master_csv}")
        print("Please run batch processing first.")
