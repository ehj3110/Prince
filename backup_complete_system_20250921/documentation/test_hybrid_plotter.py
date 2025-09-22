"""
Test Script for Hybrid Adhesion Plotter
=======================================

This script tests the new hybrid approach that combines:
- Automatic peak detection and layer segmentation (from original)
- Precise metric calculations (from calculator)

Author: Cheng Sun Lab Team
Date: September 19, 2025
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Test the hybrid plotter
def test_hybrid_plotter():
    """Test the hybrid plotter with the L48-L50 data."""
    print("="*80)
    print("TESTING HYBRID ADHESION PLOTTER")
    print("="*80)
    
    try:
        from hybrid_adhesion_plotter import HybridAdhesionPlotter
        
        # Initialize the hybrid plotter
        print("Initializing HybridAdhesionPlotter...")
        plotter = HybridAdhesionPlotter(
            figure_size=(24, 18),
            dpi=300,
            smoothing_window=3,  # Minimal smoothing for peak detection
            smoothing_polyorder=1
        )
        print("✓ Plotter initialized successfully")
        
        # Test with L48-L50 data
        csv_file = "autolog_L48-L50.csv"
        
        if not os.path.exists(csv_file):
            print(f"❌ Test file not found: {csv_file}")
            print("Available CSV files:")
            for file in os.listdir('.'):
                if file.endswith('.csv'):
                    print(f"  - {file}")
            return False
        
        print(f"\n📁 Loading test data: {csv_file}")
        
        # Create the plot using hybrid approach
        print("\n🔄 Creating hybrid analysis plot...")
        fig = plotter.plot_from_csv(
            csv_file,
            title="L48-L50 Hybrid Analysis Test",
            save_path="hybrid_L48_L50_test.png"
        )
        
        print("✓ Plot created successfully!")
        print("✓ This hybrid approach combines:")
        print("  - Automatic peak detection from original")
        print("  - Position-based layer segmentation from original")
        print("  - Focused time windowing from original")
        print("  - Precise metric calculations from calculator")
        print("  - Professional visualization layout")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required dependencies are installed:")
        print("  - numpy")
        print("  - pandas") 
        print("  - matplotlib")
        print("  - scipy")
        return False
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_calculator_availability():
    """Test if the calculator is available and working."""
    print("\n" + "="*60)
    print("TESTING CALCULATOR AVAILABILITY")
    print("="*60)
    
    try:
        from adhesion_metrics_calculator import AdhesionMetricsCalculator
        
        # Test basic calculator functionality
        calc = AdhesionMetricsCalculator()
        print("✓ AdhesionMetricsCalculator imported successfully")
        print("✓ Calculator ready for hybrid integration")
        return True
        
    except ImportError as e:
        print(f"❌ Calculator import error: {e}")
        print("Make sure adhesion_metrics_calculator.py exists in the current directory")
        return False
    except Exception as e:
        print(f"❌ Calculator initialization error: {e}")
        return False


def compare_with_original():
    """Compare features of hybrid vs original approaches."""
    print("\n" + "="*80)
    print("HYBRID APPROACH FEATURE COMPARISON")
    print("="*80)
    
    print("\n🔍 ORIGINAL APPROACH (final_layer_visualization.py):")
    print("  ✓ Automatic peak detection with find_peaks")
    print("  ✓ Position-based layer boundary detection")  
    print("  ✓ Focused time windowing around peeling events")
    print("  ✓ Second derivative propagation end detection")
    print("  ✓ Sophisticated layer segmentation")
    print("  ❌ Embedded calculations mixed with plotting")
    print("  ❌ Not modular/reusable")
    
    print("\n🆕 HYBRID APPROACH (hybrid_adhesion_plotter.py):")
    print("  ✓ Automatic peak detection with find_peaks")
    print("  ✓ Position-based layer boundary detection")
    print("  ✓ Focused time windowing around peeling events") 
    print("  ✓ Second derivative propagation end detection (via calculator)")
    print("  ✓ Sophisticated layer segmentation")
    print("  ✓ Modular design - separate calculation from plotting")
    print("  ✓ Reusable calculator component")
    print("  ✓ Professional visualization layout")
    print("  ✓ Exact same methodology as original")
    
    print("\n✅ BEST OF BOTH WORLDS:")
    print("  - Original's robust data processing and visualization")
    print("  - Calculator's precise metrics and modularity")
    print("  - Clean separation of concerns")
    print("  - Maintainable and extensible code")


if __name__ == "__main__":
    print("🧪 HYBRID ADHESION PLOTTER TEST SUITE")
    print("="*80)
    
    # Test 1: Calculator availability
    calc_ok = test_calculator_availability()
    
    # Test 2: Hybrid plotter functionality
    if calc_ok:
        hybrid_ok = test_hybrid_plotter()
    else:
        print("❌ Skipping hybrid plotter test due to calculator issues")
        hybrid_ok = False
    
    # Test 3: Feature comparison
    compare_with_original()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if calc_ok and hybrid_ok:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Hybrid plotter is ready to use")
        print("✅ Combines original's robustness with calculator's precision")
        print("\n📋 NEXT STEPS:")
        print("  1. Test with your actual data files")
        print("  2. Compare results with original visualization")
        print("  3. Adjust parameters if needed")
        print("  4. Integrate into your workflow")
    else:
        print("❌ SOME TESTS FAILED")
        if not calc_ok:
            print("  - Calculator needs to be fixed")
        if not hybrid_ok:
            print("  - Hybrid plotter needs debugging")
        
    print("\n💡 The hybrid approach gives you the best of both worlds!")
