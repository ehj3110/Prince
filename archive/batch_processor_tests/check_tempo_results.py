import pandas as pd
import numpy as np

# Read the master CSV
df = pd.read_csv('C:/Users/ehunt/OneDrive - Northwestern University/Lab Work/Nissan/Adhesion Tests/SteppedConeTests/V9/data/MASTER_all_metrics.csv')

print("="*60)
print("TEMPO Data Summary (After 200ms Skip Applied)")
print("="*60)

# Filter TEMPO data
tempo = df[df['condition_label'].str.contains('TEMPO')]

print(f"\nTotal TEMPO layers: {len(tempo)}")
print(f"\nConditions:")

for cond in sorted(tempo['condition_label'].unique()):
    data = tempo[tempo['condition_label']==cond]
    print(f"\n{cond}:")
    print(f"  Layers: {len(data)}")
    print(f"  Peak Force: {data['peak_force_N'].mean():.4f} ± {data['peak_force_N'].std():.4f} N")
    print(f"  Work: {data['work_of_adhesion_mJ'].mean():.4f} ± {data['work_of_adhesion_mJ'].std():.4f} mJ")
    
    # Show range for largest areas
    large_areas = data[data['area_mm2'] > 70].sort_values('area_mm2', ascending=False)
    if len(large_areas) > 0:
        print(f"  Largest area peak forces:")
        for _, row in large_areas.head(5).iterrows():
            print(f"    L{int(row['layer_number'])}: {row['area_mm2']:.1f} mm² → {row['peak_force_N']:.4f} N")

print("\n" + "="*60)
print("Comparison")
print("="*60)

upw_data = tempo[tempo['condition_label'] == 'TEMPO_200um_V23Ext_UPW_1000']
water_data = tempo[tempo['condition_label'] == 'TEMPO_200um_V23Ext_Water_1000']

if len(upw_data) > 0 and len(water_data) > 0:
    upw_force = upw_data['peak_force_N'].mean()
    water_force = water_data['peak_force_N'].mean()
    diff_pct = ((upw_force - water_force) / water_force) * 100
    
    print(f"\nUPW vs Water:")
    print(f"  UPW Peak Force:   {upw_force:.4f} N")
    print(f"  Water Peak Force: {water_force:.4f} N")
    print(f"  Difference: +{diff_pct:.1f}% (UPW is stiffer)")
