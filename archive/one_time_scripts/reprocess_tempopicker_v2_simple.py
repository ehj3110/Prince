"""
Process all TEMPO Picker V2 folders individually
Then generate master plots
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def main():
    v2_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2")
    
    # List of all folders to process
    folders = [
        "10umTEMPO_400umGap",
        "5umTEMPO_200um",
        "5umTEMPO_200umGap",
        "5umTEMPO_400umGap_Good",
        "FlatTEMPO_400umGap",
        "TEMPO_400umGap"
    ]
    
    print("="*80)
    print("TEMPO Picker V2 - Reprocessing All Folders")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    success_count = 0
    failed_folders = []
    
    # Step 1: Process each folder individually
    for i, folder in enumerate(folders, 1):
        folder_path = v2_dir / folder
        print(f"\n[{i}/{len(folders)}] Processing: {folder}")
        print("-" * 80)
        
        if not folder_path.exists():
            print(f"  ✗ ERROR: Folder not found: {folder_path}")
            failed_folders.append(folder)
            continue
        
        # Run post_print_analyzer on this folder
        cmd = [
            sys.executable,
            "post_print_analyzer.py",
            str(folder_path)
        ]
        
        print(f"  Running: post_print_analyzer.py on {folder}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        # Check if automated_work_of_adhesion.csv was created/updated
        result_csv = folder_path / "automated_work_of_adhesion.csv"
        
        if result_csv.exists():
            file_time = datetime.fromtimestamp(result_csv.stat().st_mtime)
            print(f"  ✓ Updated: automated_work_of_adhesion.csv ({file_time.strftime('%H:%M:%S')})")
            success_count += 1
        else:
            print(f"  ✗ ERROR: No automated_work_of_adhesion.csv generated")
            print(f"\nSTDOUT:\n{result.stdout}")
            print(f"\nSTDERR:\n{result.stderr}")
            failed_folders.append(folder)
    
    print("\n" + "="*80)
    print(f"Folder Processing Complete: {success_count}/{len(folders)} successful")
    print("="*80)
    
    if failed_folders:
        print("\nFailed folders:")
        for folder in failed_folders:
            print(f"  - {folder}")
    
    # Step 2: Generate master plots
    if success_count > 0:
        print("\n" + "="*80)
        print("Generating Master Plots")
        print("="*80)
        
        cmd2 = [
            sys.executable,
            "generate_tempopicker_v2_master_plots.py"
        ]
        
        result2 = subprocess.run(
            cmd2,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result2.returncode == 0:
            print("✓ Master plots generated successfully!")
            print("\nGenerated files:")
            master_dir = v2_dir
            for file in master_dir.glob("MASTER_tempopicker_v2_*"):
                print(f"  - {file.name}")
        else:
            print("✗ ERROR generating master plots")
            print(f"\nSTDOUT:\n{result2.stdout}")
            print(f"\nSTDERR:\n{result2.stderr}")
            return False
    
    print("\n" + "="*80)
    print(f"ALL PROCESSING COMPLETE!")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return len(failed_folders) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
