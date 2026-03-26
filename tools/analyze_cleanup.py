"""
Identify and clean up comparison and test files that are no longer needed
"""
import os
import glob

print("ANALYZING FILES FOR CLEANUP")
print("=" * 50)

# Files that are no longer needed (debugging/comparison scripts)
files_to_remove = [
    # Comparison scripts (superseded by corrected system)
    "compare_calculators.py",
    "compare_time_data.py", 
    "simple_compare.py",
    "direct_prop_end_compare.py",
    "replicate_hybrid_plotter.py",
    "final_calculator_comparison.py",
    
    # Test files that were temporary
    "check_boundaries.py",  # Appears to be empty
    
    # Plotting scripts that duplicate functionality
    "run_normal_plotter.py",  # Superseded by corrected hybrid plotter
    "run_fixed_plotter.py",   # Temporary fix script
]

# Important files to KEEP
files_to_keep = [
    "Prince_Segmented.py",  # Main printer control
    "adhesion_metrics_calculator.py",  # Corrected calculator
    "hybrid_adhesion_plotter.py",  # Corrected plotter
    "test_adhesion_calculator_with_derivatives.py",  # Useful for analysis
    "batch_process_printing_data.py",  # Batch processing
    "final_layer_visualization.py",  # Specialized visualization
    "adhesion_metrics_calculator_backup.py",  # Backup copy
]

print("FILES TO REMOVE (no longer needed):")
remove_count = 0
for file in files_to_remove:
    if os.path.exists(file):
        file_size = os.path.getsize(file)
        print(f"  📄 {file} ({file_size} bytes)")
        remove_count += 1
    else:
        print(f"  ❌ {file} (not found)")

print(f"\nFILES TO KEEP (important):")
keep_count = 0
for file in files_to_keep:
    if os.path.exists(file):
        file_size = os.path.getsize(file)
        print(f"  ✅ {file} ({file_size} bytes)")
        keep_count += 1
    else:
        print(f"  ❌ {file} (not found)")

print(f"\nSUMMARY:")
print(f"  Files to remove: {remove_count}")
print(f"  Important files: {keep_count}")
print(f"  Action: Remove {remove_count} unnecessary files")

# Ask for confirmation (in a real cleanup)
print(f"\nThese files were used for debugging the smoothing parameter issue")
print(f"and are no longer needed since the problem is resolved.")
print(f"They can be safely removed to clean up the workspace.")
