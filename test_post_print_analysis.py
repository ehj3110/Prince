"""
Test script to simulate end-of-print analysis
Creates synthetic force/position data and tests the post-print analysis pipeline
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys
import os

# Add support_modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'support_modules'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'post-processing'))

def generate_synthetic_peel_data(num_layers=6, base_time=0.0, sampling_rate=100):
    """
    Generate synthetic force/position data that mimics a real peeling process.
    
    Args:
        num_layers: Number of layers to simulate
        base_time: Starting time
        sampling_rate: Samples per second (Hz)
    
    Returns:
        DataFrame with columns: Elapsed Time (s), Force (N), Position (mm), Phase
    """
    all_data = []
    current_time = base_time
    current_position = 70.0  # Start at reference position
    
    for layer in range(num_layers):
        # Phase 1: Sandwich (compression) - moving down, force builds up
        sandwich_duration = 2.0  # seconds
        sandwich_samples = int(sandwich_duration * sampling_rate)
        
        for i in range(sandwich_samples):
            t = current_time + i / sampling_rate
            # Move down slowly
            pos = current_position - (i / sandwich_samples) * 0.5  # Move down 0.5mm
            # Force builds up gradually (compression is negative)
            force = -0.15 * (i / sandwich_samples)
            all_data.append([t, force, pos, 'Sandwich'])
        
        current_time += sandwich_duration
        current_position -= 0.5
        
        # Phase 2: Lifting (peel) - moving up, force increases to peak then drops
        lifting_duration = 4.0  # seconds
        lifting_samples = int(lifting_duration * sampling_rate)
        peak_force = 0.12 + np.random.uniform(-0.02, 0.04)  # Random peak 0.10-0.16N
        
        for i in range(lifting_samples):
            t = current_time + i / sampling_rate
            # Move up to peel
            pos = current_position + (i / lifting_samples) * 6.0  # Peel up 6mm
            
            # Force profile: ramps up to peak around 30%, then drops off
            if i < lifting_samples * 0.3:
                # Pre-initiation: gradual buildup
                force = (i / (lifting_samples * 0.3)) * peak_force
            elif i < lifting_samples * 0.5:
                # Peak region
                force = peak_force * (1 - 0.1 * np.random.random())
            else:
                # Propagation: force drops off
                decay = (i - lifting_samples * 0.5) / (lifting_samples * 0.5)
                force = peak_force * (1 - decay) * 0.3
            
            # Add noise
            force += np.random.normal(0, 0.002)
            all_data.append([t, force, pos, 'Lift'])
        
        current_time += lifting_duration
        current_position += 6.0
        
        # Phase 3: Retraction (return down) - moving down, minimal force
        retraction_duration = 4.0  # seconds
        retraction_samples = int(retraction_duration * sampling_rate)
        
        for i in range(retraction_samples):
            t = current_time + i / sampling_rate
            # Move back down
            pos = current_position - (i / retraction_samples) * 6.0  # Return 6mm
            # Small retraction force at end
            if i > retraction_samples * 0.8:
                force = 0.025 + np.random.normal(0, 0.002)
            else:
                force = 0.005 + np.random.normal(0, 0.002)
            all_data.append([t, force, pos, 'Retract'])
        
        current_time += retraction_duration
        current_position -= 6.0
        
        # Small pause between layers
        pause_duration = 0.5
        pause_samples = int(pause_duration * sampling_rate)
        for i in range(pause_samples):
            t = current_time + i / sampling_rate
            force = np.random.normal(0, 0.001)
            all_data.append([t, force, current_position, 'Pause'])
        
        current_time += pause_duration
    
    # Create DataFrame
    df = pd.DataFrame(all_data, columns=['Elapsed Time (s)', 'Force (N)', 'Position (mm)', 'Phase'])
    return df

def create_test_session():
    """Create a test printing session directory with synthetic data"""
    
    # Create test directory structure
    test_dir = Path(__file__).parent / "test_post_print_data"
    test_dir.mkdir(exist_ok=True)
    
    session_dir = test_dir / "Print 1"
    session_dir.mkdir(exist_ok=True)
    
    print(f"Creating test session in: {session_dir}")
    
    # Generate synthetic data for layers 60-65
    print("Generating synthetic force/position data...")
    df = generate_synthetic_peel_data(num_layers=6, base_time=0.0, sampling_rate=100)
    
    # Save CSV file with expected naming convention
    csv_file = session_dir / "autolog_L60-L65.csv"
    df.to_csv(csv_file, index=False)
    print(f"✓ Created CSV file: {csv_file.name} ({len(df)} data points)")
    
    # Create work of adhesion CSV (simulated from PeakForceLogger)
    woa_data = []
    for layer_num in range(60, 66):
        woa_data.append({
            'Layer_Number': layer_num,
            'Peak_Force_N': np.random.uniform(0.10, 0.17),
            'Work_of_Adhesion_mJ': np.random.uniform(0.3, 0.8),
            'Initiation_Time_s': np.random.uniform(0.5, 1.2),
            'Propagation_Duration_s': np.random.uniform(1.5, 2.5),
            'Total_Duration_s': np.random.uniform(2.0, 3.5),
            'Distance_to_Peak_mm': np.random.uniform(1.5, 2.5),
            'Distance_to_Propagate_mm': np.random.uniform(3.0, 4.5),
            'Total_Peel_Distance_mm': np.random.uniform(5.0, 6.5),
            'Peak_Retraction_Force_N': np.random.uniform(0.020, 0.035),
            'Cross_Sectional_Area_mm2': 31.67  # Standard Ø6.35mm platform
        })
    
    woa_df = pd.DataFrame(woa_data)
    woa_file = session_dir / "automated_work_of_adhesion.csv"
    woa_df.to_csv(woa_file, index=False)
    print(f"✓ Created work of adhesion file: {woa_file.name} ({len(woa_df)} layers)")
    
    return session_dir

def run_post_print_analysis(session_dir):
    """Run the post-print analysis on the test session"""
    from post_print_analyzer import PostPrintAnalyzer
    
    print("\n" + "="*60)
    print("STARTING POST-PRINT ANALYSIS TEST")
    print("="*60)
    
    try:
        # Initialize analyzer
        analyzer = PostPrintAnalyzer()
        
        # Create session dictionary matching expected format
        csv_files = list(session_dir.glob("autolog_*.csv"))
        session = {
            'date': '2025-11-24',
            'print_number': 'Print 1',
            'path': session_dir,
            'csv_files': csv_files
        }
        
        # Run analysis on the test session
        results = analyzer.analyze_print_session(session)
        
        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        
        if results:
            print(f"✓ Analysis completed successfully")
            print(f"  Sessions processed: {len(results)}")
            for result in results:
                print(f"\n  CSV: {result['csv_file'].name}")
                print(f"  Layers: {result['data_points']}")
                if result.get('plot_path'):
                    print(f"  Plot: {result['plot_path'].name}")
                else:
                    print(f"  Plot: Not generated")
            
            # Check if files were created
            print("\n" + "="*60)
            print("GENERATED FILES")
            print("="*60)
            
            output_dir = session_dir / "Post_Processing"
            if output_dir.exists():
                files = list(output_dir.glob("*"))
                for f in files:
                    size_kb = f.stat().st_size / 1024
                    print(f"  ✓ {f.name} ({size_kb:.1f} KB)")
                
                # Check for plot files
                plots = list(output_dir.glob("*.png"))
                if plots:
                    print(f"\n  📊 {len(plots)} plot(s) generated successfully!")
                else:
                    print(f"\n  ⚠️  No plots found")
            else:
                print("  ⚠️  Output directory not created")
            
            return True
        else:
            print("✗ Analysis returned no results")
            return False
            
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("POST-PRINT ANALYSIS TEST SCRIPT")
    print("="*60)
    
    # Step 1: Create test data
    print("\n[1/2] Creating test session with synthetic data...")
    session_dir = create_test_session()
    
    # Step 2: Run analysis
    print("\n[2/2] Running post-print analysis...")
    success = run_post_print_analysis(session_dir)
    
    # Summary
    print("\n" + "="*60)
    if success:
        print("✓ TEST PASSED - Analysis pipeline is working correctly!")
        print(f"\nTest data location: {session_dir}")
        print("Check the Post_Processing folder for generated plots and summaries.")
    else:
        print("✗ TEST FAILED - See errors above")
    print("="*60)
