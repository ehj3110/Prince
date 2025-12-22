@echo off
echo ========================================
echo Git Push Script for RED Lab Updates
echo ========================================
echo.

cd C:\printer_code\dinglab_printer_notebook

echo Staging modified files...
git add printer_helper_force_sensing.py
git add support_modules\SensorDataWindow.py
git add AUTOMATED_LOGGING_INTEGRATION_COMPLETE.md
git add AUTOMATED_LOGGING_STATUS.md
git add AUTOMATED_LOGGING_ROOT_CAUSE.md
git add MIGRATION_GUIDE_GITHUB_TO_CURRENT_SYSTEM.md
git add GIT_COMMIT_GUIDE.md
git add MULTITHREADING_ANALYSIS.md

echo.
echo Creating commit...
git commit -m "feat: Add automated layer logging integration for RED Lab

- Added 3 integration hooks to print loop:
  * Print start: Configure logging session
  * Layer update: Log each layer with Z position
  * Print end: Save collected data to CSV

- Fixed SensorDataWindow path handling:
  * Extract directory from txt file path (RED Lab compatibility)
  * Support both Prince (directory) and RED (file path) styles

- Added comprehensive documentation:
  * Integration guide with testing procedures
  * Root cause analysis of missing hooks
  * Verification report with expected behavior
  * Updated migration guide
  * Multi-threading analysis

Features:
- Layer-by-layer position/force logging
- Peak force detection per layer
- Work of adhesion calculation
- Automated CSV file generation
- Compatible with existing logging_windows.csv workflow

Tested: Integration complete, ready for print testing"

echo.
echo Pushing to GitHub...
git push origin main

echo.
echo ========================================
echo Push complete!
echo ========================================
pause
