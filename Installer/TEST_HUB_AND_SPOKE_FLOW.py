#!/usr/bin/env python3
"""
Test Hub-and-Spoke Data Transfer Flow
Tests the complete employee -> central data transfer system.
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
import tempfile

# Get installation directory
installation_dir = Path(__file__).parent

# Add AI directory to path
ai_dir = installation_dir / "AI"
if ai_dir.exists() and str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

print("=" * 70)
print("HUB-AND-SPOKE DATA TRANSFER FLOW TEST")
print("=" * 70)
print()

# Test results
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def test_pass(test_name):
    """Record a passed test"""
    test_results["passed"] += 1
    print(f"[PASS] {test_name}")

def test_fail(test_name, error=None):
    """Record a failed test"""
    test_results["failed"] += 1
    error_msg = f" - {error}" if error else ""
    print(f"[FAIL] {test_name}{error_msg}")
    if error:
        test_results["errors"].append(f"{test_name}: {error}")

# Test 1: Import modules
print("TEST 1: Importing required modules...")
try:
    from monitoring.system_config import (
        configure_employee_mode,
        configure_central_mode,
        load_config,
        is_employee_computer,
        is_central_computer,
        get_central_data_path,
        get_computer_id
    )
    from monitoring.data_transfer import DataTransferManager
    from monitoring.central_data_collector import CentralDataCollector
    test_pass("Module imports")
except Exception as e:
    test_fail("Module imports", str(e))
    print("\n[ERROR] Cannot continue without required modules!")
    sys.exit(1)

# Create temporary test directories
print("\nTEST 2: Setting up test environment...")
try:
    test_base = Path(tempfile.mkdtemp(prefix="hub_spoke_test_"))
    test_employee_install = test_base / "employee_computer"
    test_central_install = test_base / "central_computer"
    test_central_data = test_base / "central_data_folder"
    
    # Create directory structure
    (test_employee_install / "AI" / "training_data").mkdir(parents=True)
    (test_employee_install / "AI" / "monitoring").mkdir(parents=True)
    (test_central_install / "AI" / "training_data").mkdir(parents=True)
    (test_central_install / "AI" / "monitoring").mkdir(parents=True)
    test_central_data.mkdir(parents=True)
    
    print(f"   Test base: {test_base}")
    print(f"   Employee install: {test_employee_install}")
    print(f"   Central install: {test_central_install}")
    print(f"   Central data folder: {test_central_data}")
    test_pass("Test environment setup")
except Exception as e:
    test_fail("Test environment setup", str(e))
    sys.exit(1)

# Test 3: Configure employee mode
print("\nTEST 3: Configuring employee mode...")
try:
    result = configure_employee_mode(
        test_employee_install,
        str(test_central_data),
        24
    )
    if result:
        config = load_config(test_employee_install)
        # Check mode and that central_data_path exists (path normalization may change format)
        config_path = Path(config.get("central_data_path", ""))
        expected_path = Path(test_central_data).resolve()
        
        if config.get("mode") == "employee" and config_path.resolve() == expected_path:
            test_pass("Employee mode configuration")
        else:
            test_fail("Employee mode configuration", 
                     f"Mode={config.get('mode')}, Path match={config_path.resolve() == expected_path}")
    else:
        test_fail("Employee mode configuration", "Function returned False")
except Exception as e:
    test_fail("Employee mode configuration", str(e))

# Test 4: Verify employee computer detection
print("\nTEST 4: Verifying employee computer detection...")
try:
    if is_employee_computer(test_employee_install):
        test_pass("Employee computer detection")
    else:
        test_fail("Employee computer detection", "Computer not detected as employee")
except Exception as e:
    test_fail("Employee computer detection", str(e))

# Test 5: Create test training data
print("\nTEST 5: Creating test training data...")
try:
    training_data_dir = test_employee_install / "AI" / "training_data"
    
    # Create sample training data files
    test_file1 = training_data_dir / "test_coordinates.json"
    test_file2 = training_data_dir / "test_browser_activity.json"
    
    test_file1.write_text(json.dumps({
        "coordinates": [{"x": 100, "y": 200, "element": "button1"}],
        "timestamp": datetime.now().isoformat()
    }))
    
    test_file2.write_text(json.dumps({
        "navigations": [{"url": "https://example.com", "timestamp": datetime.now().isoformat()}]
    }))
    
    if test_file1.exists() and test_file2.exists():
        test_pass("Test training data creation")
    else:
        test_fail("Test training data creation", "Files not created")
except Exception as e:
    test_fail("Test training data creation", str(e))

# Test 6: Test data transfer
print("\nTEST 6: Testing data transfer (employee -> central)...")
try:
    computer_id = get_computer_id(test_employee_install)
    transfer_manager = DataTransferManager(test_employee_install)
    
    # Transfer data
    transfer_stats = transfer_manager.transfer_data_to_central(
        test_central_data,
        computer_id
    )
    
    # Verify files were transferred
    computer_folder = test_central_data / computer_id
    transferred_files = list(computer_folder.glob("*.json"))
    
    if transfer_stats.get("files_transferred", 0) > 0 and len(transferred_files) > 0:
        test_pass(f"Data transfer ({transfer_stats['files_transferred']} files)")
    else:
        test_fail("Data transfer", f"Expected files transferred, got {transfer_stats}")
except Exception as e:
    test_fail("Data transfer", str(e))

# Test 7: Configure central mode
print("\nTEST 7: Configuring central mode...")
try:
    result = configure_central_mode(test_central_install)
    if result:
        config = load_config(test_central_install)
        if config.get("mode") == "central":
            # Also set central_data_path for collection
            config["central_data_path"] = str(test_central_data)
            from monitoring.system_config import save_config
            save_config(test_central_install, config)
            test_pass("Central mode configuration")
        else:
            test_fail("Central mode configuration", f"Config incorrect: {config}")
    else:
        test_fail("Central mode configuration", "Function returned False")
except Exception as e:
    test_fail("Central mode configuration", str(e))

# Test 8: Verify central computer detection
print("\nTEST 8: Verifying central computer detection...")
try:
    if is_central_computer(test_central_install):
        test_pass("Central computer detection")
    else:
        test_fail("Central computer detection", "Computer not detected as central")
except Exception as e:
    test_fail("Central computer detection", str(e))

# Test 9: Test central data collection
print("\nTEST 9: Testing central data collection...")
try:
    collector = CentralDataCollector(test_central_install, test_central_data)
    collection_stats = collector.collect_employee_data()
    
    # Verify files were collected
    central_training_dir = test_central_install / "AI" / "training_data"
    collected_files = list(central_training_dir.glob("*.json"))
    
    if collection_stats.get("files_collected", 0) > 0 and len(collected_files) > 0:
        test_pass(f"Central data collection ({collection_stats['files_collected']} files)")
    else:
        test_fail("Central data collection", f"Expected files collected, got {collection_stats}")
except Exception as e:
    test_fail("Central data collection", str(e))

# Test 10: Verify data cleanup integration
print("\nTEST 10: Testing data cleanup integration...")
try:
    from monitoring.data_cleanup import DataCleanupManager
    
    # Test employee mode cleanup
    employee_cleanup = DataCleanupManager(test_employee_install)
    if is_employee_computer(test_employee_install):
        stats = employee_cleanup.cleanup_all()
        if "files_transferred" in stats:
            test_pass("Employee mode cleanup integration")
        else:
            test_fail("Employee mode cleanup integration", "Transfer stats missing")
    
    # Test central mode cleanup
    central_cleanup = DataCleanupManager(test_central_install)
    if is_central_computer(test_central_install):
        stats = central_cleanup.cleanup_all()
        test_pass("Central mode cleanup integration")
except Exception as e:
    test_fail("Cleanup integration", str(e))

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"[OK] Passed: {test_results['passed']}")
print(f"[FAIL] Failed: {test_results['failed']}")
print()

if test_results['failed'] > 0:
    print("FAILED TESTS:")
    for error in test_results['errors']:
        print(f"  • {error}")
    print()

# Cleanup
print("Cleaning up test environment...")
try:
    shutil.rmtree(test_base)
    print(f"   Removed: {test_base}")
except Exception as e:
    print(f"   [WARNING] Could not remove test directory: {e}")
    print(f"   Manual cleanup needed: {test_base}")

print()
if test_results['failed'] == 0:
    print("[SUCCESS] ALL TESTS PASSED! Hub-and-spoke system is working correctly.")
    sys.exit(0)
else:
    print("[ERROR] SOME TESTS FAILED. Review errors above.")
    sys.exit(1)

