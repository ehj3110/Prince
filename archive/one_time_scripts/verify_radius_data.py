import pandas as pd

df = pd.read_csv(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\MASTER_final_combined.csv")

print("\n" + "="*80)
print("VERIFICATION: All Conditions Have Radius Data")
print("="*80)

print("\nCondition counts:")
print(df['condition'].value_counts())

print("\n\nRadius summary by condition:")
for cond in sorted(df['condition'].unique()):
    cond_df = df[df['condition']==cond]
    radius_data = cond_df['radius_mm'].dropna()
    
    if len(radius_data) > 0:
        print(f"\n{cond}:")
        print(f"  Radius range: [{radius_data.min():.2f}, {radius_data.max():.2f}] mm")
        print(f"  Unique radius values: {radius_data.nunique()}")
        print(f"  Valid radius entries: {len(radius_data)}/{len(cond_df)}")
    else:
        print(f"\n{cond}: NO RADIUS DATA")

print("\n" + "="*80)
