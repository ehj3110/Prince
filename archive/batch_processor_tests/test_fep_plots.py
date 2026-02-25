"""
Test script to regenerate plots for FEP folder only
"""
import sys
from pathlib import Path

# Add support_modules and post-processing to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'post-processing'))

from batch_process_v9 import V9BatchProcessor

# Create processor
processor = V9BatchProcessor(skip_individual_plots=False)

# Process just the FEP folder
fep_folder = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9\FEP_500um_V19_Air_400")

print(f"Processing {fep_folder.name}...")
processor.process_single_folder(fep_folder)
print("\nDone!")
