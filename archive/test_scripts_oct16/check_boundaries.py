import pandas as pd
import numpy as np

df = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\autolog_L430-L435.csv')

print("="*60)
print("Layer 2 (431) - Detected Boundaries")
print("="*60)

# Detected boundaries from our algorithm
start_idx = 430
end_idx = 840

print(f"\nDetected lifting phase: Index {start_idx} to {end_idx}")
print(f"Start: Time={df.iloc[start_idx]['Elapsed Time (s)']:.3f}s, Pos={df.iloc[start_idx]['Position (mm)']:.3f}mm")
print(f"End:   Time={df.iloc[end_idx]['Elapsed Time (s)']:.3f}s, Pos={df.iloc[end_idx]['Position (mm)']:.3f}mm")

# Find peak
peak_idx = start_idx + np.argmax(df.iloc[start_idx:end_idx+1]['Force (N)'].values)
print(f"\nPeak: Index {peak_idx}, Time={df.iloc[peak_idx]['Elapsed Time (s)']:.3f}s, Force={df.iloc[peak_idx]['Force (N)']:.4f}N")

# Check if there's more data after index 840
print(f"\n--- Checking data after detected end (index {end_idx}) ---")
for i in range(end_idx, min(end_idx+20, len(df))):
    print(f"Index {i}: Time={df.iloc[i]['Elapsed Time (s)']:.3f}s, Pos={df.iloc[i]['Position (mm)']:.3f}mm, Force={df.iloc[i]['Force (N)']:.4f}N")

print(f"\n--- Around your suspected end time (14.357s) ---")
time_mask = (df['Elapsed Time (s)'] >= 14.3) & (df['Elapsed Time (s)'] <= 14.4)
matches = df[time_mask]
for idx, row in matches.iterrows():
    print(f"Index {idx}: Time={row['Elapsed Time (s)']:.3f}s, Pos={row['Position (mm)']:.3f}mm, Force={row['Force (N)']:.4f}N")
