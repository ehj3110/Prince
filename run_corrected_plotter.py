"""
Run the corrected hybrid plotter with light smoothing settings
"""
from hybrid_adhesion_plotter import HybridAdhesionPlotter

# Create plotter instance
plotter = HybridAdhesionPlotter()

print("Running hybrid plotter with corrected light smoothing settings...")
print("Processing autolog_L198-L200.csv...")

# Generate plot
fig = plotter.plot_from_csv(
    "autolog_L198-L200.csv",
    title="L198-L200 Corrected Analysis (Light Smoothing)",
    save_path="corrected_L198_L200_analysis.png"
)

print("Plot saved as: corrected_L198_L200_analysis.png")
print("Layer 198 should now show propagation end at ~11.7s (corrected from ~11.8s)")
