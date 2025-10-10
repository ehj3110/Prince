
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, medfilt
import numpy as np
import os

# Function to calculate fidelity, roughness, and a combined score
def calculate_scores(y_true, y_pred, lambda_val=1.0):
    if np.all(np.isnan(y_pred)):
        return float('inf'), float('inf'), float('inf')
    valid_indices = ~np.isnan(y_pred)
    ssr = np.sum((y_true[valid_indices] - y_pred[valid_indices])**2)
    roughness = np.sum(np.diff(y_pred[valid_indices], 2)**2)
    combined_score = ssr + lambda_val * roughness
    return ssr, roughness, combined_score

# --- Default Configuration ---
# You can change these defaults as needed
DEFAULT_FILE = 'autolog_L80-L84.csv'
LAMBDA_VALUE = 1.0
MEDIAN_KERNEL = 5
SG_WINDOW = 9
SG_ORDER = 2

# --- Data Loading ---
if not os.path.exists(DEFAULT_FILE):
    print(f"Error: Default file '{DEFAULT_FILE}' not found.")
else:
    df = pd.read_csv(DEFAULT_FILE)
    time = df.iloc[:, 0]
    original_force = df.iloc[:, 2]

    # --- Apply the Default Filter Chain ---
    # 1. Median filter pass for outlier rejection
    median_pass = medfilt(original_force, kernel_size=MEDIAN_KERNEL)
    
    # 2. Savitzky-Golay pass for smoothing
    final_filtered = savgol_filter(median_pass, SG_WINDOW, SG_ORDER)

    # --- Calculate and Print Scores ---
    ssr, roughness, score = calculate_scores(original_force, final_filtered, LAMBDA_VALUE)
    
    print("--- Default Filter Analysis ---")
    print(f"File: {DEFAULT_FILE}")
    print(f"Filter: Median(k={MEDIAN_KERNEL}) -> Savitzky-Golay(w={SG_WINDOW}, o={SG_ORDER})")
    print(f"Lambda: {LAMBDA_VALUE}")
    print("\n--- SCORES ---")
    print(f"  - Fidelity (SSR): {ssr:.6f}")
    print(f"  - Roughness:      {roughness:.6f}")
    print(f"  - Combined Score: {score:.6f}")

    # --- Plotting ---
    plt.figure(figsize=(18, 12))
    plt.plot(time, original_force, label='Original Signal', alpha=0.4, color='gray')
    plt.plot(time, final_filtered, label=f'Filtered Signal\nScore: {score:.4f}', color='red', linewidth=2)
    
    output_filename = f"filtered_result_{os.path.splitext(DEFAULT_FILE)[0]}.png"
    plt.title(f'Default Filter Applied to {DEFAULT_FILE}')
    plt.xlabel('Time (s)')
    plt.ylabel('Force (N)')
    plt.legend()
    plt.grid(True)
    plt.savefig(output_filename)
    
    print(f"\nPlot saved to {output_filename}")
