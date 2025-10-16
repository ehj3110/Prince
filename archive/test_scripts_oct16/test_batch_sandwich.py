"""
Quick batch test on sandwich data to verify the simplified boundary detection
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'post-processing'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Test files
test_files = [
    'post-processing/autolog_L335-L340.csv',
    'post-processing/autolog_L365-L370.csv',
]

calc = AdhesionMetricsCalculator()

print("="*70)
print("BATCH TEST: Sandwich Data with Simplified 6mm Boundary Detection")
print("="*70)

for csv_file in test_files:
    if not os.path.exists(csv_file):
        print(f"\n⚠️  File not found: {csv_file}")
        continue
    
    print(f"\n{'='*70}")
    print(f"Processing: {os.path.basename(csv_file)}")
    print(f"{'='*70}")
    
    processor = RawDataProcessor(calc)
    
    try:
        layers = processor.process_csv(csv_file)
        
        print(f"\n✅ Successfully processed {len(layers)} layers")
        print(f"\nSummary:")
        print(f"  {'Layer':<8} {'Peak Force':<12} {'Pre-Init':<12} {'Propagation':<12}")
        print(f"  {'-'*8} {'-'*12} {'-'*12} {'-'*12}")
        
        for layer in layers:
            metrics = layer['metrics']
            layer_num = metrics.get('layer_number', '?')
            peak = metrics.get('peak_force', 0)
            pre_init = metrics.get('pre_initiation_time', 0)
            prop = metrics.get('propagation_time', 0)
            print(f"  {layer_num:<8} {peak:<12.4f} {pre_init:<12.4f} {prop:<12.4f}")
    
    except Exception as e:
        print(f"\n❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*70}")
print("Batch test complete!")
print(f"{'='*70}")
