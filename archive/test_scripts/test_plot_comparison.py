"""
Quick test to show the difference between scatter and plot styles
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Sample data
x = np.array([1, 2, 3, 4, 5])
y = np.array([2, 4, 3, 5, 4])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# LEFT: Using plot with 'o' marker (creates connecting line)
ax1.plot(x, y, 'o', markersize=8, color='blue', label='Data')
ax1.set_title('Using ax.plot(x, y, "o") - WRONG\nConnects points with invisible line', fontweight='bold')
ax1.set_xlabel('X')
ax1.set_ylabel('Y')
ax1.grid(True, alpha=0.3)
ax1.legend()

# RIGHT: Using scatter (no connecting line)
ax2.scatter(x, y, s=64, color='red', label='Data', edgecolors='none')
ax2.set_title('Using ax.scatter(x, y) - CORRECT\nNo connecting lines', fontweight='bold')
ax2.set_xlabel('X')
ax2.set_ylabel('Y')
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.tight_layout()
plt.savefig('test_plot_vs_scatter.png', dpi=150)
print("✓ Saved test_plot_vs_scatter.png")
print("\nThe V2 master plots now use scatter() on the RIGHT side.")
