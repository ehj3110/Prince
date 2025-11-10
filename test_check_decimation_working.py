"""
Quick test to verify decimation is working in your live system.
Run this WHILE Prince is running and recording force data.
"""

import pandas as pd
import numpy as np
import sys

def analyze_force_data(csv_file):
    """Analyze a force data CSV to check if decimation is working."""
    print("=" * 70)
    print("FORCE DATA ANALYSIS - Checking for Decimation")
    print("=" * 70)
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        
        print(f"\n📁 File: {csv_file}")
        print(f"   Rows: {len(df)}")
        
        # Check columns
        if 'Time(s)' not in df.columns or 'Force (N)' not in df.columns:
            print("❌ CSV doesn't have expected columns")
            return
        
        times = df['Time(s)'].values
        forces = df['Force (N)'].values
        
        # Calculate time intervals
        if len(times) > 1:
            intervals = np.diff(times) * 1000  # Convert to ms
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            
            print(f"\n⏱️  Timing Analysis:")
            print(f"   Mean interval: {mean_interval:.2f}ms")
            print(f"   Std dev: {std_interval:.2f}ms")
            print(f"   Expected: Should match your GUI setting (e.g., 25ms)")
            
            # Check for consistency
            if std_interval < 2:
                print(f"   ✅ Timing is consistent")
            else:
                print(f"   ⚠️  Timing varies significantly")
        
        # Check for repeated values
        if len(forces) > 1:
            repeated_count = 0
            max_repeat_length = 0
            current_repeat = 1
            
            for i in range(1, len(forces)):
                if np.isclose(forces[i], forces[i-1], atol=1e-10):
                    current_repeat += 1
                    max_repeat_length = max(max_repeat_length, current_repeat)
                else:
                    if current_repeat >= 3:
                        repeated_count += 1
                    current_repeat = 1
            
            print(f"\n🔁 Repeated Values Check:")
            print(f"   Sequences of 3+ identical values: {repeated_count}")
            print(f"   Longest repeat sequence: {max_repeat_length}")
            
            if repeated_count == 0:
                print(f"   ✅ No significant repeats (GOOD - decimation working)")
            elif repeated_count < len(forces) * 0.1:
                print(f"   ⚠️  Some repeats (may be OK)")
            else:
                print(f"   ❌ Many repeats (BAD - timing mismatch)")
        
        # Calculate noise/variation
        force_std = np.std(forces)
        force_mean = np.mean(forces)
        force_range = np.max(forces) - np.min(forces)
        
        print(f"\n📊 Force Statistics:")
        print(f"   Mean: {force_mean:.6f} N")
        print(f"   Std dev: {force_std:.6f} N")
        print(f"   Range: {force_range:.6f} N")
        print(f"   Noise ratio (std/mean): {(force_std/force_mean)*100:.2f}%")
        
        # Calculate expected vs actual based on timing
        if len(times) > 1:
            duration = times[-1] - times[0]
            sample_rate = len(times) / duration if duration > 0 else 0
            
            print(f"\n📈 Sample Rate:")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Samples: {len(times)}")
            print(f"   Actual rate: {sample_rate:.1f} Hz")
            print(f"   From interval: {1000/mean_interval:.1f} Hz")
        
        print("\n" + "=" * 70)
        print("VERDICT")
        print("=" * 70)
        
        # Overall assessment
        timing_good = std_interval < 2 if len(times) > 1 else False
        no_repeats = repeated_count == 0 if len(forces) > 1 else False
        
        if timing_good and no_repeats:
            print("✅ System appears to be working correctly")
            print("   - Consistent timing")
            print("   - No repeated values")
            print("   - Decimation likely working as expected")
        elif timing_good and not no_repeats:
            print("⚠️  Timing is good but some repeated values detected")
            print("   - Check if decimation is enabled (USE_DECIMATION = True)")
            print("   - Look for console debug messages")
        else:
            print("❌ Issues detected")
            print("   - Check console output for decimation status")
            print("   - Verify USE_DECIMATION = True")
            print("   - Check if callback is being triggered")
        
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # Default to most recent test file
        csv_file = "test_output.csv"
        print(f"No file specified, using default: {csv_file}")
        print("Usage: python test_check_decimation_working.py <path_to_csv>")
        print()
    
    analyze_force_data(csv_file)
    
    print("\n" + "=" * 70)
    print("WHAT TO CHECK NEXT")
    print("=" * 70)
    print("\n1. Look at console output when Prince starts")
    print("   Should see: 'DECIMATION STATUS' banner with settings")
    print()
    print("2. While recording, watch for:")
    print("   '[DECIMATION DEBUG] Output sample #X: averaged Y samples'")
    print()
    print("3. If you don't see these messages:")
    print("   - Decimation may not be enabled")
    print("   - Callback may not be running")
    print("   - Check USE_DECIMATION in ForceGaugeManager.py")
    print()
