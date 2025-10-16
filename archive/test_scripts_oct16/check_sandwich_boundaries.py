import sys
sys.path.insert(0, 'post-processing')
sys.path.insert(0, 'support_modules')
from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

filepath = r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SandwichedCone_BPAGDA_6000umps\autolog_L335-L340.csv'
calc = AdhesionMetricsCalculator()
rp = RawDataProcessor(calc)
rp.process_csv(filepath)

print(f'\n=== Detected Boundaries ===')
print(f'First layer lifting phase: {rp.detected_layer_boundaries[0]["lifting"]}')
print(f'First layer retraction: {rp.detected_layer_boundaries[0]["retraction"]}')
print(f'\nPROBLEM: Lifting should start around idx 370-400 (after the 47.20mm hold phase)')
print(f'NOT at index {rp.detected_layer_boundaries[0]["lifting"][0]} which includes pause/exposure time!')
