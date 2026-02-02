"""
Test Runner for Prince Printing System

Runs all unit tests and generates a comprehensive report.
Supports individual test selection and verbose output.

Usage:
    python run_all_tests.py              # Run all tests
    python run_all_tests.py -v           # Verbose output
    python run_all_tests.py session      # Run only SessionManager tests
    python run_all_tests.py adhesion     # Run only AdhesionMetrics tests
    python run_all_tests.py peakforce    # Run only PeakForceLogger tests
"""

import sys
import os
import unittest
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_all_tests(verbose=False, specific_test=None):
    """
    Run all tests or specific test suite.
    
    Args:
        verbose (bool): Enable verbose output
        specific_test (str): Name of specific test to run ('session', 'adhesion', 'peakforce')
    
    Returns:
        bool: True if all tests passed
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Define test modules
    test_modules = {
        'session': 'test_session_manager',
        'adhesion': 'test_adhesion_metrics',
        'peakforce': 'test_peak_force_logger'
    }
    
    # Determine which tests to run
    if specific_test:
        if specific_test.lower() not in test_modules:
            print(f"Error: Unknown test '{specific_test}'")
            print(f"Available tests: {', '.join(test_modules.keys())}")
            return False
        
        modules_to_test = {specific_test.lower(): test_modules[specific_test.lower()]}
    else:
        modules_to_test = test_modules
    
    # Load tests
    print("=" * 70)
    print("PRINCE PRINTING SYSTEM - TEST SUITE")
    print("=" * 70)
    print(f"Loading tests from: {Path(__file__).parent}")
    print()
    
    for test_name, module_name in modules_to_test.items():
        try:
            module = __import__(module_name)
            suite.addTests(loader.loadTestsFromModule(module))
            print(f"✓ Loaded {test_name} tests from {module_name}.py")
        except ImportError as e:
            print(f"✗ Failed to load {test_name} tests: {e}")
            return False
    
    print()
    print("=" * 70)
    print(f"Running {suite.countTestCases()} tests...")
    print("=" * 70)
    print()
    
    # Run tests
    start_time = time.time()
    
    if verbose:
        runner = unittest.TextTestRunner(verbosity=2)
    else:
        runner = unittest.TextTestRunner(verbosity=1)
    
    result = runner.run(suite)
    
    # Print summary
    elapsed_time = time.time() - start_time
    
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Time: {elapsed_time:.2f} seconds")
    print("=" * 70)
    
    if result.wasSuccessful():
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        return True
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 70)
        
        if result.failures:
            print("\nFailed Tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\nTests with Errors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        print()
        return False


def print_usage():
    """Print usage information"""
    print(__doc__)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run Prince Printing System tests',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'test',
        nargs='?',
        default=None,
        help='Specific test to run (session, adhesion, peakforce)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available tests'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available test suites:")
        print("  session    - SessionManager tests")
        print("  adhesion   - AdhesionMetricsCalculator tests")
        print("  peakforce  - PeakForceLogger tests")
        print()
        print("Run all tests: python run_all_tests.py")
        print("Run specific: python run_all_tests.py session")
        return
    
    # Run tests
    success = run_all_tests(verbose=args.verbose, specific_test=args.test)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
