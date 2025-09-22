"""
Clean up comparison and test files that are no longer needed
"""
import os

# Files to remove (confirmed as no longer needed)
files_to_remove = [
    "compare_calculators.py",
    "compare_time_data.py", 
    "simple_compare.py",
    "direct_prop_end_compare.py",
    "replicate_hybrid_plotter.py",
    "final_calculator_comparison.py",
    "check_boundaries.py",
    "run_normal_plotter.py",
    "run_fixed_plotter.py",
]

print("CLEANING UP UNNECESSARY FILES")
print("=" * 40)

removed_count = 0
total_size = 0

for file in files_to_remove:
    if os.path.exists(file):
        file_size = os.path.getsize(file)
        print(f"Removing: {file} ({file_size} bytes)")
        os.remove(file)
        removed_count += 1
        total_size += file_size
    else:
        print(f"Not found: {file}")

print(f"\nCLEANUP COMPLETE:")
print(f"  Removed {removed_count} files")
print(f"  Freed {total_size} bytes")
print(f"  Workspace is now clean and focused on working code")

print(f"\nREMAINING IMPORTANT FILES:")
important_files = [
    "Prince_Segmented.py",
    "adhesion_metrics_calculator.py", 
    "hybrid_adhesion_plotter.py",
    "test_adhesion_calculator_with_derivatives.py"
]

for file in important_files:
    if os.path.exists(file):
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} (missing!)")

print(f"\nBackup location: backup_corrected_system_20250921/")
