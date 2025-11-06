"""
Automated Analysis Report Generator
===================================

Generates comprehensive PDF reports from batch processing results.

Features:
- Combines results from all analysis modules
- Includes plots, statistics, and QC summaries
- Generates multi-page PDF reports
- Configurable sections

Usage:
    from generate_analysis_report import ReportGenerator
    
    generator = ReportGenerator()
    generator.generate_full_report(master_csv_path, output_dir)

Author: Cheng Sun Lab Team
Date: October 29, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


class ReportGenerator:
    """
    Generates comprehensive analysis reports.
    """
    
    def __init__(self):
        """Initialize report generator."""
        self.report_sections = []
    
    def create_title_page(self, pdf: PdfPages, title: str, metadata: Dict):
        """
        Create title page for report.
        
        Args:
            pdf: PdfPages object
            title: Report title
            metadata: Dictionary with report metadata
        """
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.7, title, 
                ha='center', fontsize=24, fontweight='bold')
        
        # Metadata
        y_pos = 0.5
        for key, value in metadata.items():
            fig.text(0.5, y_pos, f"{key}: {value}", 
                    ha='center', fontsize=12)
            y_pos -= 0.05
        
        # Timestamp
        fig.text(0.5, 0.1, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                ha='center', fontsize=10, style='italic')
        
        plt.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def add_text_page(self, pdf: PdfPages, title: str, content: str):
        """
        Add a text page to the report.
        
        Args:
            pdf: PdfPages object
            title: Page title
            content: Text content
        """
        fig = plt.figure(figsize=(8.5, 11))
        
        # Title
        fig.text(0.5, 0.95, title, 
                ha='center', fontsize=16, fontweight='bold')
        
        # Content (wrapped)
        fig.text(0.1, 0.05, content, 
                ha='left', va='bottom', fontsize=9, 
                family='monospace', wrap=True)
        
        plt.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def add_plot_page(self, pdf: PdfPages, plot_path: Path, title: str = None):
        """
        Add a plot page to the report.
        
        Args:
            pdf: PdfPages object
            plot_path: Path to plot image
            title: Optional title
        """
        if not plot_path.exists():
            print(f"Warning: Plot not found: {plot_path}")
            return
        
        fig = plt.figure(figsize=(8.5, 11))
        
        if title:
            fig.text(0.5, 0.95, title, 
                    ha='center', fontsize=14, fontweight='bold')
        
        # Load and display image
        img = plt.imread(str(plot_path))
        ax = fig.add_subplot(111)
        ax.imshow(img)
        ax.axis('off')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def add_summary_table(self, pdf: PdfPages, df: pd.DataFrame, title: str):
        """
        Add a summary table page.
        
        Args:
            pdf: PdfPages object
            df: DataFrame to display
            title: Table title
        """
        fig, ax = plt.subplots(figsize=(8.5, 11))
        
        ax.axis('tight')
        ax.axis('off')
        
        # Title
        fig.text(0.5, 0.95, title, 
                ha='center', fontsize=14, fontweight='bold')
        
        # Create table
        table = ax.table(cellText=df.values, 
                        colLabels=df.columns,
                        cellLoc='center',
                        loc='center',
                        bbox=[0.1, 0.1, 0.8, 0.8])
        
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def generate_full_report(self, master_csv: Path, output_dir: Path,
                           include_qc: bool = True,
                           include_stats: bool = True,
                           include_scaling: bool = True,
                           include_plots: bool = True) -> Path:
        """
        Generate comprehensive PDF report.
        
        Args:
            master_csv: Path to MASTER CSV file
            output_dir: Directory to save report
            include_qc: Include QC section
            include_stats: Include statistical analysis
            include_scaling: Include scaling analysis
            include_plots: Include master plots
            
        Returns:
            Path to generated PDF
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Output PDF path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = output_dir / f"Analysis_Report_{timestamp}.pdf"
        
        # Load data
        if not master_csv.exists():
            print(f"Error: Master CSV not found: {master_csv}")
            return None
        
        df = pd.read_csv(master_csv)
        
        print(f"\nGenerating comprehensive analysis report...")
        print(f"Output: {pdf_path}")
        print("="*60)
        
        with PdfPages(pdf_path) as pdf:
            # Title page
            metadata = {
                'Data Source': master_csv.name,
                'Number of Layers': len(df),
                'Conditions': len(df['condition_label'].unique()),
                'Analysis Date': datetime.now().strftime('%Y-%m-%d')
            }
            self.create_title_page(pdf, "Adhesion Analysis Report", metadata)
            
            # Table of contents
            toc_content = """
TABLE OF CONTENTS

1. Data Summary
2. Quality Control Report
3. Statistical Analysis
4. Scaling Analysis
5. Master Plots
6. Appendix
            """
            self.add_text_page(pdf, "Table of Contents", toc_content)
            
            # Section 1: Data Summary
            print("Adding data summary...")
            summary_text = f"""
DATA SUMMARY

Total Layers Analyzed: {len(df)}
Conditions: {', '.join(df['condition_label'].unique())}

Metrics Calculated:
  - Peak Force (N)
  - Work of Adhesion (mJ)
  - Peel Distance (mm)
  - Effective Stiffness (N/mm)
  - Retraction Force (N)
  - Pre-initiation Time (s)

Data Range:
  Peak Force: {df['peak_force_N'].min():.4f} - {df['peak_force_N'].max():.4f} N
  Work of Adhesion: {df['work_of_adhesion_mJ'].min():.4f} - {df['work_of_adhesion_mJ'].max():.4f} mJ
            """
            self.add_text_page(pdf, "1. Data Summary", summary_text)
            
            # Section 2: Quality Control
            if include_qc:
                print("Adding QC report...")
                qc_report_path = output_dir / "QC_Report.txt"
                if qc_report_path.exists():
                    qc_content = qc_report_path.read_text()
                    self.add_text_page(pdf, "2. Quality Control Report", qc_content)
                else:
                    self.add_text_page(pdf, "2. Quality Control Report", 
                                     "QC report not found. Run data_validator.py first.")
            
            # Section 3: Statistical Analysis
            if include_stats:
                print("Adding statistical analysis...")
                stats_report_path = output_dir / "Statistical_Analysis_Report.txt"
                if stats_report_path.exists():
                    stats_content = stats_report_path.read_text()
                    # Split into pages if too long
                    lines = stats_content.split('\n')
                    page_size = 50
                    for i in range(0, len(lines), page_size):
                        page_content = '\n'.join(lines[i:i+page_size])
                        page_num = i // page_size + 1
                        self.add_text_page(pdf, f"3. Statistical Analysis (Page {page_num})", 
                                         page_content)
                else:
                    self.add_text_page(pdf, "3. Statistical Analysis", 
                                     "Statistical report not found. Run statistical_analysis.py first.")
            
            # Section 4: Scaling Analysis
            if include_scaling:
                print("Adding scaling analysis...")
                scaling_report_path = output_dir / "scaling_analysis_results.csv"
                if scaling_report_path.exists():
                    scaling_df = pd.read_csv(scaling_report_path)
                    # Display first few rows
                    display_df = scaling_df.head(10)
                    self.add_summary_table(pdf, display_df, "4. Scaling Analysis Results")
                    
                    # Add scaling plots
                    for metric in ['peak_force_N', 'work_of_adhesion_mJ']:
                        plot_path = output_dir / f"scaling_analysis_{metric}.png"
                        if plot_path.exists():
                            self.add_plot_page(pdf, plot_path, 
                                             f"Scaling Analysis: {metric}")
                else:
                    self.add_text_page(pdf, "4. Scaling Analysis", 
                                     "Scaling analysis not found. Run advanced_metrics.py first.")
            
            # Section 5: Master Plots
            if include_plots:
                print("Adding master plots...")
                master_plots = [
                    "MASTER_area_analysis.png",
                    "MASTER_distance_analysis.png",
                    "MASTER_stiffness_analysis.png",
                    "MASTER_time_analysis.png"
                ]
                
                for plot_name in master_plots:
                    plot_path = output_dir / plot_name
                    if plot_path.exists():
                        self.add_plot_page(pdf, plot_path, f"Master Plot: {plot_name[7:-4]}")
            
            # Appendix: Metadata
            print("Adding appendix...")
            appendix_content = f"""
APPENDIX: Analysis Parameters

File Locations:
  Master CSV: {master_csv}
  Output Directory: {output_dir}

Analysis Modules Used:
  - Batch Processing: {'✓' if True else '✗'}
  - Quality Control: {'✓' if include_qc else '✗'}
  - Statistical Analysis: {'✓' if include_stats else '✗'}
  - Scaling Analysis: {'✓' if include_scaling else '✗'}

Software Version:
  Python Analysis Pipeline v1.0
  Cheng Sun Lab, Northwestern University
            """
            self.add_text_page(pdf, "Appendix", appendix_content)
        
        print("="*60)
        print(f"Report generated successfully: {pdf_path}")
        
        return pdf_path
    
    def generate_quick_summary(self, master_csv: Path, output_path: Path = None) -> str:
        """
        Generate a quick text summary (no PDF).
        
        Args:
            master_csv: Path to MASTER CSV
            output_path: Optional path to save summary
            
        Returns:
            Summary as string
        """
        df = pd.read_csv(master_csv)
        
        lines = []
        lines.append("=" * 70)
        lines.append("QUICK ANALYSIS SUMMARY")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")
        
        # Basic stats
        lines.append(f"Total Layers: {len(df)}")
        lines.append(f"Conditions: {len(df['condition_label'].unique())}")
        lines.append("")
        
        # Summary by condition
        lines.append("SUMMARY BY CONDITION")
        lines.append("-" * 70)
        
        for condition in df['condition_label'].unique():
            condition_data = df[df['condition_label'] == condition]
            
            lines.append(f"\n{condition}:")
            lines.append(f"  Layers: {len(condition_data)}")
            lines.append(f"  Peak Force: {condition_data['peak_force_N'].mean():.4f} ± {condition_data['peak_force_N'].std():.4f} N")
            lines.append(f"  Work: {condition_data['work_of_adhesion_mJ'].mean():.4f} ± {condition_data['work_of_adhesion_mJ'].std():.4f} mJ")
        
        lines.append("")
        lines.append("=" * 70)
        
        summary = "\n".join(lines)
        
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(summary)
            print(f"Summary saved to: {output_path}")
        
        return summary


if __name__ == "__main__":
    """Example usage"""
    
    # Path to master CSV
    master_csv = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V3\MASTER_steppedcone_metrics.csv")
    
    if master_csv.exists():
        output_dir = master_csv.parent
        
        # Generate quick summary
        generator = ReportGenerator()
        summary = generator.generate_quick_summary(master_csv, 
                                                   output_path=output_dir / "Quick_Summary.txt")
        print(summary)
        
        print("\n" + "="*60)
        print("To generate full PDF report, run:")
        print(f"  generator.generate_full_report(master_csv, output_dir)")
        print("="*60)
        
    else:
        print(f"Master CSV not found: {master_csv}")
        print("Please run batch processing first.")
