"""
Reprocess each TEMPO Picker V2 folder individually
Processes autolog files in each folder to regenerate automated_work_of_adhesion.csv
"""

import subprocess
import sys
from pathlib import Path

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
    print("TEMPO Picker V2 - Individual Folder Reprocessing")
    print("="*80)
    
    success_count = 0
    failed_folders = []
    
    for i, folder in enumerate(folders, 1):
        folder_path = v2_dir / folder
        print(f"\n[{i}/{len(folders)}] Processing: {folder}")
        print("-" * 80)
        
        if not folder_path.exists():
            print(f"  ✗ ERROR: Folder not found: {folder_path}")
            failed_folders.append(folder)
            continue
        
        # Create a temporary parent directory structure for batch processor
        # batch_process_universal expects a parent with subfolders
        temp_parent = v2_dir / f"_temp_{folder}"
        temp_subfolder = temp_parent / folder
        
        try:
            # Create temporary structure
            temp_subfolder.mkdir(parents=True, exist_ok=True)
            
            # Copy autolog files to temp location
            autolog_files = list(folder_path.glob("autolog_*.csv"))
            print(f"  Found {len(autolog_files)} autolog files")
            
            for autolog_file in autolog_files:
                dest = temp_subfolder / autolog_file.name
                import shutil
                shutil.copy2(autolog_file, dest)
            
            # Run batch processor on temporary parent
            cmd = [
                sys.executable,
                "batch_processors/batch_process_universal.py",
                str(temp_parent)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            
            # Copy results back to original folder
            result_csv = temp_subfolder / "automated_work_of_adhesion.csv"
            result_plots = temp_subfolder / "plots"
            
            if result_csv.exists():
                dest_csv = folder_path / "automated_work_of_adhesion.csv"
                shutil.copy2(result_csv, dest_csv)
                print(f"  ✓ Updated: automated_work_of_adhesion.csv")
                success_count += 1
            else:
                print(f"  ✗ ERROR: No automated_work_of_adhesion.csv generated")
                failed_folders.append(folder)
            
            if result_plots.exists():
                dest_plots = folder_path / "plots"
                if dest_plots.exists():
                    import shutil
                    shutil.rmtree(dest_plots)
                shutil.copytree(result_plots, dest_plots)
                plot_count = len(list(result_plots.glob("*.png")))
                print(f"  ✓ Generated {plot_count} plots")
            
            # Clean up temp directory
            shutil.rmtree(temp_parent)
            
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            failed_folders.append(folder)
            # Try to clean up temp directory
            try:
                if temp_parent.exists():
                    shutil.rmtree(temp_parent)
            except:
                pass
    
    # Summary
    print("\n" + "="*80)
    print(f"Processing Complete: {success_count}/{len(folders)} folders successful")
    print("="*80)
    
    if failed_folders:
        print("\nFailed folders:")
        for folder in failed_folders:
            print(f"  - {folder}")
        return False
    
    print("\n✓ All folders reprocessed successfully!")
    print("\nNext step: Run generate_tempopicker_v2_master_plots.py to create master plots")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
