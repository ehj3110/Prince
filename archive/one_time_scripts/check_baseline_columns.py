import pandas as pd

df = pd.read_csv(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\Hybrid\automated_work_of_adhesion.csv")

print("Checking baseline-corrected columns:")
print("=" * 60)

# Check force columns
print("\nFORCE COLUMNS:")
if 'peak_force_corrected' in df.columns:
    print(f"  ✓ peak_force_corrected: {df['peak_force_corrected'].notna().sum()} values")
    print(f"    Range: [{df['peak_force_corrected'].min():.4f}, {df['peak_force_corrected'].max():.4f}] N")
else:
    print("  ✗ peak_force_corrected: NOT FOUND")

if 'Peak_Force_N' in df.columns:
    print(f"  • Peak_Force_N (raw): {df['Peak_Force_N'].notna().sum()} values")
    print(f"    Range: [{df['Peak_Force_N'].min():.4f}, {df['Peak_Force_N'].max():.4f}] N")
else:
    print("  ✗ Peak_Force_N: NOT FOUND")

# Check work of adhesion
print("\nWORK OF ADHESION COLUMNS:")
if 'Work_of_Adhesion_mJ' in df.columns:
    print(f"  ✓ Work_of_Adhesion_mJ: {df['Work_of_Adhesion_mJ'].notna().sum()} values")
    print(f"    Range: [{df['Work_of_Adhesion_mJ'].min():.4f}, {df['Work_of_Adhesion_mJ'].max():.4f}] mJ")
else:
    print("  ✗ Work_of_Adhesion_mJ: NOT FOUND")

if 'work_of_adhesion_mJ' in df.columns:
    print(f"  • work_of_adhesion_mJ (lowercase): {df['work_of_adhesion_mJ'].notna().sum()} values")
else:
    print("  ✗ work_of_adhesion_mJ: NOT FOUND")

# Check distance
print("\nDISTANCE COLUMNS:")
if 'Total_Peel_Distance_mm' in df.columns:
    print(f"  ✓ Total_Peel_Distance_mm: {df['Total_Peel_Distance_mm'].notna().sum()} values")
    print(f"    Range: [{df['Total_Peel_Distance_mm'].min():.4f}, {df['Total_Peel_Distance_mm'].max():.4f}] mm")
    print(f"    All positive? {(df['Total_Peel_Distance_mm'] >= 0).all()}")
else:
    print("  ✗ Total_Peel_Distance_mm: NOT FOUND")

print("\n" + "=" * 60)
print("NOTES:")
print("  - peak_force_corrected = baseline-corrected peak force ✓")
print("  - Work_of_Adhesion_mJ = work_of_adhesion_corrected_mJ (renamed by batch processor) ✓")
print("  - Total_Peel_Distance_mm = already baseline-corrected (starts from pre-initiation) ✓")
