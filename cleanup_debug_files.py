"""
Clean up debug and test files created during the smoothing parameter debugging session
"""
import os
import glob

# Files to remove (debug scripts created during troubleshooting)
debug_files_to_remove = [
    "debug_plot_conversion.py",
    "debug_conversion_issue.py", 
    "test_fixed_calculator.py",
    "test_hybrid_plotter.py",
    "test_plot_visibility.py",
    "test_motion_end_idx.py",
    "test_extra_point.py",
    "test_data_length.py", 
    "test_calc_values.py",
    "run_corrected_plotter.py",
    "diagnose_time_conversion.py"
]

# Test plots to remove (generated during debugging)
test_plots_to_remove = [
    "test_layer_198_current_method_derivatives.png",
    "test_layer_199_current_method_derivatives.png", 
    "test_layer_200_current_method_derivatives.png",
    "normal_calculator_L198_L200_analysis.png",
    "fixed_calculator_L198_L200_analysis.png",
    "diagnostic_L198-L200_derivatives_SMOOTHED_CORRECTED.png"
]

# Keep the final corrected plot
keep_plots = [
    "corrected_L198_L200_analysis.png"  # This is the final working plot
]

print("CLEANING UP DEBUG FILES...")
print("="*50)

removed_count = 0

# Remove debug scripts
for file in debug_files_to_remove:
    if os.path.exists(file):
        print(f"Removing debug script: {file}")
        os.remove(file)
        removed_count += 1
    else:
        print(f"File not found: {file}")

# Remove test plots  
for file in test_plots_to_remove:
    if os.path.exists(file):
        print(f"Removing test plot: {file}")
        os.remove(file)
        removed_count += 1
    else:
        print(f"Plot not found: {file}")

print(f"\nCleaned up {removed_count} files")

# Show what we're keeping
print(f"\nKEEPING FINAL RESULTS:")
for file in keep_plots:
    if os.path.exists(file):
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} (not found)")

print(f"\nBackup location: backup_corrected_system_20250921/")
print("Cleanup complete!")
