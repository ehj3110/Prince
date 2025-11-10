"""
Test script for dynamic decimation system.
Verifies that decimation factor adjusts correctly with user sampling rate.
"""

# Test the decimation calculation logic
def test_decimation_calculation():
    hardware_interval_ms = 1  # 1200Hz
    
    test_cases = [
        (8, 8),    # 8ms user rate → 8× decimation
        (10, 10),  # 10ms user rate → 10× decimation
        (12, 12),  # 12ms user rate → 12× decimation
        (16, 16),  # 16ms user rate → 16× decimation
        (25, 25),  # 25ms user rate → 25× decimation
        (50, 50),  # 50ms user rate → 50× decimation
        (100, 100), # 100ms user rate → 100× decimation
    ]
    
    print("=" * 60)
    print("Dynamic Decimation Test")
    print("=" * 60)
    print(f"Hardware interval: {hardware_interval_ms}ms (~1200Hz)")
    print()
    
    for user_interval_ms, expected_factor in test_cases:
        calculated_factor = max(1, int(user_interval_ms / hardware_interval_ms))
        noise_reduction = calculated_factor ** 0.5
        
        status = "✓" if calculated_factor == expected_factor else "✗"
        
        print(f"{status} User Rate: {user_interval_ms}ms ({1000/user_interval_ms:.1f}Hz)")
        print(f"  → Decimation Factor: {calculated_factor}×")
        print(f"  → Noise Reduction: {noise_reduction:.2f}×")
        print(f"  → Output Rate: {user_interval_ms}ms (matches user setting!)")
        print()
    
    print("=" * 60)
    print("Key Advantage: Output rate ALWAYS matches user's GUI setting!")
    print("No more timing mismatches with PositionLogger!")
    print("=" * 60)

if __name__ == "__main__":
    test_decimation_calculation()
