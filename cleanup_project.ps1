# Automated Cleanup Script for Prince_CurrentWorkingVersion
# Generated: October 8, 2025
# Run this to clean up test files, empty files, and archive old scripts

Write-Host "="*80
Write-Host "PRINCE PROJECT CLEANUP SCRIPT"
Write-Host "="*80
Write-Host ""

# Create a cleanup log
$logFile = "cleanup_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
function Log-Action {
    param($message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

Log-Action "Starting cleanup process..."
Log-Action "Working directory: $PWD"

# Safety check - ensure we're in the right directory
if (-not (Test-Path "Prince_Segmented.py")) {
    Write-Host "ERROR: Prince_Segmented.py not found!" -ForegroundColor Red
    Write-Host "Please run this script from the Prince_CurrentWorkingVersion directory" -ForegroundColor Red
    exit 1
}

# Ask for confirmation
Write-Host "`nThis script will:" -ForegroundColor Yellow
Write-Host "  1. Delete empty placeholder files (2 files)" -ForegroundColor Yellow
Write-Host "  2. Delete test output CSVs (3 files)" -ForegroundColor Yellow
Write-Host "  3. Archive implementation scripts (2 files)" -ForegroundColor Yellow
Write-Host "  4. Optionally archive test scripts (6 files)" -ForegroundColor Yellow
Write-Host "  5. Optionally archive experimental zip (1 file)" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Continue with cleanup? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Cleanup cancelled." -ForegroundColor Red
    exit 0
}

# Counter for actions
$filesDeleted = 0
$filesArchived = 0
$errors = 0

# ============================================================================
# STEP 1: Delete Empty Placeholder Files
# ============================================================================
Write-Host "`n[STEP 1] Deleting empty placeholder files..." -ForegroundColor Cyan

$emptyFiles = @("analysis_plotter.py", "raw_data_processor.py")
foreach ($file in $emptyFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        if ($size -eq 0) {
            try {
                Remove-Item $file -Force
                Log-Action "✓ Deleted empty file: $file"
                $filesDeleted++
            } catch {
                Log-Action "✗ Error deleting $file : $_"
                $errors++
            }
        } else {
            Log-Action "⚠ Skipped $file (not empty - $size bytes)"
        }
    } else {
        Log-Action "⚠ File not found: $file"
    }
}

# ============================================================================
# STEP 2: Delete Test Output Files
# ============================================================================
Write-Host "`n[STEP 2] Deleting test output CSV files..." -ForegroundColor Cyan

$testOutputs = @("test_output.csv", "test_peak_force_output.csv", "unified_peak_force_test.csv")
foreach ($file in $testOutputs) {
    if (Test-Path $file) {
        try {
            Remove-Item $file -Force
            Log-Action "✓ Deleted test output: $file"
            $filesDeleted++
        } catch {
            Log-Action "✗ Error deleting $file : $_"
            $errors++
        }
    } else {
        Log-Action "⚠ File not found: $file"
    }
}

# ============================================================================
# STEP 3: Archive Implementation Scripts
# ============================================================================
Write-Host "`n[STEP 3] Archiving implementation scripts..." -ForegroundColor Cyan

# Create archive directory
$implArchive = "archived_files\implementation_scripts"
if (-not (Test-Path $implArchive)) {
    try {
        New-Item -Path $implArchive -ItemType Directory -Force | Out-Null
        Log-Action "✓ Created directory: $implArchive"
    } catch {
        Log-Action "✗ Error creating directory: $_"
        $errors++
    }
}

$implScripts = @("apply_fault_recovery_fix.py", "implement_all_fixes.py")
foreach ($file in $implScripts) {
    if (Test-Path $file) {
        try {
            Move-Item $file $implArchive -Force
            Log-Action "✓ Archived: $file -> $implArchive\"
            $filesArchived++
        } catch {
            Log-Action "✗ Error archiving $file : $_"
            $errors++
        }
    } else {
        Log-Action "⚠ File not found: $file"
    }
}

# ============================================================================
# STEP 4: Archive Test Scripts (Optional)
# ============================================================================
Write-Host "`n[STEP 4] Archive test scripts?" -ForegroundColor Cyan
Write-Host "  Test scripts can be useful for debugging." -ForegroundColor Gray
Write-Host "  If you're done developing/debugging, they can be archived." -ForegroundColor Gray
$archiveTests = Read-Host "Archive test scripts? (yes/no/skip)"

if ($archiveTests -eq "yes") {
    # Create test scripts archive
    $testArchive = "archived_files\test_scripts"
    if (-not (Test-Path $testArchive)) {
        try {
            New-Item -Path $testArchive -ItemType Directory -Force | Out-Null
            Log-Action "✓ Created directory: $testArchive"
        } catch {
            Log-Action "✗ Error creating directory: $_"
            $errors++
        }
    }
    
    # Find all test_*.py files
    $testFiles = Get-ChildItem -Filter "test_*.py"
    foreach ($file in $testFiles) {
        try {
            Move-Item $file.FullName $testArchive -Force
            Log-Action "✓ Archived: $($file.Name) -> $testArchive\"
            $filesArchived++
        } catch {
            Log-Action "✗ Error archiving $($file.Name): $_"
            $errors++
        }
    }
} elseif ($archiveTests -eq "skip") {
    Log-Action "⊘ Skipped test script archiving"
} else {
    Log-Action "⊘ Kept test scripts in root directory"
}

# ============================================================================
# STEP 5: Handle Experimental Archive (Optional)
# ============================================================================
Write-Host "`n[STEP 5] Handle experimental archive?" -ForegroundColor Cyan
$expZip = "archive_experimental_compressed.zip"
if (Test-Path $expZip) {
    Write-Host "  Found: $expZip (1.38 MB)" -ForegroundColor Gray
    Write-Host "  Options:" -ForegroundColor Gray
    Write-Host "    1. Archive to archived_files/" -ForegroundColor Gray
    Write-Host "    2. Delete (if contents verified elsewhere)" -ForegroundColor Gray
    Write-Host "    3. Keep in root directory" -ForegroundColor Gray
    $expChoice = Read-Host "Choose action (1/2/3)"
    
    if ($expChoice -eq "1") {
        try {
            Move-Item $expZip "archived_files\" -Force
            Log-Action "✓ Archived: $expZip -> archived_files\"
            $filesArchived++
        } catch {
            Log-Action "✗ Error archiving $expZip : $_"
            $errors++
        }
    } elseif ($expChoice -eq "2") {
        $confirmDelete = Read-Host "⚠ Are you SURE you want to DELETE $expZip? Type 'DELETE' to confirm"
        if ($confirmDelete -eq "DELETE") {
            try {
                Remove-Item $expZip -Force
                Log-Action "✓ Deleted: $expZip"
                $filesDeleted++
            } catch {
                Log-Action "✗ Error deleting $expZip : $_"
                $errors++
            }
        } else {
            Log-Action "⊘ Deletion cancelled for $expZip"
        }
    } else {
        Log-Action "⊘ Kept $expZip in root directory"
    }
} else {
    Log-Action "⚠ File not found: $expZip"
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "`n" + "="*80 -ForegroundColor Green
Write-Host "CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "="*80 -ForegroundColor Green
Write-Host ""
Log-Action "=== CLEANUP SUMMARY ==="
Log-Action "Files deleted: $filesDeleted"
Log-Action "Files archived: $filesArchived"
Log-Action "Errors encountered: $errors"
Log-Action "Cleanup completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

Write-Host "Files deleted: $filesDeleted" -ForegroundColor Yellow
Write-Host "Files archived: $filesArchived" -ForegroundColor Yellow
Write-Host "Errors: $errors" -ForegroundColor $(if ($errors -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Cleanup log saved to: $logFile" -ForegroundColor Cyan
Write-Host ""

# Show current root directory contents
Write-Host "Current root directory files:" -ForegroundColor Cyan
Get-ChildItem -File | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

Write-Host "`nCleanup script finished!" -ForegroundColor Green
Write-Host "You can review the log at: $logFile" -ForegroundColor Gray
