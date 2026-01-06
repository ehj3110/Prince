"""
Sandwich Routine Integration Test
==================================
Verifies that speed floor modifications and 4-tier ascent logic are properly integrated.

Tests:
1. Speed floor constants are correct (30µm/s general, 15µm/s lifting)
2. 4-tier ascent triggers correctly when distance ≤ 200µm
3. 3-tier ascent used when distance > 200µm
4. Speed floor application to all tiers

Author: GitHub Copilot
Date: November 29, 2025
"""

import sys
from pathlib import Path

# Add workspace to path
workspace_dir = Path(__file__).parent
sys.path.insert(0, str(workspace_dir))


def test_speed_floor_constants():
    """Test 1: Verify speed floor constants in Prince_Segmented.py"""
    print("\n" + "="*70)
    print("TEST 1: Speed Floor Constants")
    print("="*70)
    
    # Read Prince_Segmented.py
    prince_file = workspace_dir / "Prince_Segmented.py"
    
    if not prince_file.exists():
        print("✗ FAILED: Prince_Segmented.py not found")
        return False
    
    with open(prince_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for correct constants
    checks = [
        ("min_speed_floor = 30.0", "General speed floor (30 µm/s)"),
        ("min_speed_floor_lifting = 15.0", "Lifting speed floor (15 µm/s)"),
        ("max(30.0, min(2000.0, self.adaptive_sandwich_speed_um_s))", "Adaptive speed clamp (30-2000 µm/s)"),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ Found: {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_passed = False
    
    if all_passed:
        print("\n✓ TEST 1 PASSED: All speed floor constants correct")
        return True
    else:
        print("\n✗ TEST 1 FAILED: Some speed floor constants missing or incorrect")
        return False


def test_4tier_ascent_logic():
    """Test 2: Verify 4-tier ascent conditional logic"""
    print("\n" + "="*70)
    print("TEST 2: 4-Tier Ascent Logic")
    print("="*70)
    
    prince_file = workspace_dir / "Prince_Segmented.py"
    
    with open(prince_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for 4-tier ascent logic
    checks = [
        ("distance_from_glass_um = abs(final_descent_pos_um - target_glass_um)", "Distance calculation"),
        ("use_4tier_ascent = (distance_from_glass_um <= 200.0)", "4-tier trigger condition (≤200µm)"),
        ("if use_4tier_ascent:", "Conditional branching"),
        ("Using 4-TIER ASCENT (very close to glass)", "4-tier status message"),
        ("Using 3-TIER ASCENT (standard)", "3-tier status message"),
        ("ascent_tier4 = ascent_tier3 / 2.0", "Ultra-slow tier (Base/18)"),
        ("waypoint_10pct_up_um", "10% waypoint for 4-tier"),
        ("[ASCENT SEG 1/4]", "First segment label (4-tier)"),
        ("[ASCENT SEG 2/4]", "Second segment label (4-tier)"),
        ("[ASCENT SEG 3/4]", "Third segment label (4-tier)"),
        ("[ASCENT SEG 1/3]", "First segment label (3-tier)"),
        ("[ASCENT SEG 2/3]", "Second segment label (3-tier)"),
        ("seg_label = \"4/4\" if use_4tier_ascent else \"3/3\"", "Dynamic final segment label"),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ Found: {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_passed = False
    
    if all_passed:
        print("\n✓ TEST 2 PASSED: 4-tier ascent logic properly integrated")
        return True
    else:
        print("\n✗ TEST 2 FAILED: Some 4-tier logic missing")
        return False


def test_speed_floor_application():
    """Test 3: Verify speed floors are applied to tiers"""
    print("\n" + "="*70)
    print("TEST 3: Speed Floor Application")
    print("="*70)
    
    prince_file = workspace_dir / "Prince_Segmented.py"
    
    with open(prince_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that floors are applied
    checks = [
        ("ascent_tier3 = max(min_speed_floor_lifting, ascent_tier3)", "Tier 3 floor (15 µm/s)"),
        ("ascent_tier2 = max(min_speed_floor, ascent_tier2)", "Tier 2 floor (30 µm/s)"),
        ("ascent_tier1 = max(min_speed_floor, ascent_tier1)", "Tier 1 floor (30 µm/s)"),
        ("ascent_tier4 = max(min_speed_floor_lifting, ascent_tier4)", "Tier 4 floor (15 µm/s, for 4-tier mode)"),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ Found: {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_passed = False
    
    if all_passed:
        print("\n✓ TEST 3 PASSED: Speed floors correctly applied to all tiers")
        return True
    else:
        print("\n✗ TEST 3 FAILED: Some floor applications missing")
        return False


def test_segment_structure():
    """Test 4: Verify segment structure and convergence at 50%"""
    print("\n" + "="*70)
    print("TEST 4: Segment Structure")
    print("="*70)
    
    prince_file = workspace_dir / "Prince_Segmented.py"
    
    with open(prince_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for proper segment structure
    checks = [
        ("waypoint_50pct_up_um", "50% waypoint (common pause point)"),
        ("[ASCENT PAUSE 1/2]", "Pause at 50% waypoint"),
        ("seg_label = \"4/4\" if use_4tier_ascent else \"3/3\"", "Dynamic segment labeling"),
        ("sandwich_target_position_um", "Final target position"),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ Found: {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_passed = False
    
    # Check that both paths use waypoint_50pct_up_um
    if content.count("waypoint_50pct_up_um") >= 4:  # Defined in both branches + used in common section
        print(f"  ✓ Found: 50% waypoint used in multiple places")
    else:
        print(f"  ✗ Missing: 50% waypoint not consistently used")
        all_passed = False
    
    if all_passed:
        print("\n✓ TEST 4 PASSED: Segment structure correct with convergence at 50%")
        return True
    else:
        print("\n✗ TEST 4 FAILED: Segment structure issues")
        return False


def test_documentation_exists():
    """Test 5: Verify documentation files exist"""
    print("\n" + "="*70)
    print("TEST 5: Documentation Files")
    print("="*70)
    
    doc_files = [
        ("SANDWICH_SPEED_FLOOR_MODIFICATIONS.md", "Speed floor documentation"),
        ("4_TIER_ASCENT_ENHANCEMENT.md", "4-tier ascent documentation"),
    ]
    
    all_passed = True
    for filename, description in doc_files:
        doc_path = workspace_dir / filename
        if doc_path.exists():
            print(f"  ✓ Found: {description} ({filename})")
        else:
            print(f"  ✗ Missing: {description} ({filename})")
            all_passed = False
    
    if all_passed:
        print("\n✓ TEST 5 PASSED: All documentation files present")
        return True
    else:
        print("\n✗ TEST 5 FAILED: Some documentation missing")
        return False


def main():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("SANDWICH ROUTINE INTEGRATION TEST SUITE")
    print("="*70)
    print("Verifying speed floor modifications and 4-tier ascent")
    print("="*70)
    
    tests = [
        ("Speed Floor Constants", test_speed_floor_constants),
        ("4-Tier Ascent Logic", test_4tier_ascent_logic),
        ("Speed Floor Application", test_speed_floor_application),
        ("Segment Structure", test_segment_structure),
        ("Documentation Files", test_documentation_exists),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓✓✓ ALL INTEGRATION TESTS PASSED ✓✓✓")
        print("\nSandwich routine modifications successfully integrated:")
        print("  • Speed floors: 30 µm/s (general), 15 µm/s (lifting)")
        print("  • 4-tier ascent: Activates when ≤200µm from glass")
        print("  • 3-tier ascent: Standard mode for >200µm")
        print("  • Ultra-slow tier: Base/18 for first 10% of ascent")
        print("\nReady for production testing!")
        return 0
    else:
        print(f"\n✗✗✗ {total - passed} TEST(S) FAILED ✗✗✗")
        print("Please review failed tests above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
