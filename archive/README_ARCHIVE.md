# ARCHIVED FILES - September 21, 2025
**Purpose**: Non-critical files moved to clean up main workspace  
**Status**: Safely archived - can be deleted or restored as needed

---

## 📁 **ARCHIVE ORGANIZATION**

### **old_plots/** 
*Generated visualization files that can be regenerated*
- Test plots (test_display.png, test_plot.png, etc.)
- Diagnostic plots (diagnostic_*.png)
- Analysis result plots (final_*.png, L298-L300_*.png, etc.)
- Troubleshooting plots (troubleshoot_*.png)
- Position analysis plots

### **legacy_docs/**
*Documentation from previous versions and completed work*
- Fix documentation (*FIX_20250917.md)
- Old backup summaries (BACKUP_SUMMARY_20250917.md)
- Integration documentation (INTEGRATION*.md)

### **redundant_scripts/**
*Python scripts replaced by the hybrid system*
- Old plotter (adhesion_metrics_plotter.py - replaced by hybrid)
- Analysis scripts (analyze_single_file.py, etc.)
- Test scripts (test_calculator_and_plotter.py, etc.)
- Debug scripts (comprehensive_diagnostic.py, debug_position.py)
- Troubleshooting scripts (troubleshoot_*.py)

### **analysis_files/**
*File organization and cleanup documentation*
- File categorization analysis
- Cleanup summaries
- Organization documentation

---

## 🔄 **RESTORATION NOTES**

### **Safe to Delete**:
- All files in this archive can be safely deleted
- Plots can be regenerated with current hybrid system
- Scripts are superseded by hybrid_adhesion_plotter.py

### **If Restoration Needed**:
```powershell
# To restore specific files back to main directory
Move-Item "archived_files\[folder]\[filename]" ".\"
```

### **Archive Contents Summary**:
- **old_plots/**: ~12 PNG files (diagnostic and test plots)
- **legacy_docs/**: ~5 MD files (old documentation)
- **redundant_scripts/**: ~12 PY files (superseded scripts)
- **analysis_files/**: ~3 MD files (cleanup documentation)

---

**Total Space Saved**: Significant reduction in main directory clutter  
**Functionality Impact**: None - all essential systems preserved in main directory  
**Recommendation**: Keep archive for 30 days, then delete if no issues encountered
