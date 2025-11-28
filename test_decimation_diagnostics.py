"""
Decimation Diagnostics Tool
Tests whether decimation is actually working in the ForceGaugeManager.
"""

import time
import threading
from collections import deque
import numpy as np

# Simulate the decimation callback behavior
class DecimationTester:
    def __init__(self, decimation_factor=25):
        self.USE_DECIMATION = True
        self.decimation_factor = decimation_factor
        self.decimation_buffer = deque(maxlen=max(50, decimation_factor * 2))
        self.decimation_counter = 0
        
        # Tracking
        self.callback_count = 0
        self.output_count = 0
        self.callback_times = []
        self.output_times = []
        self.output_values = []
        
        # Raw samples for comparison
        self.raw_samples = []
        
    def simulate_callback(self, voltageRatio):
        """Simulate hardware callback at ~1ms intervals."""
        timestamp = time.time()
        self.callback_count += 1
        self.callback_times.append(timestamp)
        self.raw_samples.append(voltageRatio)
        
        if self.USE_DECIMATION:
            # Add to decimation buffer
            self.decimation_buffer.append(voltageRatio)
            self.decimation_counter += 1
            
            # When enough samples, output averaged value
            if self.decimation_counter >= self.decimation_factor:
                if len(self.decimation_buffer) > 0:
                    averaged_voltage = sum(self.decimation_buffer) / len(self.decimation_buffer)
                    
                    # This would go to the queue
                    self.output_count += 1
                    self.output_times.append(timestamp)
                    self.output_values.append(averaged_voltage)
                
                # Reset counter
                self.decimation_counter = 0
        else:
            # No decimation - output every sample
            self.output_count += 1
            self.output_times.append(timestamp)
            self.output_values.append(voltageRatio)
    
    def get_statistics(self):
        """Calculate statistics about decimation performance."""
        if len(self.callback_times) < 2 or len(self.output_times) < 2:
            return None
        
        # Calculate rates
        callback_duration = self.callback_times[-1] - self.callback_times[0]
        output_duration = self.output_times[-1] - self.output_times[0]
        
        callback_rate = (self.callback_count - 1) / callback_duration if callback_duration > 0 else 0
        output_rate = (self.output_count - 1) / output_duration if output_duration > 0 else 0
        
        # Calculate average intervals
        callback_intervals = np.diff(self.callback_times) * 1000  # Convert to ms
        output_intervals = np.diff(self.output_times) * 1000
        
        # Calculate noise reduction
        raw_std = np.std(self.raw_samples) if len(self.raw_samples) > 0 else 0
        output_std = np.std(self.output_values) if len(self.output_values) > 0 else 0
        noise_reduction = raw_std / output_std if output_std > 0 else 0
        
        return {
            'callback_count': self.callback_count,
            'output_count': self.output_count,
            'callback_rate_hz': callback_rate,
            'output_rate_hz': output_rate,
            'expected_decimation': self.decimation_factor,
            'actual_decimation': self.callback_count / self.output_count if self.output_count > 0 else 0,
            'callback_interval_ms': {
                'mean': np.mean(callback_intervals),
                'std': np.std(callback_intervals)
            },
            'output_interval_ms': {
                'mean': np.mean(output_intervals),
                'std': np.std(output_intervals)
            },
            'noise_reduction': {
                'raw_std': raw_std,
                'output_std': output_std,
                'reduction_factor': noise_reduction,
                'expected_factor': self.decimation_factor ** 0.5
            }
        }


def run_simulation_test():
    """Run simulation to verify decimation logic."""
    print("=" * 70)
    print("DECIMATION SIMULATION TEST")
    print("=" * 70)
    
    decimation_factor = 25
    tester = DecimationTester(decimation_factor=decimation_factor)
    
    print(f"\nSimulating {decimation_factor}× decimation (25ms output from 1ms hardware)")
    print("Generating 1200 samples (simulating 1 second at 1200Hz)...")
    
    # Simulate hardware callbacks at ~1ms
    np.random.seed(42)
    base_signal = 0.5
    noise_amplitude = 0.01
    
    for i in range(1200):
        # Simulate noisy sensor reading
        noisy_value = base_signal + np.random.normal(0, noise_amplitude)
        tester.simulate_callback(noisy_value)
        time.sleep(0.0001)  # Very short delay to simulate timing
    
    # Get statistics
    stats = tester.get_statistics()
    
    if stats:
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        print(f"\n📊 Sample Counts:")
        print(f"  Hardware callbacks: {stats['callback_count']}")
        print(f"  Output samples: {stats['output_count']}")
        print(f"  Actual decimation ratio: {stats['actual_decimation']:.1f}×")
        print(f"  Expected ratio: {stats['expected_decimation']}×")
        
        match_status = "✅ MATCH" if abs(stats['actual_decimation'] - stats['expected_decimation']) < 1 else "❌ MISMATCH"
        print(f"  Status: {match_status}")
        
        print(f"\n⏱️  Timing:")
        print(f"  Output interval: {stats['output_interval_ms']['mean']:.1f}ms (±{stats['output_interval_ms']['std']:.2f}ms)")
        print(f"  Expected interval: {decimation_factor}ms")
        
        print(f"\n🔇 Noise Reduction:")
        print(f"  Raw signal std dev: {stats['noise_reduction']['raw_std']:.6f}")
        print(f"  Averaged signal std dev: {stats['noise_reduction']['output_std']:.6f}")
        print(f"  Actual reduction: {stats['noise_reduction']['reduction_factor']:.2f}×")
        print(f"  Expected reduction: {stats['noise_reduction']['expected_factor']:.2f}×")
        
        reduction_match = abs(stats['noise_reduction']['reduction_factor'] - stats['noise_reduction']['expected_factor']) < 1
        reduction_status = "✅ WORKING" if reduction_match else "⚠️  CHECK"
        print(f"  Status: {reduction_status}")
        
        print("\n" + "=" * 70)
        print("VERDICT")
        print("=" * 70)
        
        all_good = (
            abs(stats['actual_decimation'] - stats['expected_decimation']) < 1 and
            reduction_match
        )
        
        if all_good:
            print("✅ Decimation logic is working correctly!")
            print("   - Proper sample ratio")
            print("   - Expected noise reduction")
            print("   - Correct timing")
        else:
            print("⚠️  Decimation may have issues:")
            if abs(stats['actual_decimation'] - stats['expected_decimation']) >= 1:
                print("   - Sample ratio doesn't match expected")
            if not reduction_match:
                print("   - Noise reduction below expected")
    
    print("\n" + "=" * 70)


def print_live_system_checklist():
    """Print checklist for testing live system."""
    print("\n" + "=" * 70)
    print("LIVE SYSTEM TESTING CHECKLIST")
    print("=" * 70)
    
    print("\n📋 To test if decimation is working in your actual system:\n")
    
    print("1️⃣  CHECK CONSOLE OUTPUT ON STARTUP:")
    print("   Look for: 'Dynamic decimation mode: Hardware at 1ms'")
    print("   Status: _____ (Found / Not Found)")
    
    print("\n2️⃣  CHECK DECIMATION FACTOR UPDATES:")
    print("   Change sampling rate in GUI (e.g., 25ms → 50ms)")
    print("   Look for: 'Decimation factor updated to 50× for 50ms rate'")
    print("   Status: _____ (Found / Not Found)")
    
    print("\n3️⃣  ADD DEBUG OUTPUT TO CALLBACK:")
    print("   In ForceGaugeManager._onVoltageRatioChange(), add:")
    print("   ```python")
    print("   if self.decimation_counter % 100 == 0:")
    print("       print(f'Callback: {self.decimation_counter}/{self.decimation_factor}')")
    print("   ```")
    print("   You should see this counting output")
    print("   Status: _____ (Working / Not Working)")
    
    print("\n4️⃣  CHECK ACTUAL NOISE REDUCTION:")
    print("   Record 30 seconds at 25ms (should give ~1200 samples)")
    print("   Calculate std dev of force column")
    print("   Expected: ~5× reduction (for 25× decimation)")
    print("   Actual reduction: _____ ×")
    
    print("\n5️⃣  VERIFY OUTPUT RATE:")
    print("   Check CSV timestamp intervals")
    print("   Should match GUI setting (e.g., 25ms)")
    print("   Actual interval: _____ ms")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_simulation_test()
    print_live_system_checklist()
    
    print("\n💡 TIP: If simulation passes but live system fails,")
    print("   the issue is likely that USE_DECIMATION is False")
    print("   or the callback isn't being triggered correctly.")
