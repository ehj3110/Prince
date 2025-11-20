"""
Analyze if 200um PDMS pyramid scaling changes with part size
"""

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from pathlib import Path

# Load the data
script_dir = Path(__file__).parent
df = pd.read_csv(script_dir / 'post-processing/scaling_tests_results/MASTER_scaling_tests_all_data.csv')

# Filter for 200um PDMS Pyramid data only
pyramid_200um = df[(df['condition_label'] == '200um PDMS TankV20') & (df['model'] == 'Pyramid')].copy()
pyramid_200um = pyramid_200um.sort_values('area_mm2')

print('='*80)
print('200um PDMS TankV20 Pyramid Data Analysis')
print('='*80)
print(f'\nTotal measurements: {len(pyramid_200um)}')
print(f'Area range: {pyramid_200um["area_mm2"].min():.2f} - {pyramid_200um["area_mm2"].max():.2f} mm²')
print(f'Radius range: {pyramid_200um["part_radius_mm"].min():.2f} - {pyramid_200um["part_radius_mm"].max():.2f} mm')
print(f'Force range: {pyramid_200um["peak_force_N"].min():.3f} - {pyramid_200um["peak_force_N"].max():.3f} N')

# Split into small, medium, large (adjusted for pyramid range)
tercile_1 = pyramid_200um["area_mm2"].quantile(0.33)
tercile_2 = pyramid_200um["area_mm2"].quantile(0.67)

small = pyramid_200um[pyramid_200um['area_mm2'] < tercile_1]
medium = pyramid_200um[(pyramid_200um['area_mm2'] >= tercile_1) & (pyramid_200um['area_mm2'] < tercile_2)]
large = pyramid_200um[pyramid_200um['area_mm2'] >= tercile_2]

print(f'\nSmall parts (<{tercile_1:.1f} mm²): {len(small)} measurements')
print(f'Medium parts ({tercile_1:.1f}-{tercile_2:.1f} mm²): {len(medium)} measurements')
print(f'Large parts (>{tercile_2:.1f} mm²): {len(large)} measurements')

# Fit power law for each subset
def fit_power_law(data):
    if len(data) < 3:
        return None
    log_x = np.log(data['part_radius_mm'])
    log_y = np.log(data['peak_force_N'])
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
    return {'n': slope, 'stderr': std_err, 'R2': r_value**2, 'count': len(data)}

print('\n' + '='*80)
print('Size-Dependent Scaling Analysis (Force vs Radius)')
print('='*80)

for name, subset in [('Small', small), ('Medium', medium), ('Large', large), ('All', pyramid_200um)]:
    result = fit_power_law(subset)
    if result:
        print(f'\n{name} parts (n={result["count"]}):')
        print(f'  Exponent: n = {result["n"]:.3f} ± {result["stderr"]:.3f}')
        print(f'  R² = {result["R2"]:.3f}')

# Check for trend in residuals vs size
log_x = np.log(pyramid_200um['part_radius_mm'])
log_y = np.log(pyramid_200um['peak_force_N'])
slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
predicted_log_y = slope * log_x + intercept
residuals = log_y - predicted_log_y

# Correlate residuals with size
corr, p = stats.pearsonr(pyramid_200um['area_mm2'], residuals)

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

# Also check Force vs Area scaling
print('\n' + '='*80)
print('Force vs Area Scaling Analysis')
print('='*80)

def fit_power_law_area(data):
    if len(data) < 3:
        return None
    log_x = np.log(data['area_mm2'])
    log_y = np.log(data['peak_force_N'])
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
    return {'n': slope, 'stderr': std_err, 'R2': r_value**2}

for name, subset in [('Small', small), ('Medium', medium), ('Large', large), ('All', pyramid_200um)]:
    result = fit_power_law_area(subset)
    if result:
        print(f'\n{name}: n = {result["n"]:.3f} ± {result["stderr"]:.3f}, R² = {result["R2"]:.3f}')

# Create a visualization
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# Top-left: Force vs Radius with size groups
ax = axes[0, 0]
colors_map = {
    'Small': 'blue',
    'Medium': 'green', 
    'Large': 'red'
}
for name, subset, color in [('Small', small, 'blue'), ('Medium', medium, 'green'), ('Large', large, 'red')]:
    if len(subset) > 0:
        result = fit_power_law(subset)
        ax.scatter(subset['part_radius_mm'], subset['peak_force_N'], 
                  color=color, alpha=0.6, s=50, label=f'{name} (n={result["n"]:.2f})')

# Add overall fit line
x_fit = np.linspace(pyramid_200um['part_radius_mm'].min(), pyramid_200um['part_radius_mm'].max(), 100)
overall_result = fit_power_law(pyramid_200um)
k = np.exp(intercept)
y_fit = k * x_fit ** overall_result['n']
ax.plot(x_fit, y_fit, 'k--', linewidth=2, label=f'Overall fit (n={overall_result["n"]:.2f})')

ax.set_xlabel('Part Radius (mm)', fontsize=12)
ax.set_ylabel('Peak Force (N)', fontsize=12)
ax.set_title('200um PDMS Pyramid: Force vs Radius by Size Range', fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)

# Top-right: Log-log plot
ax = axes[0, 1]
for name, subset, color in [('Small', small, 'blue'), ('Medium', medium, 'green'), ('Large', large, 'red')]:
    if len(subset) > 0:
        ax.scatter(subset['part_radius_mm'], subset['peak_force_N'], 
                  color=color, alpha=0.6, s=50, label=name)
ax.plot(x_fit, y_fit, 'k--', linewidth=2, label=f'Fit: n={overall_result["n"]:.2f}')
ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlabel('Part Radius (mm)', fontsize=12)
ax.set_ylabel('Peak Force (N)', fontsize=12)
ax.set_title('Log-Log Plot (R² = {:.3f})'.format(overall_result['R2']), fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)

# Bottom-left: Residuals vs size
ax = axes[1, 0]
ax.scatter(pyramid_200um['area_mm2'], residuals, alpha=0.6, s=50)
ax.axhline(0, color='red', linestyle='--', linewidth=2, label='Perfect fit')
# Add trend line if significant
if p < 0.05:
    z = np.polyfit(pyramid_200um['area_mm2'], residuals, 1)
    p_fit = np.poly1d(z)
    ax.plot(pyramid_200um['area_mm2'], p_fit(pyramid_200um['area_mm2']), 
            'orange', linewidth=2, label=f'Trend (r={corr:.3f})')
ax.set_xlabel('Part Area (mm²)', fontsize=12)
ax.set_ylabel('Log Residuals', fontsize=12)
ax.set_title(f'Residuals vs Size (r={corr:.3f}, p={p:.4f})', fontsize=14)
ax.grid(True, alpha=0.3)
ax.legend()

# Bottom-right: Force vs Area
ax = axes[1, 1]
for name, subset, color in [('Small', small, 'blue'), ('Medium', medium, 'green'), ('Large', large, 'red')]:
    if len(subset) > 0:
        ax.scatter(subset['area_mm2'], subset['peak_force_N'], 
                  color=color, alpha=0.6, s=50, label=name)

# Overall fit for area
log_x_area = np.log(pyramid_200um['area_mm2'])
log_y_area = np.log(pyramid_200um['peak_force_N'])
slope_area, intercept_area, r_area, _, _ = stats.linregress(log_x_area, log_y_area)
x_fit_area = np.linspace(pyramid_200um['area_mm2'].min(), pyramid_200um['area_mm2'].max(), 100)
k_area = np.exp(intercept_area)
y_fit_area = k_area * x_fit_area ** slope_area
ax.plot(x_fit_area, y_fit_area, 'k--', linewidth=2, 
        label=f'Fit: n={slope_area:.2f} (R²={r_area**2:.3f})')

ax.set_xlabel('Part Area (mm²)', fontsize=12)
ax.set_ylabel('Peak Force (N)', fontsize=12)
ax.set_title('Force vs Area', fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
output_path = script_dir / 'post-processing/scaling_tests_results/200um_pyramid_size_dependence_analysis.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f'\n✓ Plot saved: {output_path}')
