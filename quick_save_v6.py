"""
Quick V6 Stiffness Analysis - Use Existing Results
===================================================

Saves the stiffness results that were just calculated.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'batch_processors'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))

from batch_process_universal import UniversalBatchProcessor

V6_DIR = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6')

# The processor was already run and all_results are stored
# We just need to save them
processor = UniversalBatchProcessor(str(V6_DIR))

# Process all folders (this should be fast if already done recently)
print("Processing folders...")
processor.process_all_folders()

# Save CSV and generate plots
print("\nSaving CSV...")
csv_path = processor.save_combined_csv()

print("\nGenerating master plots...")
processor.generate_master_plots()

print(f"\nDone! CSV saved to: {csv_path}")
