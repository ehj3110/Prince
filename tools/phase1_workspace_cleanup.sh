#!/usr/bin/env bash
set -euo pipefail

# Phase 1 workspace cleanup script
# - Dry-run by default
# - Deletes only exact duplicate root files (compared to canonical subfolder copies)
# - Moves generated artifacts and handoff/history docs out of root

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "============================================================"
echo "Phase 1 Workspace Cleanup"
echo "Root: $ROOT_DIR"
if [[ $APPLY -eq 1 ]]; then
  echo "Mode: APPLY (changes will be made)"
else
  echo "Mode: DRY RUN (no files will be changed)"
  echo "Tip : re-run with --apply to execute"
fi
echo "============================================================"

run_cmd() {
  if [[ $APPLY -eq 1 ]]; then
    "$@"
  else
    echo "[DRY RUN] $*"
  fi
}

ensure_dir() {
  local dir="$1"
  if [[ -d "$dir" ]]; then
    return
  fi
  echo "Create dir: $dir"
  run_cmd mkdir -p "$dir"
}

delete_root_if_exact_duplicate() {
  local root_file="$1"
  local canonical_file="$2"

  if [[ ! -e "$root_file" ]]; then
    echo "Skip delete (missing root): $root_file"
    return 0
  fi

  if [[ ! -e "$canonical_file" ]]; then
    echo "Skip delete (missing canonical): $canonical_file"
    return 0
  fi

  if cmp -s "$root_file" "$canonical_file"; then
    echo "Delete duplicate root file: $root_file"
    run_cmd rm -f "$root_file"
  else
    echo "Skip delete (content differs): $root_file != $canonical_file"
  fi
}

move_file_safe() {
  local src="$1"
  local dst="$2"

  if [[ ! -e "$src" ]]; then
    echo "Skip move (missing): $src"
    return 0
  fi

  ensure_dir "$(dirname "$dst")"

  if [[ -e "$dst" ]]; then
    echo "Skip move (destination exists): $dst"
    return 0
  fi

  echo "Move: $src -> $dst"
  run_cmd mv "$src" "$dst"
}

echo
echo "Step 1/3: Delete exact duplicate root files"

# Root tests duplicated in tests/
delete_root_if_exact_duplicate "test_adhesion_calculator_with_derivatives.py" "tests/test_adhesion_calculator_with_derivatives.py"
delete_root_if_exact_duplicate "test_data_length.py" "tests/test_data_length.py"
delete_root_if_exact_duplicate "test_extra_point.py" "tests/test_extra_point.py"
delete_root_if_exact_duplicate "test_fixed_calculator.py" "tests/test_fixed_calculator.py"
delete_root_if_exact_duplicate "test_motion_end_idx.py" "tests/test_motion_end_idx.py"
delete_root_if_exact_duplicate "test_parameter_fix.py" "tests/test_parameter_fix.py"
delete_root_if_exact_duplicate "test_path_fix.py" "tests/test_path_fix.py"
delete_root_if_exact_duplicate "test_post_print_integration.py" "tests/test_post_print_integration.py"
delete_root_if_exact_duplicate "test_print_workflow.py" "tests/test_print_workflow.py"

# Root duplicates of tools/debug files
delete_root_if_exact_duplicate "analyze_cleanup.py" "tools/analyze_cleanup.py"
delete_root_if_exact_duplicate "cleanup_comparison_files.py" "tools/cleanup_comparison_files.py"
delete_root_if_exact_duplicate "cleanup_debug_files.py" "tools/cleanup_debug_files.py"
delete_root_if_exact_duplicate "compare_time_data.py" "tools/compare_time_data.py"
delete_root_if_exact_duplicate "final_calculator_comparison.py" "debug/final_calculator_comparison.py"
delete_root_if_exact_duplicate "final_layer_visualization.py" "debug/final_layer_visualization.py"
delete_root_if_exact_duplicate "quick_workflow_test.py" "debug/quick_workflow_test.py"
delete_root_if_exact_duplicate "replicate_hybrid_plotter.py" "debug/replicate_hybrid_plotter.py"
delete_root_if_exact_duplicate "run_corrected_plotter.py" "debug/run_corrected_plotter.py"
delete_root_if_exact_duplicate "run_fixed_plotter.py" "debug/run_fixed_plotter.py"
delete_root_if_exact_duplicate "upgrade_peak_force_logger.py" "debug/upgrade_peak_force_logger.py"

echo
echo "Step 2/3: Move generated root artifacts"

ensure_dir "tests/data/fixtures"
ensure_dir "debug/plots/root_cleanup_20260325"

# CSV fixtures
move_file_safe "autolog_L48-L50.csv" "tests/data/fixtures/autolog_L48-L50.csv"
move_file_safe "autolog_L148-L150.csv" "tests/data/fixtures/autolog_L148-L150.csv"
move_file_safe "autolog_L198-L200.csv" "tests/data/fixtures/autolog_L198-L200.csv"
move_file_safe "test.csv" "tests/data/fixtures/test.csv"
move_file_safe "test_auto.csv" "tests/data/fixtures/test_auto.csv"
move_file_safe "test_default.csv" "tests/data/fixtures/test_default.csv"
move_file_safe "test_two_step_integration.csv" "tests/data/fixtures/test_two_step_integration.csv"

# PNG diagnostics
move_file_safe "dynamic_layout_test.png" "debug/plots/root_cleanup_20260325/dynamic_layout_test.png"
move_file_safe "example_plot_current_format.png" "debug/plots/root_cleanup_20260325/example_plot_current_format.png"
move_file_safe "improved_plot_format.png" "debug/plots/root_cleanup_20260325/improved_plot_format.png"
move_file_safe "position_test_output.png" "debug/plots/root_cleanup_20260325/position_test_output.png"
move_file_safe "thread_safe_test.png" "debug/plots/root_cleanup_20260325/thread_safe_test.png"

echo
echo "Step 3/3: Move root handoff/history docs"

ensure_dir "documentation/handoffs"
ensure_dir "documentation/history"

move_file_safe "MERGE_HANDOFF_FOR_GEMINI.md" "documentation/handoffs/MERGE_HANDOFF_FOR_GEMINI.md"
move_file_safe "POST_PRINT_ANALYSIS_INTEGRATION.md" "documentation/handoffs/POST_PRINT_ANALYSIS_INTEGRATION.md"

move_file_safe "ANALYSIS_RESULTS_COMPARISON.md" "documentation/history/ANALYSIS_RESULTS_COMPARISON.md"
move_file_safe "HYBRID_SYSTEM_BACKUP_MANIFEST.md" "documentation/history/HYBRID_SYSTEM_BACKUP_MANIFEST.md"
move_file_safe "HYBRID_SYSTEM_SUCCESS_REPORT.md" "documentation/history/HYBRID_SYSTEM_SUCCESS_REPORT.md"
move_file_safe "PROJECT_UPDATE_HYBRID_SYSTEM.md" "documentation/history/PROJECT_UPDATE_HYBRID_SYSTEM.md"
move_file_safe "UNIFIED_CALCULATOR_IMPLEMENTATION.md" "documentation/history/UNIFIED_CALCULATOR_IMPLEMENTATION.md"
move_file_safe "WORK_OF_ADHESION_METRICS_DEFINITIONS.md" "documentation/history/WORK_OF_ADHESION_METRICS_DEFINITIONS.md"

echo
echo "Done."
if [[ $APPLY -eq 0 ]]; then
  echo "No changes were made (dry run)."
  echo "Review output, then run: bash tools/phase1_workspace_cleanup.sh --apply"
else
  echo "Changes applied. Next recommended check: git status --short"
fi
