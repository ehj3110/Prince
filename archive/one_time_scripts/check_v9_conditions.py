import pandas as pd
from pathlib import Path

v9_base = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9")

# Get all subfolders
subfolders = [f for f in v9_base.iterdir() if f.is_dir()]

print("V9 Experimental Conditions:")
print("=" * 80)

for folder in sorted(subfolders):
    print(f"\nFolder: {folder.name}")
    print("-" * 80)
    
    # Check for experimental_conditions.csv
    exp_conditions = folder / "experimental_conditions.csv"
    if exp_conditions.exists():
        df = pd.read_csv(exp_conditions)
        print("\nExperimental Conditions:")
        print(df.to_string(index=False))
    else:
        print("  No experimental_conditions.csv found")
    
    print()
