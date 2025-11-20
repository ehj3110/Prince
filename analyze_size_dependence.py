"""
Analyze if 200um PDMS scaling changes with part size
"""

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from pathlib import Path

# Load the data
script_dir = Path(__file__).parent
df = pd.read_csv(script_dir / 'post-processing/scaling_tests_results/MASTER_scaling_tests_all_data.csv')

# Filter for 200um PDMS Cone data only
cone_200um = df[(df['condition_label'] == '200um PDMS TankV19') & (df['model'] == 'Cone')].copy()
cone_200um = cone_200um.sort_values('area_mm2')

print('='*80)
print('200um PDMS TankV19 Cone Data Analysis')
print('='*80)
print(f'\nTotal measurements: {len(cone_200um)}')
print(f'Area range: {cone_200um["area_mm2"].min():.2f} - {cone_200um["area_mm2"].max():.2f} mm²')
print(f'Radius range: {cone_200um["part_radius_mm"].min():.2f} - {cone_200um["part_radius_mm"].max():.2f} mm')

# Split into small, medium, large
small = cone_200um[cone_200um['area_mm2'] < 2.5]
medium = cone_200um[(cone_200um['area_mm2'] >= 2.5) & (cone_200um['area_mm2'] < 5.0)]
large = cone_200um[cone_200um['area_mm2'] >= 5.0]

print(f'\nSmall parts (<2.5 mm²): {len(small)} measurements')
print(f'Medium parts (2.5-5.0 mm²): {len(medium)} measurements')
print(f'Large parts (>5.0 mm²): {len(large)} measurements')

# Fit power law for each subset
def fit_power_law(data):
    if len(data) < 3:
        return None
    log_x = np.log(data['part_radius_mm'])
    log_y = np.log(data['peak_force_N'])
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
    return {'n': slope, 'stderr': std_err, 'R2': r_value**2, 'count': len(data)}

print('\n' + '='*80)
print('Size-Dependent Scaling Analysis')
print('='*80)

for name, subset in [('Small', small), ('Medium', medium), ('Large', large), ('All', cone_200um)]:
    result = fit_power_law(subset)
    if result:
        print(f'\n{name} parts (n={result["count"]}):')
        print(f'  Exponent: n = {result["n"]:.3f} ± {result["stderr"]:.3f}')
        print(f'  R² = {result["R2"]:.3f}')

# Check for trend in residuals vs size
log_x = np.log(cone_200um['part_radius_mm'])
log_y = np.log(cone_200um['peak_force_N'])
slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
predicted_log_y = slope * log_x + intercept
residuals = log_y - predicted_log_y

# Correlate residuals with size
corr, p = stats.pearsonr(cone_200um['area_mm2'], residuals)

print('\n' + '='*80)
print('Residual Analysis (Testing for Size-Dependent Trend)')
print('='*80)
print(f'Correlation between residuals and area: r = {corr:.3f}, p = {p:.4f}')
if abs(corr) > 0.3 and p < 0.05:
    print('⚠️  Significant trend detected - scaling may change with size!')
elif p < 0.05:
    print('⚠️  Weak but statistically significant trend')
else:
    print('✓ No significant size-dependent trend')

# Create a visualization
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Left: Data with fits by size range
ax = axes[0]
colors = {'Small': 'blue', 'Medium': 'green', 'Large': 'red'}
for name, subset, color in [('Small', small, 'blue'), ('Medium', medium, 'green'), ('Large', large, 'red')]:
    if len(subset) > 0:
        result = fit_power_law(subset)
        ax.scatter(subset['part_radius_mm'], subset['peak_force_N'], 
                  color=color, alpha=0.6, s=50, label=f'{name} (n={result["n"]:.2f})')
        
        # Plot fit line
        if result:
            x_fit = np.linspace(subset['part_radius_mm'].min(), subset['part_radius_mm'].max(), 100)
            k = np.exp(intercept)  # This is approximate, would need per-group fits for exact
            # For now just show the points
            
ax.set_xlabel('Part Radius (mm)', fontsize=12)
ax.set_ylabel('Peak Force (N)', fontsize=12)
ax.set_title('200um PDMS: Force vs Radius by Size Range', fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)

# Right: Residuals vs size
ax = axes[1]
ax.scatter(cone_200um['area_mm2'], residuals, alpha=0.6, s=50)
ax.axhline(0, color='red', linestyle='--', linewidth=2, label='Perfect fit')
ax.set_xlabel('Part Area (mm²)', fontsize=12)
ax.set_ylabel('Log Residuals', fontsize=12)
ax.set_title(f'Residuals vs Size (r={corr:.3f}, p={p:.4f})', fontsize=14)
ax.grid(True, alpha=0.3)
ax.legend()

plt.tight_layout()
output_path = script_dir / 'post-processing/scaling_tests_results/200um_size_dependence_analysis.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f'\n✓ Plot saved: {output_path}')
