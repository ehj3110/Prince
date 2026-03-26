"""
Update PeakForceLogger to Use Corrected Calculator
=================================================

This script modifies the support_modules/PeakForceLogger.py to optionally
use our corrected adhesion_metrics_calculator during printing, giving us
the enhanced metrics with accurate propagation end times.

Changes:
1. Add option to use AdhesionMetricsCalculator instead of TwoStepBaselineAnalyzer
2. Use corrected light smoothing settings
3. Maintain backward compatibility with existing analyzers

Date: September 21, 2025
"""

import os
import shutil

def upgrade_peak_force_logger():
    """
    Upgrade the PeakForceLogger to use corrected adhesion_metrics_calculator.
    """
    print("UPGRADING PEAKFORCELOGGER TO USE CORRECTED CALCULATOR")
    print("=" * 60)
    
    pfl_path = "support_modules/PeakForceLogger.py"
    backup_path = "support_modules/PeakForceLogger_original_backup.py"
    
    # Create backup
    if not os.path.exists(backup_path):
        shutil.copy(pfl_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
    else:
        print(f"✅ Backup already exists: {backup_path}")
    
    print(f"\\n📝 Manual upgrade instructions for {pfl_path}:")
    print("-" * 40)
    
    print("\\n1. Add import for corrected calculator at top:")
    print("   from adhesion_metrics_calculator import AdhesionMetricsCalculator")
    
    print("\\n2. Add to __init__ method after line 23:")
    print("""
    # Option to use corrected adhesion_metrics_calculator
    if enhanced_analysis and analyzer_type == "corrected_calculator":
        self.adhesion_analyzer = None  # Will use direct calculator
        self.corrected_calculator = AdhesionMetricsCalculator(
            smoothing_window=3,        # Light smoothing
            smoothing_polyorder=1,     # Linear polynomial  
            baseline_threshold_factor=0.002,
            min_peak_height=0.01,
            min_peak_distance=50
        )
    else:
        self.corrected_calculator = None
    """)
    
    print("\\n3. Add method after _write_enhanced_csv_entry:")
    print("""
def _analyze_with_corrected_calculator(self, timestamps, positions, forces):
    \"\"\"
    Analyze data using corrected adhesion_metrics_calculator with light smoothing.
    \"\"\"
    if not self.corrected_calculator:
        return None
        
    # Convert to arrays
    times = np.array(timestamps)
    pos = np.array(positions) 
    force_data = np.array(forces)
    
    # Reset time to start at 0 (like hybrid plotter does)
    elapsed_times = times - times[0]
    
    try:
        # Use corrected calculator with light smoothing
        metrics = self.corrected_calculator.calculate_from_arrays(
            elapsed_times, pos, force_data, 
            layer_number=self.current_layer_number
        )
        
        # Convert to format expected by PFL logging
        return {
            'peak_force_N': metrics['peak_force'],
            'work_of_adhesion_mJ': metrics['work_of_adhesion_corrected_mJ'],
            'propagation_end_time_s': metrics['propagation_end_time'],
            'baseline_force_N': metrics['baseline_force'],
            'peak_force_time_s': metrics['peak_force_time']
        }
    except Exception as e:
        print(f"PFL Corrected Calculator Error: {e}")
        return None
    """)
    
    print("\\n4. Modify stop_monitoring_and_log_peak method around line 145:")
    print("   Add after 'if self.enhanced_analysis and len(self._data_buffer) >= 2:'")
    print("""
    # Try corrected calculator first
    if hasattr(self, 'corrected_calculator') and self.corrected_calculator:
        enhanced_results = self._analyze_with_corrected_calculator(timestamps, positions, forces)
        if enhanced_results:
            peak_peel_force = enhanced_results['peak_force_N']
            work_of_adhesion_mJ = enhanced_results['work_of_adhesion_mJ']
            
            # Create CSV entry for corrected calculator results
            log_entry_made = self._write_corrected_csv_entry(enhanced_results)
            print(f"PFL Corrected: Layer {self.current_layer_number} - Peak: {peak_peel_force:.4f}N, Work: {work_of_adhesion_mJ:.4f}mJ, PropEnd: {enhanced_results['propagation_end_time_s']:.3f}s")
            
        else:
            # Fallback to existing analyzers
    """)
    
    print("\\n5. Add CSV writing method:")
    print("""
def _write_corrected_csv_entry(self, results):
    \"\"\"Write results from corrected calculator to CSV.\"\"\"
    try:
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        with open(self.output_csv_filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            if self.is_manual_log:
                writer.writerow([
                    timestamp_str,
                    self.current_layer_number,
                    f"{results['peak_force_N']:.4f}",
                    f"{results['work_of_adhesion_mJ']:.4f}",
                    f"{results['propagation_end_time_s']:.4f}",
                    f"{results['baseline_force_N']:.4f}"
                ])
            else:
                writer.writerow([
                    self.current_layer_number,
                    f"{results['peak_force_N']:.4f}", 
                    f"{results['work_of_adhesion_mJ']:.4f}",
                    f"{results['propagation_end_time_s']:.4f}",
                    f"{results['baseline_force_N']:.4f}"
                ])
        return True
    except Exception as e:
        print(f"Error writing corrected results: {e}")
        return False
    """)
    
    print("\\n6. To enable corrected calculator during printing:")
    print("   Change analyzer_type from 'two_step_baseline' to 'corrected_calculator'")
    print("   in Prince_Segmented.py where PeakForceLogger is initialized")
    
    print("\\n" + "=" * 60)
    print("UPGRADE SUMMARY:")
    print("- ✅ Backup created")
    print("- 📝 Manual modifications required (see above)")  
    print("- 🎯 Result: PeakForceLogger will use corrected light smoothing")
    print("- 🎯 Result: Propagation end times will be accurate during printing")
    print("=" * 60)


if __name__ == "__main__":
    upgrade_peak_force_logger()
