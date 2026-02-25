"""
Reprocess only TEMPO folders with updated hydrodynamic locking mitigation
"""
import sys
from pathlib import Path

# Add support_modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'post-processing'))

from batch_process_v9 import V9BatchProcessor

if __name__ == "__main__":
    print("="*60)
    print("Reprocessing TEMPO folders with extended skip time")
    print("="*60 + "\n")
    
    # Create processor
    processor = V9BatchProcessor(skip_individual_plots=False)
    
    # Get TEMPO folders only
    v9_path = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9")
    
    tempo_folders = [
        v9_path / "TEMPO_200um_V23Ext_UPW_1000",
        v9_path / "TEMPO_200um_V23Ext_Water_1000"
    ]
    
    # Process each TEMPO folder
    for folder in tempo_folders:
        if folder.exists():
            print(f"\n{'='*60}")
            print(f"Processing: {folder.name}")
            print('='*60)
            processor.process_single_folder(folder)
        else:
            print(f"Warning: {folder} not found")
    
    print("\n" + "="*60)
    print("TEMPO reprocessing complete!")
    print("="*60)
    print("\nNote: Run full batch_process_v9.py to regenerate master plots with updated data.")
