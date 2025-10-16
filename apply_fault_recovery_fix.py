"""
Apply the fault recovery fix to Prince_Segmented.py
Fixes the bug: 'Warnings' object has no attribute 'clear'
"""

import re

# Read the file
with open('Prince_Segmented.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the old buggy code
old_code = """                            try:
                                # Clear any faults
                                self.axis.warnings.clear()
                                time.sleep(0.5)
                                
                                # Try a very slow, gentle movement back up"""

# Define the fixed code
new_code = """                            try:
                                # Clear any faults by sending home command to reset state
                                # Note: Zaber warnings don't have a .clear() method
                                # Instead, we try to reset the axis state
                                self.axis.home(wait_until_idle=False)
                                time.sleep(0.5)
                                self.axis.stop()
                                time.sleep(0.5)
                                
                                # Try a very slow, gentle movement back up"""

# Apply the fix
if old_code in content:
    content = content.replace(old_code, new_code)
    print("✓ Fix applied successfully!")
    
    # Write back
    with open('Prince_Segmented.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ File saved!")
else:
    print("✗ Could not find the buggy code - it may have already been fixed or the code has changed.")
    print("\nSearching for 'warnings.clear'...")
    if 'warnings.clear()' in content:
        # Find the line number
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'warnings.clear()' in line:
                print(f"  Found at line {i}: {line.strip()}")
    else:
        print("  'warnings.clear()' not found - may already be fixed!")
