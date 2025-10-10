
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import medfilt
from scipy.ndimage import gaussian_filter1d

# --- Script Configuration ---
FILE_PATH = 'autolog_L80-L84.csv'

# --- Data Loading ---
df = pd.read_csv(FILE_PATH)
time = df.iloc[:, 0]
original_force = df.iloc[:, 2]

# --- Filter Implementations ---

# 1. Previous Best Hybrid Filter (Median -> Gaussian)
median_pass = medfilt(original_force, kernel_size=5)
hybrid_filtered = gaussian_filter1d(median_pass, sigma=2)

# 2. FFT (Fast Fourier Transform) Filter
#    This method transforms the signal to frequency space,
#    cuts off high frequencies, and transforms it back.

# Compute the FFT
fft_signal = np.fft.fft(original_force.values)

# Define a cutoff. We'll keep the first `cutoff_percentage` of frequencies.
# This is the main parameter to tune for this filter.
cutoff_percentage = 1.5 # Keep 1.5% of the lowest frequencies
cutoff_index = int(len(fft_signal) * (cutoff_percentage / 100))

# Zero out the high-frequency components
fft_signal_filtered = fft_signal.copy()
fft_signal_filtered[cutoff_index:-cutoff_index] = 0

# Compute the Inverse FFT to get the filtered signal
fft_filtered = np.fft.ifft(fft_signal_filtered).real


# --- Plotting ---
plt.figure(figsize=(18, 12))
plt.plot(time, original_force, label='Original Signal', alpha=0.3, color='gray')
plt.plot(time, hybrid_filtered, label=f'Best Hybrid Filter (Median->Gauss)', linestyle='--')
plt.plot(time, fft_filtered, label=f'FFT Filter ({cutoff_percentage}% cutoff)', color='red', linewidth=2)

plt.title(f'FFT Filtering vs. Hybrid Method for {FILE_PATH}')
plt.xlabel('Time (s)')
plt.ylabel('Force (N)')
plt.legend()
plt.grid(True)

output_filename = 'fft_vs_hybrid.png'
plt.savefig(output_filename)

print(f"Comparison plot saved to: {output_filename}")
print(f"The FFT filter cutoff can be adjusted with the 'cutoff_percentage' variable in the script.")
