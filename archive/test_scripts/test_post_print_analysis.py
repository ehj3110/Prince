"""
Test script for post-print analysis with new layer boundary detection
"""

import pandas as pd
from pathlib import Path
from post_print_analyzer import PostPrintAnalyzer

def test_single_file(file_path):
    analyzer = PostPrintAnalyzer()
    
    try:
        df = pd.read_csv(file_path)
        if not all(col in df.columns for col in ['Time', 'Force', 'Position']):
            print(f"Error: CSV file must contain Time, Force, and Position columns")
            return
                
        print(f"Analyzing file: {file_path}")
        result = analyzer._analyze_data(df, file_path)
        print(f"Analysis complete - {len(result['layers'])} layers processed")
        print(f"Plot saved to: {result['plot_path']}")
            
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return

if __name__ == "__main__":
    test_file = Path("post-processing/autolog_L48-L50.csv")
    test_single_file(test_file)