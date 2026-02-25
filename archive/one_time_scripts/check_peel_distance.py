"""Check for false peaks by looking at total peel distance"""
import pandas as pd

master = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\MASTER_all_metrics.csv')

print("="*80)
print("PEEL DISTANCE CHECK FOR ALL CONDITIONS")
print("="*80)

for cond in sorted(master['Condition'].unique()):
    cond_df = master[master['Condition'] == cond]
    
    print(f"\n{cond}:")
    print(f"  Count: {len(cond_df)}")
    print(f"  Min: {cond_df['Total_Peel_Distance_mm'].min():.3f} mm")
    print(f"  Max: {cond_df['Total_Peel_Distance_mm'].max():.3f} mm")
    print(f"  Mean: {cond_df['Total_Peel_Distance_mm'].mean():.3f} mm")
    
    low = cond_df[cond_df['Total_Peel_Distance_mm'] < 1.0]
    if len(low) > 0:
        print(f"  WARNING: {len(low)} rows with peel distance < 1.0mm!")
    else:
        print(f"  OK: No false peaks detected")
