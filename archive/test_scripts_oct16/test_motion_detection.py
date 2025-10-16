import pandas as pd
import numpy as np

# Load data
df = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\2p5PEO_1mm_SteppedCone_BPAGDA_1000\autolog_L100-L105.csv')
pos = df['Position (mm)'].to_numpy()

window_size = 10
pos_threshold = 0.02

print("Testing motion detection:")
print(f"Window size: {window_size}")
print(f"Position threshold: {pos_threshold} mm\n")

# Test sequential windows
last_avg = np.mean(pos[10:10+window_size])
print(f"Starting avg (i=10): {last_avg:.4f} mm\n")

for i in range(20, 900, 10):
    curr_avg = np.mean(pos[i:i+window_size])
    diff = curr_avg - last_avg
    
    if abs(diff) >= pos_threshold:
        direction = "DOWN" if diff < 0 else "UP"
        print(f"i={i:4d}: avg={curr_avg:.4f}, diff={diff:+.4f} -> {direction}")
    
    last_avg = curr_avg
    
    if i > 900:
        break
