"""
Test: Find where position ACTUALLY stops moving (not just where large motion ends)
"""
import pandas as pd
import numpy as np

df = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\autolog_L430-L435.csv')

position = df['Position (mm)'].values
time = df['Elapsed Time (s)'].values

def find_motion_end(start_idx, direction, position_data, min_stable_points=5):
    """
    Find where motion actually STOPS (position stabilizes).
    
    Args:
        start_idx: Where to start searching
        direction: -1 for downward (LIFT), +1 for upward (RETRACT)
        position_data: Position array
        min_stable_points: How many consecutive stable points needed
        
    Returns:
        Index where motion ends (position stabilizes)
    """
    stability_threshold = 0.02  # Position must vary less than 0.02mm
    
    for i in range(start_idx, min(start_idx + 600, len(position_data) - min_stable_points)):
        # Check if next N points are stable
        window = position_data[i:i+min_stable_points]
        pos_range = np.max(window) - np.min(window)
        
        if pos_range < stability_threshold:
            # Found stable region
            return i
    
    # If no stable region found, return search limit
    return min(start_idx + 600, len(position_data) - 1)


print("="*60)
print("Testing motion end detection for Layer 2 (431)")
print("="*60)

# Current algorithm says: LIFT: idx 430-840
current_start = 430
current_end = 840

print(f"\nCurrent detection: {current_start} to {current_end}")
print(f"  Start: {time[current_start]:.3f}s at {position[current_start]:.3f}mm")
print(f"  End:   {time[current_end]:.3f}s at {position[current_end]:.3f}mm")

# Find actual end
actual_end = find_motion_end(current_end, -1, position, min_stable_points=3)

print(f"\nActual motion end: {actual_end}")
print(f"  Time: {time[actual_end]:.3f}s at {position[actual_end]:.3f}mm")

print(f"\nDifference: {actual_end - current_end} indices ({time[actual_end] - time[current_end]:.3f}s)")

print(f"\n--- Position trace from current end to actual end ---")
for i in range(current_end, min(actual_end + 5, len(position))):
    print(f"  Index {i}: {time[i]:.3f}s, Pos={position[i]:.3f}mm")
