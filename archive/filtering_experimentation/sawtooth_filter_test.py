import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, savgol_filter, medfilt
from scipy.ndimage import gaussian_filter1d
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

# Helper function to apply a filter chain based on text descriptions
def apply_filter_chain(data, chain_description, params_str):
    chain_parts = chain_description.split(' -> ')
    median_part = chain_parts[0]
    second_part = chain_parts[1]
    median_kernel = int(median_part.split('=')[1].replace(')',''))
    processed_data = medfilt(data, kernel_size=median_kernel)
    plot_params = dict(item.split('=') for item in params_str.split(', '))
    if second_part == 'Butterworth':
        b, a = butter(int(plot_params['N']), float(plot_params['Wn']), btype='low')
        final_data = filtfilt(b, a, processed_data)
    elif second_part == 'Gaussian':
        final_data = gaussian_filter1d(processed_data, sigma=int(plot_params['sigma']))
    elif second_part == 'Savitzky-Golay':
        final_data = savgol_filter(processed_data, int(plot_params['window']), int(plot_params['order']))
    else:
        raise ValueError(f"Unknown filter type: {second_part}")
    return final_data

def run_analysis_on_file(file_path, lambda_val):
    print(f"\n{'='*20} ANALYSIS FOR {file_path} (Lambda = {lambda_val}) {'='*20}")
    
    # --- Script Configuration ---
    param_grid = {
        'butterworth': {'N': [3], 'Wn': [0.05, 0.1, 0.15, 0.2, 0.25]},
        'gaussian': {'sigma': [1, 2, 3, 4, 5]},
        'savitzky-golay': {'window_length': [5, 9, 13, 17, 21], 'polyorder': [2]}
    }
    median_kernels = [5, 9]

    # --- Data Loading ---
    df = pd.read_csv(file_path)
    time = df.iloc[:, 0]
    original_force = df.iloc[:, 2]

    # --- Hybrid Grid Search ---
    results = []
    for kernel_size in median_kernels:
        median_filtered_force = medfilt(original_force, kernel_size=kernel_size)
        for N in param_grid['butterworth']['N']:
            for Wn in param_grid['butterworth']['Wn']:
                final_filtered = filtfilt(butter(N, Wn, btype='low')[0], butter(N, Wn, btype='low')[1], median_filtered_force)
                _, _, score = calculate_scores(original_force, final_filtered, lambda_val)
                results.append({'filter': f'Median(k={kernel_size}) -> Butterworth', 'params': f'N={N}, Wn={Wn}', 'score': score})
        for sigma in param_grid['gaussian']['sigma']:
            final_filtered = gaussian_filter1d(median_filtered_force, sigma=sigma)
            _, _, score = calculate_scores(original_force, final_filtered, lambda_val)
            results.append({'filter': f'Median(k={kernel_size}) -> Gaussian', 'params': f'sigma={sigma}', 'score': score})
        for window in param_grid['savitzky-golay']['window_length']:
            for order in param_grid['savitzky-golay']['polyorder']:
                if window > order:
                    final_filtered = savgol_filter(median_filtered_force, window, order)
                    _, _, score = calculate_scores(original_force, final_filtered, lambda_val)
                    results.append({'filter': f'Median(k={kernel_size}) -> Savitzky-Golay', 'params': f'window={window}, order={order}', 'score': score})

    # --- Analyze Results ---
    results_df = pd.DataFrame(results).sort_values(by='score').reset_index(drop=True)
    
    # Save and print the full table
    table_filename = f"results_{os.path.splitext(file_path)[0]}_lambda{int(lambda_val)}.txt"
    results_df.to_csv(table_filename, sep='\t', index=False)
    print(f"Full results table saved to: {table_filename}")
    
    # Find and print winners
    overall_winner = results_df.iloc[0]
    print("\n--- WINNER FOR THIS FILE ---")
    print("Overall Winner:", overall_winner.to_dict(), sep='\n')

    # --- Apply Best Filters for Plotting ---
    best_butter_chain = results_df[results_df['filter'].str.contains('Butterworth')].iloc[0]
    best_gauss_chain = results_df[results_df['filter'].str.contains('Gaussian')].iloc[0]
    best_sg_chain = results_df[results_df['filter'].str.contains('Savitzky-Golay')].iloc[0]
    best_butter_data = apply_filter_chain(original_force, best_butter_chain['filter'], best_butter_chain['params'])
    best_gauss_data = apply_filter_chain(original_force, best_gauss_chain['filter'], best_gauss_chain['params'])
    best_sg_data = apply_filter_chain(original_force, best_sg_chain['filter'], best_sg_chain['params'])

    # --- Final Summary Plot ---
    plt.figure(figsize=(18, 12))
    plt.plot(time, original_force, label='Original Signal', alpha=0.3, color='gray')
    plt.plot(time, best_butter_data, label=f"Best Butterworth: {best_butter_chain['filter']} ({best_butter_chain['params']})\nScore: {best_butter_chain['score']:.4f}")
    plt.plot(time, best_gauss_data, label=f"Best Gaussian: {best_gauss_chain['filter']} ({best_gauss_chain['params']})\nScore: {best_gauss_chain['score']:.4f}")
    plt.plot(time, best_sg_data, label=f"Best Savitzky-Golay: {best_sg_chain['filter']} ({best_sg_chain['params']})\nScore: {best_sg_chain['score']:.4f}")
    
    plot_filename = f"plot_summary_{os.path.splitext(file_path)[0]}_lambda{int(lambda_val)}.png"
    plt.title(f'Comparison of Best Hybrid Filter Chains for {file_path} (Lambda = {lambda_val})')
    plt.xlabel('Time (s)')
    plt.ylabel('Force (N)')
    plt.legend()
    plt.grid(True)
    plt.savefig(plot_filename)
    print(f"Summary plot saved to: {plot_filename}")

# --- Main Execution ---
if __name__ == "__main__":
    files_to_analyze = ['autolog_L80-L84.csv', 'autolog_L345-L349.csv']
    lambdas_to_test = [15.0, 30.0, 50.0]
    for l in lambdas_to_test:
        for f in files_to_analyze:
            run_analysis_on_file(f, l)