#!/usr/bin/env python3
"""
Automatic Dependency Installation - Enterprise Deployment
Installs all dependencies automatically when bots are installed on employee computers.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import logging

class AutoDependencyInstaller:
    """Automatically installs all dependencies for enterprise AI system"""
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize dependency installer"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.system_dir = self.installation_dir / "_system"
        
        # Setup logging
        self.log_file = self.system_dir / "dependency_install.log"
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def install_all_dependencies(self):
        """Install all dependencies for enterprise AI system"""
        self.logger.info("Starting automatic dependency installation...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            self.logger.error(f"Python 3.8+ required. Current version: {python_version.major}.{python_version.minor}")
            return False
        
        self.logger.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Upgrade pip first
        self.logger.info("Upgrading pip to latest version...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                 "pip", "--no-warn-script-location"],
                capture_output=True,
                text=True,
                timeout=300
            )
        except:
            pass  # Continue even if pip upgrade fails
        
        # Install standard dependencies
        requirements_file = self.system_dir / "requirements.txt"
        if requirements_file.exists():
            self.logger.info("Installing standard dependencies...")
            self._install_from_requirements(requirements_file)
        
        # Install enterprise dependencies (including AI monitoring)
        enterprise_requirements = self.system_dir / "requirements_enterprise.txt"
        if enterprise_requirements.exists():
            self.logger.info("Installing enterprise AI dependencies (including monitoring)...")
            self._install_from_requirements(enterprise_requirements)

        # Install bot-specific requirements
        self._install_bot_requirements()
        
        # Install critical packages individually (ensure they're installed)
        critical_packages = [
            "cryptography>=41.0.0",
            "selenium>=4.0.0",
            "webdriver-manager>=4.0.0",
            "pandas>=2.0.0",
            "pillow>=10.0.0",
            "mss>=9.0.0",
            "pynput>=1.7.6",
            "psutil>=5.9.0",
            "watchdog>=3.0.0"
        ]
        
        self.logger.info("Installing critical packages individually...")
        for package in critical_packages:
            self._install_package(package)
        
        # Verify installations
        self._verify_installations()
        
        self.logger.info("Dependency installation completed!")
        return True
    
    def _install_from_requirements(self, requirements_file: Path):
        """Install packages from requirements file"""
        try:
            # First, upgrade pip
            self.logger.info("Upgrading pip...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", 
                 "pip", "--no-warn-script-location"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Install packages with --only-binary for packages that might need compilation
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                 "--no-warn-script-location", "--only-binary", ":all:",
                 "-r", str(requirements_file)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully installed from {requirements_file.name}")
            else:
                # Retry without --only-binary for packages that need it
                self.logger.info(f"Retrying installation without binary-only flag...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                     "--no-warn-script-location", "-r", str(requirements_file)],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result.returncode == 0:
                    self.logger.info(f"Successfully installed from {requirements_file.name} (retry)")
                else:
                    self.logger.warning(f"Some packages may not have installed: {result.stderr}")
        except subprocess.TimeoutExpired:
            self.logger.error(f"Installation timeout for {requirements_file.name}")
        except Exception as e:
            self.logger.error(f"Error installing from {requirements_file.name}: {e}")
    
    def _install_package(self, package_name: str):
        """Install a single package"""
        try:
            # Try with --only-binary first (faster, avoids compilation)
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                 "--no-warn-script-location", "--only-binary", ":all:", package_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully installed {package_name}")
            else:
                # Retry without --only-binary if it fails
                self.logger.info(f"Retrying {package_name} without binary-only flag...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
                     "--no-warn-script-location", package_name],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    self.logger.info(f"Successfully installed {package_name} (retry)")
                else:
                    self.logger.warning(f"Failed to install {package_name}: {result.stderr}")
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout installing {package_name}")
        except Exception as e:
            self.logger.error(f"Error installing {package_name}: {e}")
    
    def _verify_installations(self):
        """Verify critical packages are installed"""
        critical_packages = [
            "cryptography",
            "pandas",
            "numpy",
            "requests",
            "selenium",
            "mss",
            "pynput",
            "psutil",
            "watchdog"
        ]
        
        self.logger.info("Verifying critical package installations...")
        installed_count = 0
        for package in critical_packages:
            try:
                __import__(package)
                self.logger.info(f"✓ {package} installed")
                installed_count += 1
            except ImportError:
                self.logger.warning(f"✗ {package} not installed")
        
        self.logger.info(f"Installed {installed_count}/{len(critical_packages)} critical packages")
    
    def install_ollama(self):
        """Provide instructions for Ollama installation"""
        self.logger.info("Ollama (local AI) installation:")
        self.logger.info("1. Download from: https://ollama.ai")
        self.logger.info("2. Install Ollama")
        self.logger.info("3. Run: ollama serve")
        self.logger.info("4. Pull model: ollama pull llama2")

    def _install_bot_requirements(self):
        """Install requirements.txt files located under the _bots directory."""
        bots_dir = self.installation_dir / "_bots"

        if not bots_dir.exists():
            self.logger.warning("_bots directory not found - skipping bot dependency installation")
            return

        requirement_files = sorted({req.resolve() for req in bots_dir.rglob("requirements.txt")})

        if not requirement_files:
            self.logger.info("No bot requirements files found")
            return

        self.logger.info("Installing bot-specific dependencies...")

        for req_file in requirement_files:
            try:
                relative_path = req_file.relative_to(self.installation_dir)
            except ValueError:
                relative_path = req_file

            self.logger.info(f"Installing dependencies from {relative_path}")
            try:
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "--quiet",
                        "--upgrade",
                        "--no-warn-script-location",
                        "-r",
                        str(req_file)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=True,
                )
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout installing dependencies from {relative_path}")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to install dependencies from {relative_path}: {e}")
            except Exception as e:
                self.logger.warning(f"Unexpected error installing {relative_path}: {e}")

if __name__ == "__main__":
    installer = AutoDependencyInstaller()
    installer.install_all_dependencies()

