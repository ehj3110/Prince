# Testing Guide for Prince Printing System

## Overview

This guide describes the testing infrastructure for the Prince printing system. The test suite ensures code quality, catches regressions early, and validates new features before integration.

## Test Structure

```
tests/
├── run_all_tests.py              # Main test runner
├── test_session_manager.py       # SessionManager unit tests
├── test_adhesion_metrics.py      # AdhesionMetricsCalculator tests
├── test_peak_force_logger.py     # PeakForceLogger tests
└── README.md                     # This file (organized test info)
```

## Quick Start

### Run All Tests
```powershell
cd tests
python run_all_tests.py
```

### Run Specific Test Suite
```powershell
# Session manager tests only
python run_all_tests.py session

# Adhesion metrics tests only
python run_all_tests.py adhesion

# Peak force logger tests only
python run_all_tests.py peakforce
```

### Verbose Output
```powershell
python run_all_tests.py -v
```

### List Available Tests
```powershell
python run_all_tests.py --list
```

## Test Suites

### 1. SessionManager Tests (`test_session_manager.py`)

Tests session management functionality:
- ✓ Session log initialization and file creation
- ✓ Print numbering with existing prints
- ✓ GUI state save/load functionality
- ✓ Post-print analysis triggering
- ✓ Edge cases (empty directories, nonexistent files)

**Run:** `python run_all_tests.py session`

### 2. AdhesionMetrics Tests (`test_adhesion_metrics.py`)

Tests adhesion calculation engine:
- ✓ Force smoothing and filtering
- ✓ Peak detection algorithms
- ✓ Work of adhesion calculation
- ✓ Baseline detection
- ✓ NaN and infinite value handling
- ✓ Realistic adhesion profiles
- ✓ Edge cases (all zeros, negative forces, high noise)

**Run:** `python run_all_tests.py adhesion`

### 3. PeakForceLogger Tests (`test_peak_force_logger.py`)

Tests peak force logging system:
- ✓ Layer monitoring start/stop
- ✓ Data point buffering
- ✓ CSV output generation
- ✓ Cross-sectional area calculation
- ✓ Integration with AdhesionMetricsCalculator
- ✓ Multiple layer logging workflow
- ✓ Manual vs automated logging modes

**Run:** `python run_all_tests.py peakforce`

## Writing New Tests

### Test File Template

```python
"""
Unit tests for [ModuleName]

Tests [module] functionality including:
- Feature 1
- Feature 2
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from support_modules.[module] import [ClassName]


class Test[ClassName](unittest.TestCase):
    """Test cases for [ClassName]"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Initialize test objects
        pass
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up after tests
        pass
    
    def test_feature_name(self):
        """Test specific feature"""
        # Arrange
        # Act
        # Assert
        self.assertEqual(expected, actual)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(Test[ClassName]))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
```

### Test Naming Conventions

- **Test files:** `test_[module_name].py`
- **Test classes:** `Test[ClassName]` or `Test[ClassName][Category]`
- **Test methods:** `test_[feature_description]`

Examples:
```python
test_session_manager.py
    class TestSessionManager
        def test_initialization
        def test_init_session_log_creates_files
        def test_get_next_print_number_empty_directory
```

### Best Practices

1. **Use setUp and tearDown**
   - Initialize fixtures in `setUp()`
   - Clean up resources in `tearDown()`
   - Ensures clean state for each test

2. **Test one thing per test**
   - Each test should verify one specific behavior
   - Makes failures easier to diagnose

3. **Use descriptive test names**
   - `test_get_next_print_number_with_existing_prints` ✓
   - `test_print_num` ✗

4. **Use temporary directories**
   ```python
   import tempfile
   import shutil
   
   def setUp(self):
       self.temp_dir = tempfile.mkdtemp()
   
   def tearDown(self):
       shutil.rmtree(self.temp_dir)
   ```

5. **Mock external dependencies**
   ```python
   from unittest.mock import Mock, patch
   
   @patch('module.external_function')
   def test_with_mock(self, mock_func):
       mock_func.return_value = 'test'
       # Test code
   ```

## Integration with Development Workflow

### Before Committing Code
```powershell
# Run all tests
python tests\run_all_tests.py

# If all pass, commit
git add .
git commit -m "Feature: Added new functionality"
```

### When Adding New Features

1. **Write tests first (TDD approach)**
   ```powershell
   # Create test file
   cd tests
   # Edit test_new_feature.py
   
   # Run test (should fail initially)
   python test_new_feature.py
   
   # Implement feature
   # Run test again (should pass)
   python test_new_feature.py
   ```

2. **Or write tests alongside feature**
   - Implement feature
   - Write comprehensive tests
   - Verify all tests pass
   - Commit both feature and tests

### Continuous Testing

Run tests frequently during development:
```powershell
# Quick check after changes
python tests\run_all_tests.py session

# Full test suite before pushing
python tests\run_all_tests.py -v
```

## Test Coverage Goals

### Current Coverage (January 2026)

| Module | Coverage | Status |
|--------|----------|--------|
| SessionManager | ~80% | ✓ Good |
| AdhesionMetricsCalculator | ~70% | ✓ Good |
| PeakForceLogger | ~65% | ⚠ Needs improvement |
| ForceGaugeManager | 0% | ✗ Not tested |
| SandwichRoutines | 0% | ✗ Not tested |
| AutoHomeRoutine | 0% | ✗ Not tested |

### Future Test Additions

1. **ForceGaugeManager tests**
   - Hardware connection mocking
   - Calibration workflow
   - Data acquisition threading
   - USB coordination

2. **SandwichRoutines tests**
   - Routine initialization
   - Speed calculations
   - Tier-based movement
   - Error handling

3. **Integration tests**
   - Full print workflow simulation
   - Multi-module coordination
   - End-to-end data flow

## Troubleshooting Tests

### Import Errors
```
ModuleNotFoundError: No module named 'support_modules'
```
**Solution:** Ensure you're running from the tests directory or adjust `sys.path`

### Phidget/Hardware Errors
```
PhidgetException: Unable to connect
```
**Solution:** These are expected in tests. Mock hardware dependencies:
```python
@patch('Phidget22.Devices.VoltageRatioInput')
def test_with_mocked_hardware(self, mock_device):
    # Test code
```

### Timeout Issues
```
Test takes too long to complete
```
**Solution:** 
- Reduce data size in synthetic tests
- Mock time-consuming operations
- Use smaller buffer sizes for testing

### Test Failures After Updates

1. **Check recent changes**
   ```powershell
   git diff
   ```

2. **Run specific failing test with verbose output**
   ```powershell
   python test_session_manager.py -v
   ```

3. **Verify test expectations match new behavior**
   - If behavior changed intentionally, update test
   - If behavior changed unintentionally, fix code

## Performance Testing

For performance-critical modules, add timing tests:

```python
import time

def test_performance_fast_processing(self):
    """Ensure processing completes within time limit"""
    start = time.time()
    
    # Run operation
    result = self.module.process_data(large_dataset)
    
    elapsed = time.time() - start
    self.assertLess(elapsed, 1.0, "Processing took too long")
```

## Test Data

### Synthetic Data Generation

Create realistic test data:
```python
def generate_realistic_force_profile(n_points=500):
    """Generate realistic adhesion force profile"""
    force = np.zeros(n_points)
    force[0:100] = 0.01  # Baseline
    force[100:150] = np.linspace(0.01, 0.8, 50)  # Rising
    force[150:200] = 0.8  # Peak
    force[200:400] = np.linspace(0.8, 0.05, 200)  # Decay
    force[400:500] = 0.01  # End
    return force
```

### Using Real Data

For validation, use archived real print data:
```python
def test_with_real_data(self):
    """Test with actual print data"""
    csv_path = Path(__file__).parent / "test_post_print_data" / "real_layer.csv"
    result = self.calculator.calculate_from_csv(csv_path)
    # Verify results
```

## CI/CD Integration (Future)

When setting up automated testing:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python tests/run_all_tests.py
```

## Resources

- **Python unittest documentation:** https://docs.python.org/3/library/unittest.html
- **Mock object library:** https://docs.python.org/3/library/unittest.mock.html
- **Testing best practices:** https://realpython.com/python-testing/

## Contributing Tests

When contributing new tests:

1. Follow existing test structure
2. Include docstrings explaining what is tested
3. Test both success and failure cases
4. Add edge case tests
5. Update this README if adding new test suite
6. Ensure all tests pass before submitting PR

## Getting Help

If you need help with testing:
1. Review existing test files for examples
2. Consult this guide
3. Check Python unittest documentation
4. Ask team members for guidance

---

**Last Updated:** January 6, 2026
**Test Framework:** Python unittest
**Total Test Suites:** 3
**Total Test Cases:** 20+
