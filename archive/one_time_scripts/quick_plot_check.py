"""
Quick plot of exported data: Time vs Force with Position on secondary axis
"""
import pandas as pd
import matplotlib.pyplot as plt

# Read data
df = pd.read_csv(r'C:\Users\cheng sun\BoyuanSun\Slicing\Evan\10SqmmCylinder\Printing_Logs\ToProcess\peak_layer_custom_raw.csv')

# Create figure with subplots for each material
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
axes = axes.flatten()

materials = ['PDMS_800nm', 'PDMS_Flat', 'PFPE_800nm', 'PFPE_Flat_NoOil_BPAGDA']

for idx, material in enumerate(materials):
    ax1 = axes[idx]
    
    # Get data
    time = df[f'{material}_Time_s'].dropna()
    force = df[f'{material}_RelativeForce_N'].dropna()[:len(time)]
    position = df[f'{material}_Position_mm'].dropna()[:len(time)]
    
    # Plot force on primary axis
    color1 = 'tab:blue'
    ax1.set_xlabel('Time (s)', fontsize=12)
    ax1.set_ylabel('Relative Force (N)', color=color1, fontsize=12)
    line1 = ax1.plot(time, force, color=color1, linewidth=2, label='Force')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3)
    
    # Create secondary axis for position
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Stage Position (mm)', color=color2, fontsize=12)
    line2 = ax2.plot(time, position, color=color2, linewidth=2, linestyle='--', label='Position', alpha=0.7)
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Title
    ax1.set_title(f'{material}', fontsize=14, fontweight='bold')
    
    # Combined legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right', fontsize=10)

plt.tight_layout()
plt.savefig(r'C:\Users\cheng sun\BoyuanSun\Slicing\Evan\10SqmmCylinder\Printing_Logs\ToProcess\quick_check_plot.png', 
            dpi=300, bbox_inches='tight')
print("Plot saved to: quick_check_plot.png")
plt.show()
