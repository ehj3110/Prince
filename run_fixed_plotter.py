"""
Run fixed hybrid plotter with smaller figure size to avoid image size error
"""
from hybrid_adhesion_plotter import HybridAdhesionPlotter

# Create plotter instance with smaller DPI to avoid image size error
plotter = HybridAdhesionPlotter()
plotter.dpi = 100  # Reduce from default to avoid large image

print("Creating plot with fixed hybrid adhesion plotter...")
print("Processing autolog_L198-L200.csv")

try:
    # Plot from CSV with fixed calculator
    fig = plotter.plot_from_csv(
        "autolog_L198-L200.csv",
        title="L198-L200 Fixed Analysis",
        save_path="fixed_calculator_L198_L200_analysis.png"
    )
    
    print("Plot completed successfully!")
    print("You can now see if Layer 198 propagation end shows ~11.8s as expected")
    
except Exception as e:
    print(f"Plotting error: {e}")
    print("Let me try with an even smaller figure...")
    
    # Try with minimal plotting
    plotter.figure_width = 8
    plotter.figure_height = 6
    plotter.dpi = 80
    
    fig = plotter.plot_from_csv(
        "autolog_L198-L200.csv", 
        title="L198-L200 Fixed Analysis (Compact)",
        save_path="fixed_calculator_compact.png"
    )
    
    print("Compact plot completed!")
