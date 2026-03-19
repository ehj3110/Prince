"""
Master Analysis Pipeline - Complete Workflow
============================================

Orchestrates the complete modular analysis pipeline:
1. Batch processing (optional)
2. Quality control validation
3. Normalized metrics and scaling analysis
4. Statistical analysis (ANOVA, t-tests)
5. Report generation

Usage:
    python run_complete_analysis.py --folder V3
    python run_complete_analysis.py --folder V4 --skip-batch

Author: Cheng Sun Lab Team
Date: October 29, 2025
"""

import sys
import argparse
from pathlib import Path
import pandas as pd

# Import analysis modules
from data_validator import DataValidator
from advanced_metrics import AdvancedMetricsCalculator
from statistical_analysis import StatisticalAnalyzer
from generate_analysis_report import ReportGenerator


class MasterAnalysisPipeline:
    """
    Orchestrates the complete analysis workflow.
    """
    
    def __init__(self, base_dir: Path = None):
        """
        Initialize pipeline.
        
        Args:
            base_dir: Base directory for SteppedCone tests
        """
        if base_dir is None:
            self.base_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests")
        else:
            self.base_dir = Path(base_dir)
    
    def run_batch_processing(self, folder: str):
        """
        Run batch processing to generate MASTER CSV.
        
        Args:
            folder: Folder name (e.g., 'V3')
        """
        print("\n" + "="*70)
        print("STEP 1: Batch Processing")
        print("="*70)
        
        # Import batch processor
        import subprocess
        
        script_path = Path(__file__).parent / "batch_process_steppedcone_generalized.py"
        
        # Run as subprocess
        result = subprocess.run(
            [sys.executable, str(script_path), '--folder', folder],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error running batch processing:\n{result.stderr}")
            return False
        
        print(result.stdout)
        print("\n✓ Batch processing complete")
        return True
    
    def run_quality_control(self, master_csv: Path) -> dict:
        """
        Run data validation and QC checks.
        
        Args:
            master_csv: Path to MASTER CSV
            
        Returns:
            QC results dictionary
        """
        print("\n" + "="*70)
        print("STEP 2: Quality Control")
        print("="*70)
        
        df = pd.read_csv(master_csv)
        
        validator = DataValidator()
        qc_results = validator.validate(df)
        
        # Generate report
        qc_report_path = master_csv.parent / "QC_Report.txt"
        validator.generate_qc_report(qc_results, output_path=qc_report_path)
        
        print(f"\n✓ QC report saved to: {qc_report_path}")
        
        return qc_results
    
    def run_advanced_metrics(self, master_csv: Path) -> Path:
        """
        Calculate normalized metrics and perform scaling analysis.
        
        Args:
            master_csv: Path to MASTER CSV
            
        Returns:
            Path to enhanced CSV with new metrics
        """
        print("\n" + "="*70)
        print("STEP 3: Advanced Metrics & Scaling Analysis")
        print("="*70)
        
        df = pd.read_csv(master_csv)
        
        calculator = AdvancedMetricsCalculator()
        
        # Add normalized metrics
        print("Calculating normalized metrics...")
        df_enhanced = calculator.calculate_normalized_metrics(df)
        
        # Perform scaling analysis
        print("Performing scaling analysis...")
        calculator.generate_scaling_report(df_enhanced, output_dir=master_csv.parent)
        
        # Save enhanced CSV
        enhanced_csv = master_csv.parent / "MASTER_steppedcone_metrics_ENHANCED.csv"
        df_enhanced.to_csv(enhanced_csv, index=False)
        
        print(f"\n✓ Enhanced CSV saved to: {enhanced_csv}")
        
        return enhanced_csv
    
    def run_statistical_analysis(self, master_csv: Path):
        """
        Run statistical tests (ANOVA, pairwise comparisons).
        
        Args:
            master_csv: Path to MASTER CSV
        """
        print("\n" + "="*70)
        print("STEP 4: Statistical Analysis")
        print("="*70)
        
        df = pd.read_csv(master_csv)
        
        analyzer = StatisticalAnalyzer(alpha=0.05)
        results = analyzer.analyze_all_metrics(df)
        
        # Generate report
        stats_report_path = master_csv.parent / "Statistical_Analysis_Report.txt"
        analyzer.generate_report(results, output_path=stats_report_path)
        
        # Save detailed results
        analyzer.save_results_csv(results, output_dir=master_csv.parent)
        
        print(f"\n✓ Statistical analysis complete")
    
    def generate_final_report(self, master_csv: Path) -> Path:
        """
        Generate comprehensive PDF report.
        
        Args:
            master_csv: Path to MASTER CSV
            
        Returns:
            Path to PDF report
        """
        print("\n" + "="*70)
        print("STEP 5: Report Generation")
        print("="*70)
        
        generator = ReportGenerator()
        
        # Generate quick summary
        summary_path = master_csv.parent / "Quick_Summary.txt"
        generator.generate_quick_summary(master_csv, output_path=summary_path)
        
        # Generate full PDF report
        pdf_path = generator.generate_full_report(
            master_csv,
            output_dir=master_csv.parent,
            include_qc=True,
            include_stats=True,
            include_scaling=True,
            include_plots=True
        )
        
        if pdf_path:
            print(f"\n✓ PDF report generated: {pdf_path}")
        else:
            print("\n⚠ PDF generation failed (may require matplotlib)")
        
        return pdf_path
    
    def run_full_pipeline(self, folder: str, skip_batch: bool = False):
        """
        Run the complete analysis pipeline.
        
        Args:
            folder: Folder name (e.g., 'V3')
            skip_batch: Skip batch processing (use existing MASTER CSV)
        """
        print("\n" + "="*70)
        print("MASTER ANALYSIS PIPELINE")
        print(f"Folder: {folder}")
        print("="*70)
        
        folder_path = self.base_dir / folder
        master_csv = folder_path / "MASTER_steppedcone_metrics.csv"
        
        # Step 1: Batch processing (optional)
        if not skip_batch:
            success = self.run_batch_processing(folder)
            if not success:
                print("\nERROR: Batch processing failed")
                return
        else:
            print("\n⊳ Skipping batch processing (using existing MASTER CSV)")
            
            if not master_csv.exists():
                print(f"\nERROR: MASTER CSV not found: {master_csv}")
                print("Run without --skip-batch first.")
                return
        
        # Step 2: Quality control
        qc_results = self.run_quality_control(master_csv)
        
        # Step 3: Advanced metrics
        enhanced_csv = self.run_advanced_metrics(master_csv)
        
        # Step 4: Statistical analysis
        self.run_statistical_analysis(master_csv)
        
        # Step 5: Generate report
        pdf_path = self.generate_final_report(master_csv)
        
        # Summary
        print("\n" + "="*70)
        print("PIPELINE COMPLETE")
        print("="*70)
        print(f"✓ Data validated and QC report generated")
        print(f"✓ Normalized metrics added")
        print(f"✓ Scaling analysis performed")
        print(f"✓ Statistical tests completed")
        print(f"✓ Reports generated")
        print(f"\nOutput directory: {folder_path}")
        print("="*70 + "\n")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run complete adhesion analysis pipeline"
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        required=True,
        help='Folder name (e.g., V3, V4)'
    )
    
    parser.add_argument(
        '--base-dir',
        type=str,
        default=None,
        help='Base directory for SteppedCone tests (optional)'
    )
    
    parser.add_argument(
        '--skip-batch',
        action='store_true',
        help='Skip batch processing (use existing MASTER CSV)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Create pipeline
    pipeline = MasterAnalysisPipeline(base_dir=args.base_dir)
    
    # Run full pipeline
    pipeline.run_full_pipeline(
        folder=args.folder,
        skip_batch=args.skip_batch
    )


if __name__ == "__main__":
    main()
