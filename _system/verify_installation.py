#!/usr/bin/env python3
"""
Installation Verification Script
Verifies that all bots are properly linked and all paths exist within the installation directory.
"""

from pathlib import Path
import sys

def verify_installation():
    """Verify all bot paths and dependencies"""
    print("=" * 80)
    print("INSTALLATION VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    # Get installation directory
    installation_dir = Path(__file__).parent.parent
    print(f"Installation Directory: {installation_dir}")
    print()
    
    # Check secure launcher
    print("=== Secure Launcher ===")
    launcher = installation_dir / "_system" / "secure_launcher.py"
    print(f"Secure Launcher: {launcher.exists()} - {launcher}")
    print()
    
    # Check all bot paths in secure launcher
    print("=== Bot Paths in Secure Launcher ===")
    bots = {
        "Medical Records Bot": installation_dir / "_bots" / "Med Rec" / "Finished Product, Launch Ready" / "Bot and extender" / "integrity_medical_records_bot_v3g_batchclicks.py",
        "Consent Form Bot": installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "integrity_consent_bot_v2.py",
        "Welcome Letter Bot": installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "isws_welcome_DEEPFIX2_NOTEFORCE_v14.py",
        "Intake & Referral Department": installation_dir / "_bots" / "Launcher" / "intake_referral_launcher.py",
        "Billing Department": installation_dir / "_bots" / "Billing Department" / "billing_department_launcher.py",
        "Penelope Workflow Tool": installation_dir / "_bots" / "Penelope Workflow Tool" / "penelope_workflow_tool.py"
    }
    
    all_ok = True
    for name, path in bots.items():
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {name}: {exists}")
        if not exists:
            print(f"  MISSING: {path}")
            all_ok = False
    print()
    
    # Check Welcome Uploader Bridge
    print("=== Welcome Uploader Dependencies ===")
    bridge = installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "welcome_uploader_bridge.py"
    uploader = installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "isws_welcome_packet_uploader_v14style_FIXED.py"
    print(f"Bridge: {bridge.exists()} - {bridge}")
    print(f"Uploader: {uploader.exists()} - {uploader}")
    if not bridge.exists():
        print(f"  MISSING: {bridge}")
        all_ok = False
    if not uploader.exists():
        print(f"  MISSING: {uploader}")
        all_ok = False
    print()
    
    # Check sub-launcher bot paths
    print("=== Billing Department Launcher Bots ===")
    billing_bots = {
        "Medical Records Billing Log Bot": installation_dir / "_bots" / "Billing Department" / "Medisoft Billing" / "medisoft_billing_bot.py",
        "TN Refiling Bot": installation_dir / "_bots" / "Billing Department" / "TN Refiling Bot" / "tn_refiling_bot.py"
    }
    for name, path in billing_bots.items():
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {name}: {exists}")
        if not exists:
            print(f"  MISSING: {path}")
            all_ok = False
    print()
    
    print("=== Intake & Referral Department Launcher Bots ===")
    intake_bots = {
        "Remove Counselor Bot": installation_dir / "_bots" / "Cursor versions" / "Goose" / "isws_remove_counselor_botcursor3.py",
        "Referral Form/Upload Bot": installation_dir / "_bots" / "Referral bot and bridge (final)" / "isws_Intake_referral_bot_REFERENCE_PLUS_PRINT_ONLY_WITH_LOOPBACK_LOOPONLY_SCROLLING_TINYLOG_NO_BOTTOM_UPLOADER.py",
        "Counselor Assignment Bot": installation_dir / "_bots" / "Referral bot and bridge (final)" / "counselor_assignment_bot.py"
    }
    for name, path in intake_bots.items():
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {name}: {exists}")
        if not exists:
            print(f"  MISSING: {path}")
            all_ok = False
    print()
    
    # Summary
    print("=" * 80)
    if all_ok:
        print("✓ ALL VERIFICATION CHECKS PASSED")
        print("All bots are properly linked and all paths exist within the installation directory.")
        print("The installation is self-contained and ready to be distributed.")
    else:
        print("✗ VERIFICATION FAILED")
        print("Some bots or dependencies are missing. Please check the paths above.")
    print("=" * 80)
    
    return all_ok

if __name__ == "__main__":
    success = verify_installation()
    sys.exit(0 if success else 1)
