#!/usr/bin/env python3
"""
CCMD Bot Installation Script - Employee Version
Creates desktop shortcut with proper icon and error handling
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    print("=" * 60)
    print("CCMD Bot Installation - Employee Setup")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ ERROR: Python 3.8 or higher is required!")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def install_requirements():
    """Install Python packages from requirements.txt and enterprise requirements"""
    print("\n📦 Installing required Python packages...")
    
    # This script is now in Installer folder, so get installation root (parent of Installer)
    installer_dir = Path(__file__).parent
    installation_dir = installer_dir.parent
    system_dir = installation_dir / "_system"
    bots_dir = installation_dir / "_bots"
    
    # Upgrade pip first
    print("   Upgrading pip to latest version...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", 
            "pip", "--no-warn-script-location"
        ], timeout=300)
    except:
        pass  # Continue even if pip upgrade fails
    
    # CRITICAL: Install NumPy with --only-binary FIRST to prevent compilation errors
    # NumPy is a dependency for many packages and needs pre-built wheels (especially on Python 3.14+)
    print("   Installing NumPy (critical dependency - using pre-built wheels)...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
            "--no-warn-script-location", "--only-binary", ":all:", "numpy>=1.24.0"
        ], timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("   ✅ NumPy installed successfully")
    except:
        # Fallback: try without --only-binary (for older Python versions that might have wheels)
        try:
            print("   Retrying NumPy installation (fallback method)...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                "--no-warn-script-location", "numpy>=1.24.0"
            ], timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("   ✅ NumPy installed successfully (fallback)")
        except:
            print("   ⚠️  NumPy installation failed - some packages may fail later")
    
    # Install standard requirements
    requirements_file = system_dir / "requirements.txt"
    if requirements_file.exists():
        print("   Installing standard dependencies...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                "--no-warn-script-location", "-r", str(requirements_file)
            ], timeout=600)
            print("   ✅ Standard packages installed")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Some standard packages may not have installed: {e}")
        except subprocess.TimeoutExpired:
            print("   ⚠️  Installation timeout, but continuing...")
    
    # Install enterprise requirements (including AI monitoring)
    enterprise_requirements = system_dir / "requirements_enterprise.txt"
    if enterprise_requirements.exists():
        print("   Installing enterprise AI dependencies...")
        try:
            # Use --only-binary :all: for packages that might need compilation
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                "--no-warn-script-location", "--only-binary", ":all:",
                "-r", str(enterprise_requirements)
            ], timeout=600)
            print("   ✅ Enterprise packages installed")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Some enterprise packages may not have installed: {e}")
            # Try without --only-binary for packages that need it
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                    "--no-warn-script-location", "-r", str(enterprise_requirements)
                ], timeout=600)
                print("   ✅ Enterprise packages installed (retry successful)")
            except:
                print("   ⚠️  Some enterprise packages may be missing")
        except subprocess.TimeoutExpired:
            print("   ⚠️  Installation timeout, but continuing...")
    
    # Install bot-specific requirements files
    install_bot_requirements(bots_dir, installation_dir)

    # Install critical packages individually if needed (ensures core dependencies are installed)
    critical_packages = [
        # Core desktop automation (REQUIRED for Medisoft and other desktop bots)
        "pyautogui>=0.9.54",
        "pywinauto>=0.6.8",
        "keyboard>=0.13.5",  # F8/F9 hotkeys for training
        "opencv-python>=4.11.0",  # Image recognition with confidence matching
        # Core data processing
        "cryptography>=41.0.0",
        "selenium>=4.0.0",  # Legacy - kept for backward compatibility
        "webdriver-manager>=4.0.0",  # Legacy - kept for backward compatibility
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",  # Excel file reading
        "pillow>=10.0.0",
        "pyperclip>=1.8.2",  # Clipboard operations
        # Modern web automation (3-5x faster than Selenium!)
        "playwright>=1.40.0",  # Modern web automation - MUCH faster
        # Modern data processing (10-100x faster than pandas for large datasets)
        "polars>=0.19.0",  # Modern, fast data processing
        # Modern logging (one-line setup, auto-rotation)
        "loguru>=0.7.2",  # Much easier than standard logging
        # Modern data validation
        "pydantic>=2.5.0",  # Automatic data validation and type safety
        # PDF creation and manipulation libraries (for Welcome Letter Bot and other PDF generation)
        "PyPDF2>=3.0.0",
        "reportlab>=4.0.0",
        "fpdf2>=2.7.0",
        # PDF reading/parsing libraries
        "pdfplumber>=0.11.0",
        "pdf2image>=1.17.0",
        "pytesseract>=0.3.13",
        # Windows COM for desktop shortcuts
        "pywin32>=306",  # Required for proper icon handling on Windows
    ]
    
    print("   Installing critical packages...")
    for package in critical_packages:
        try:
            # Special handling for packages that need --only-binary to prevent compilation
            if "opencv-python" in package or "numpy" in package:
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                        "--no-warn-script-location", "--only-binary", ":all:", package
                    ], timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    # Fallback: try without --only-binary
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                        "--no-warn-script-location", package
                    ], timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                    "--no-warn-script-location", package
                ], timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass  # Continue even if individual package fails
    
    print("✅ Package installation completed")
    
    # Install Playwright browsers (required after installing playwright package)
    print("\n🌐 Installing Playwright browsers...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], timeout=300)
        print("   ✅ Playwright Chromium browser installed")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Playwright browser installation failed: {e}")
        print("   You may need to run 'playwright install chromium' manually")
    except subprocess.TimeoutExpired:
        print("   ⚠️  Playwright browser installation timed out")
        print("   You may need to run 'playwright install chromium' manually")
    except FileNotFoundError:
        print("   ⚠️  Playwright not found - skipping browser installation")
        print("   This is OK if Playwright wasn't installed")
    
    return True


def install_bot_requirements(bots_dir: Path, installation_dir: Path) -> None:
    """Install requirements.txt files located under each bot directory."""
    if not bots_dir.exists():
        print("   ⚠️  _bots directory not found - skipping bot dependency install")
        return

    requirement_files = sorted({req.resolve() for req in bots_dir.rglob("requirements.txt")})

    if not requirement_files:
        print("   ⚠️  No bot requirements.txt files found")
        return

    print("\n   Installing bot-specific dependencies...")

    for req_file in requirement_files:
        # Skip the main system requirements file if it lives under _bots by mistake
        try:
            relative_path = req_file.relative_to(installation_dir)
        except ValueError:
            relative_path = req_file

        print(f"      • {relative_path}")
        try:
            # Try with --only-binary first to prevent NumPy compilation errors
            try:
                subprocess.check_call([
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--upgrade",
                    "--no-warn-script-location",
                    "--only-binary", ":all:",
                    "-r",
                    str(req_file)
                ], timeout=600, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                # Fallback: try without --only-binary if that fails
                subprocess.check_call([
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--upgrade",
                    "--no-warn-script-location",
                    "-r",
                    str(req_file)
                ], timeout=600)
        except subprocess.TimeoutExpired:
            print("        ⚠️  Installation timed out, continuing...")
        except subprocess.CalledProcessError as e:
            print(f"        ⚠️  Failed to install dependencies from {relative_path}: {e}")
        except Exception as e:
            print(f"        ⚠️  Unexpected error installing {relative_path}: {e}")

def create_desktop_shortcut():
    """Create desktop shortcut to the launcher with proper icon"""
    print("\n🔗 Creating desktop shortcut...")
    
    # This script is now in Installer folder, so get installation root (parent of Installer)
    install_dir = Path(__file__).parent.parent
    system_dir = install_dir / "_system"
    launcher_path = system_dir / "secure_launcher.py"
    vbs_launcher = system_dir / "launch_automation_hub.vbs"
    icon_path = system_dir / "ccmd_bot_icon.ico"
    
    if not launcher_path.exists():
        print(f"❌ Launcher not found at: {launcher_path}")
        return False
    
    # Verify icon file exists and is accessible - try multiple locations (universal search)
    icon_found = False
    if icon_path.exists():
        icon_found = True
        print(f"   ✓ Icon found at primary location: {icon_path}")
    else:
        print(f"   Searching for icon file in multiple locations...")
        # Try alternative locations in order of preference (universal search)
        alt_icon_paths = [
            system_dir / "ccmd_bot_icon.ico",  # Primary location
            system_dir / "ccmd_bot_icon.png",  # PNG version in _system
            system_dir / "master_ai_robot.ico",  # Alternative in _system
            install_dir / "_admin" / "ccmd_bot_icon.ico",  # Alternative in _admin
            install_dir / "_admin" / "ccmd_bot_icon.png",  # PNG version in _admin
            install_dir / "Installer" / "ccmd_bot_icon.ico",  # In Installer folder
            install_dir / "Installer" / "ccmd_bot_icon.png",  # PNG in Installer
            install_dir / "Installer" / "medisoft_bot_icon.ico",  # Legacy name
            install_dir / "Installer" / "medisoft_bot_icon.png",  # Legacy PNG
            install_dir / "Installer" / "icon.ico",  # Generic name
            # Search recursively for any .ico file with "icon" or "bot" in name
        ]
        
        # Also search for any .ico files in common locations
        search_dirs = [system_dir, install_dir / "_admin", install_dir / "Installer"]
        for search_dir in search_dirs:
            if search_dir.exists():
                try:
                    # Look for any .ico files
                    ico_files = list(search_dir.glob("*.ico"))
                    if ico_files:
                        # Prefer files with "icon", "bot", or "ccmd" in name
                        for ico_file in ico_files:
                            name_lower = ico_file.name.lower()
                            if any(keyword in name_lower for keyword in ["icon", "bot", "ccmd", "automation"]):
                                alt_icon_paths.append(ico_file)
                                break
                except:
                    pass
        
        for alt_path in alt_icon_paths:
            try:
                if alt_path.exists() and alt_path.is_file():
                    print(f"   ✓ Found icon at: {alt_path}")
                    icon_path = alt_path
                    icon_found = True
                    break
            except:
                continue
    
    if not icon_found:
        print("   ⚠️  No icon file found - shortcut will use default icon")
        print("   (This is OK - shortcut will still work, just without custom icon)")
        icon_path = None
    else:
        # Ensure icon path is absolute and accessible
        icon_path = icon_path.resolve()
        if not icon_path.exists():
            print(f"   ⚠️  Icon path resolved but file not accessible: {icon_path}")
            icon_path = None
        else:
            # If it's a PNG, try to convert to ICO (Windows prefers ICO for shortcuts)
            if icon_path.suffix.lower() == '.png':
                try:
                    from PIL import Image
                    ico_path = icon_path.with_suffix('.ico')
                    if not ico_path.exists():
                        print(f"   Converting PNG to ICO format...")
                        img = Image.open(icon_path)
                        # Resize to common icon sizes if needed
                        if img.size[0] > 256 or img.size[1] > 256:
                            img = img.resize((256, 256), Image.Resampling.LANCZOS)
                        img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                        print(f"   ✓ Converted PNG to ICO: {ico_path}")
                        icon_path = ico_path
                    else:
                        print(f"   ✓ ICO version already exists: {ico_path}")
                        icon_path = ico_path
                except ImportError:
                    print(f"   ⚠️  PIL/Pillow not available - using PNG as-is (may not display correctly)")
                except Exception as e:
                    print(f"   ⚠️  Could not convert PNG to ICO: {e} - using PNG as-is")
            
            print(f"   ✓ Icon file verified: {icon_path}")
    
    # Get desktop path
    desktop = Path.home() / "Desktop"
    
    if platform.system() == "Windows":
        # Method 1: Try using win32com (most reliable for icons)
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            desktop_path = shell.SpecialFolders("Desktop")
            shortcut_path = os.path.join(desktop_path, "Automation Hub.lnk")
            shortcut = shell.CreateShortCut(shortcut_path)
            
            # Use VBS launcher if available, otherwise Python launcher
            if vbs_launcher.exists():
                shortcut.TargetPath = str(vbs_launcher.resolve())
            else:
                shortcut.TargetPath = sys.executable
                shortcut.Arguments = f'"{launcher_path}"'
            
            shortcut.WorkingDirectory = str(system_dir.resolve())
            shortcut.Description = "Automation Hub - Enterprise Bot Launcher"
            shortcut.WindowStyle = 1  # Minimized (no console)
            
            # Set icon with absolute path (include ",0" for icon index)
            if icon_path and icon_path.exists():
                abs_icon_path = str(icon_path.resolve())
                # Ensure path uses backslashes for Windows (required for IconLocation)
                abs_icon_path = abs_icon_path.replace('/', '\\')
                # Verify file is accessible before setting
                if os.path.exists(abs_icon_path) and os.access(abs_icon_path, os.R_OK):
                    print(f"🎯 Setting custom icon: {abs_icon_path}")
                    try:
                        # Use absolute path with icon index 0
                        shortcut.IconLocation = f"{abs_icon_path},0"
                        # Force save to apply icon immediately
                        shortcut.save()
                        # Verify icon was set (reload shortcut)
                        shortcut = shell.CreateShortCut(shortcut_path)
                        if shortcut.IconLocation and abs_icon_path.lower() in shortcut.IconLocation.lower():
                            print(f"   ✓ Icon successfully set!")
                        else:
                            # Icon might still work, just not verified - continue (don't fail)
                            print(f"   ⚠️  Icon set but verification unclear (may still work)")
                    except Exception as e:
                        print(f"⚠️  Error setting icon via win32com: {e}")
                        print(f"   Will try VBScript method instead...")
                        raise  # Re-raise to fall through to VBScript method
                else:
                    print(f"⚠️  Icon file not accessible: {abs_icon_path}")
                    print("   Using Python default icon instead")
                    shortcut.IconLocation = f"{sys.executable},0"
            else:
                print("⚠️  Custom icon not found, using Python default")
                shortcut.IconLocation = f"{sys.executable},0"
            
            shortcut.save()
            print(f"✅ Desktop shortcut created: Automation Hub")
            print(f"   Location: {shortcut_path}")
            if icon_path and icon_path.exists():
                print(f"   Icon: {str(icon_path.resolve())}")
            else:
                print(f"   Icon: Default (Python)")
            return True
        except ImportError:
            print("📝 win32com not available, using VBScript method...")
        except Exception as e:
            print(f"⚠️  win32com method failed: {e}, trying VBScript...")
        
        # Method 2: Use VBScript (works reliably)
        print("📝 Creating shortcut using VBScript...")
        vbs_path = system_dir / "create_employee_shortcut.vbs"
        shortcut_target = str(desktop / "Automation Hub.lnk")
        
        # Get absolute paths - ensure they use backslashes for Windows
        abs_install_dir = str(install_dir.resolve()).replace('/', '\\')
        abs_system_dir = str(system_dir.resolve()).replace('/', '\\')
        abs_launcher = str(launcher_path.resolve()).replace('/', '\\')
        abs_vbs_launcher = str(vbs_launcher.resolve()).replace('/', '\\') if vbs_launcher.exists() else ""
        abs_icon = str(icon_path.resolve()).replace('/', '\\') if icon_path and icon_path.exists() else ""
        abs_python_exe = str(sys.executable).replace('/', '\\')
        
        # Create VBScript to make the shortcut
        vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get desktop path
desktopPath = oWS.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\\Automation Hub.lnk"

' Create shortcut
Set oLink = oWS.CreateShortcut(shortcutPath)

' Use VBS launcher if available, otherwise Python launcher
If fso.FileExists("{abs_vbs_launcher}") Then
    oLink.TargetPath = "{abs_vbs_launcher}"
Else
    oLink.TargetPath = "{abs_python_exe}"
    oLink.Arguments = """{abs_launcher}"""
End If

oLink.WorkingDirectory = """{abs_system_dir}"""
oLink.Description = "Automation Hub - Enterprise Bot Launcher"
oLink.WindowStyle = 1

' Set icon with absolute path - verify file exists and is accessible first
If "{abs_icon}" <> "" And fso.FileExists("{abs_icon}") Then
    ' Verify file is readable
    Set iconFile = fso.GetFile("{abs_icon}")
    If Not iconFile Is Nothing Then
        oLink.IconLocation = """{abs_icon},0"""
        WScript.Echo "Icon set to: {abs_icon}"
    Else
        oLink.IconLocation = """{abs_python_exe},0"""
        WScript.Echo "Icon file not accessible, using default"
    End If
Else
    oLink.IconLocation = """{abs_python_exe},0"""
    WScript.Echo "Icon file not found, using default"
End If

oLink.Save
WScript.Echo "Shortcut created successfully with icon!"
'''
        
        # Write and execute VBScript
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_content)
        
        try:
            result = subprocess.run(['cscript', '//nologo', str(vbs_path)], 
                                  check=True, capture_output=True, text=True, timeout=10)
            vbs_path.unlink()  # Delete VBS file after use
            print(f"✅ Desktop shortcut created: Automation Hub")
            print(f"   Location: {shortcut_target}")
            if icon_path and icon_path.exists():
                print(f"   Icon: {abs_icon}")
                # Verify icon is accessible
                if not os.path.exists(abs_icon):
                    print(f"   ⚠️  WARNING: Icon file may not be accessible at: {abs_icon}")
                    print(f"   The shortcut may show a default icon instead.")
            else:
                print(f"   Icon: Default (Python)")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ VBScript failed: {e}")
            if e.stdout:
                print(f"   Output: {e.stdout}")
            if e.stderr:
                print(f"   Error: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Error creating shortcut: {e}")
            return False
    else:
        # Linux/Mac - create shell script
        shortcut_path = desktop / "CCMD Automation Hub.sh"
        with open(shortcut_path, 'w') as f:
            f.write(f'#!/bin/bash\n')
            f.write(f'cd "{install_dir}"\n')
            f.write(f'python3 "{launcher_path}"\n')
        os.chmod(shortcut_path, 0o755)
        print(f"✅ Desktop shortcut created: Automation Hub.sh")
        return True

def create_bat_wrappers():
    """Create batch file wrappers for all bots"""
    print("\n📝 Creating batch wrappers for bots...")
    
    install_dir = Path(__file__).parent.parent
    create_bat_script = install_dir / "_system" / "create_bat_wrappers.py"
    
    if not create_bat_script.exists():
        print("⚠️  Batch wrapper generator not found")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(create_bat_script)], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Batch wrappers created successfully")
            return True
        else:
            print("⚠️  Some issues creating batch wrappers")
            return False
    except Exception as e:
        print(f"❌ Failed to create batch wrappers: {e}")
        return False

def test_launcher():
    """Test if the launcher can start properly"""
    print("\n🧪 Testing launcher...")
    
    # This script is now in Installer folder, so get installation root (parent of Installer)
    install_dir = Path(__file__).parent.parent
    launcher_path = install_dir / "_system" / "secure_launcher.py"
    
    try:
        # Try to import the launcher to check for errors
        import importlib.util
        spec = importlib.util.spec_from_file_location("secure_launcher", launcher_path)
        launcher_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher_module)
        print("✅ Launcher imports successfully")
        return True
    except Exception as e:
        print(f"❌ Launcher test failed: {e}")
        return False

def configure_employee_data_transfer(installation_dir: Path) -> bool:
    """Configure employee computer for data transfer to central location."""
    print("\n📡 Configuring data transfer settings...")
    
    try:
        # Add AI directory to path
        ai_dir = installation_dir / "AI" / "monitoring"
        if ai_dir.exists():
            import sys
            if str(installation_dir / "AI") not in sys.path:
                sys.path.insert(0, str(installation_dir / "AI"))
            
            from monitoring.system_config import configure_employee_mode
            
            # Central data path is automatically set - no user input needed
            central_path = r"G:\Company\Software\Training Data"
            transfer_interval_hours = 24  # Default: 24 hours
            
            print("\n" + "=" * 60)
            print("EMPLOYEE COMPUTER CONFIGURATION")
            print("=" * 60)
            print("\nThis computer will collect data and transfer it to a central location.")
            print("Training will happen on the central computer, not here.")
            print()
            print(f"Central data folder: {central_path}")
            print(f"Transfer interval: {transfer_interval_hours} hours")
            print()
            print("Configuring automatically...")
            
            # Configure automatically
            if configure_employee_mode(installation_dir, central_path, transfer_interval_hours):
                print(f"\n✅ Employee mode configured successfully!")
                print(f"   Central data path: {central_path}")
                print(f"   Transfer interval: {transfer_interval_hours} hours")
                print("\nData will be automatically transferred when bots run.")
                
                # Verify the path is accessible (don't fail if it doesn't exist yet)
                from pathlib import Path
                try:
                    central_path_obj = Path(central_path)
                    # For network paths, try to access parent directory
                    if central_path_obj.exists():
                        print(f"✅ Central data folder is accessible")
                    elif central_path_obj.parent.exists():
                        print(f"✅ Central data folder parent exists (folder will be created automatically)")
                    else:
                        print(f"⚠️  Central data folder does not exist yet (will be created automatically on first transfer)")
                except Exception as e:
                    print(f"⚠️  Could not verify central data folder: {e}")
                    print(f"   (This is OK - folder will be created automatically on first transfer)")
                
                return True
            else:
                print("\n❌ Failed to save configuration")
                print("You can configure this later using _tools\\config\\CONFIGURE_EMPLOYEE_MODE.py")
                return False
        else:
            print("⚠️  AI monitoring directory not found. Skipping employee configuration.")
            return False
    except Exception as e:
        print(f"\n⚠️  Error configuring employee mode: {e}")
        print("You can configure this later using _tools\\config\\CONFIGURE_EMPLOYEE_MODE.py")
        return False

def main():
    print_header()
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Installation cannot continue")
        input("Press ENTER to exit...")
        return False
    
    # Install requirements
    if not install_requirements():
        print("\n⚠️  Some packages failed to install, but continuing...")
    
    # Create batch wrappers for bots
    create_bat_wrappers()
    
    # Test launcher
    if not test_launcher():
        print("\n❌ Launcher test failed - installation may not work properly")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            return False
    
    # Configure employee data transfer
    install_dir = Path(__file__).parent.parent
    configure_employee_data_transfer(install_dir)
    
    # Create desktop shortcut
    if not create_desktop_shortcut():
        print("\n❌ Failed to create desktop shortcut")
        input("Press ENTER to exit...")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Installation Complete!")
    print("=" * 60)
    print("\n📍 Next Steps:")
    print("   1. Look for 'Automation Hub' icon on your desktop")
    print("   2. Double-click it to launch the bot software")
    print("   3. Individual bots can also be double-clicked (they have .bat wrappers)")
    print("   4. Data will be automatically collected and transferred to central location")
    print("   5. If it doesn't work, check the error message and contact support")
    print("\n✅ You're all set!")
    print()
    print("=" * 60)
    print("VERIFICATION (Run This Now)")
    print("=" * 60)
    print("\n✅ Installation complete! Now verify everything is working:")
    print("\n   python _tools\\config\\VERIFY_EMPLOYEE_INSTALLATION.py")
    print("\nThis will check:")
    print("   - System configuration (employee mode)")
    print("   - Data collection setup")
    print("   - Transfer configuration (G:\\Company\\Software\\Training Data)")
    print("   - Network connectivity")
    print("\n⚠️  IMPORTANT: Run verification AFTER installation (which you just did!)")
    print()
    input("Press ENTER to exit...")
    return True

if __name__ == "__main__":
    main()
