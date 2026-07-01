# Test Scripts

This directory contains test scripts and unit tests for the Prince printing system.

## Unit Tests (NEW - January 2026)

Comprehensive unit test suite using Python's unittest framework:

### Test Runner
- **run_all_tests.py** - Main test runner for all unit tests
  - Run all: `python run_all_tests.py`
  - Run specific: `python run_all_tests.py session`
  - Verbose: `python run_all_tests.py -v`

### Unit Test Files
- **test_session_manager.py** - SessionManager unit tests (20+ test cases)
  - Session log initialization
  - Print numbering logic
  - GUI state save/load
  - Post-print analysis triggering

- **test_adhesion_metrics.py** - AdhesionMetricsCalculator tests (15+ test cases)
  - Force smoothing and filtering
  - Peak detection algorithms
  - Work of adhesion calculation
  - Edge cases (NaN, negative values, noise)

- **test_peak_force_logger.py** - PeakForceLogger tests (12+ test cases)
  - Layer monitoring workflow
  - Data buffering and CSV output
  - Cross-sectional area calculation
  - Multi-layer integration tests

### Testing Guide
- **TESTING_GUIDE.md** - Comprehensive testing documentation
  - Quick start guide
  - Writing new tests
  - Best practices
  - CI/CD integration

## Integration Test Scripts

Legacy test scripts for hardware and workflow testing:

### Hardware Tests
- **test_dlp_simple.py** - Basic DLP projector functionality test
- **test_dlp_visibility.py** - DLP visibility and pattern display test
- **test_force_sensing_hardware.py** - Force gauge hardware test (in RED_PotentialUpgradeScript/)

### Integration Tests
- **test_sandwich_integration.py** - Sandwich routine integration test
- **test_sandwich_with_precal.py** - Sandwich routine with pre-calibration test
- **test_derivative_sandwich.py** - Derivative-based sandwich routine test
- **test_printing_workflow_complete.py** - Complete printing workflow test

### Data & Analysis Tests
- **test_csv_output_quick.py** - CSV output functionality test
- **test_water_loss_plot.py** - Water loss plotting test

### Calibration Tests (in calibration_modules/)
- **test_pattern_generation.py** - Pattern generation test
- **test_dlp_pattern_display.py** - DLP pattern display test
- **test_camera.py** - Camera calibration test

## Quick Start

### Run Unit Tests
```powershell
cd tests
python run_all_tests.py
```

### Run Specific Test Suite
```powershell
python run_all_tests.py session      # SessionManager tests
python run_all_tests.py adhesion     # AdhesionMetrics tests
python run_all_tests.py peakforce    # PeakForceLogger tests
```

### Run Legacy Integration Tests
```powershell
python test_dlp_simple.py
python test_sandwich_integration.py
```

## Requirements

### Unit Tests
- Python 3.7+
- numpy
- opencv-python (cv2)
- scipy
- pandas

### Integration Tests
Some tests may require:
- Hardware connections (DLP projector, force gauge, Zaber stage)
- Calibration data files
- Configuration files (prince_settings.json)

## Test Coverage (January 2026)

| Module | Unit Tests | Status |
|--------|-----------|--------|
| SessionManager | ✓ Yes | 20+ tests |
| AdhesionMetricsCalculator | ✓ Yes | 15+ tests |
| PeakForceLogger | ✓ Yes | 12+ tests |
| ForceGaugeManager | ✗ No | Future work |
| SandwichRoutines | ✗ No | Future work |
| AutoHomeRoutine | ✗ No | Future work |

## Development Workflow

1. **Before committing code:**
   ```powershell
   python tests\run_all_tests.py
   ```

2. **When adding new features:**
   - Write unit tests for new functionality
   - Ensure all tests pass
   - Commit code and tests together

3. **Test-Driven Development (TDD):**
   - Write test first (it should fail)
   - Implement feature
   - Run test (it should pass)
   - Refactor if needed

See **TESTING_GUIDE.md** for detailed documentation.

## Note

Test organization was improved during the January 2026 cleanup. Legacy test scripts were moved from root directory, and new unit test infrastructure was added to support rapid development and validation.
