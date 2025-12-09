#!/usr/bin/env python3
"""
Deploy Update - Deploy update packages to employee computers
This tool helps deploy updates across multiple computers in your organization.
"""

import os
import sys
import json
import zipfile
import shutil
import subprocess
from pathlib import Path
import argparse
import threading
import time
from datetime import datetime

class UpdateDeployer:
    def __init__(self):
        self.computers_file = Path("computers.json")
        self.deployment_log = Path("deployment_log.txt")
        self.computers = self._load_computers()
        
    def _load_computers(self):
        """Load computer list from file"""
        if self.computers_file.exists():
            with open(self.computers_file, 'r') as f:
                return json.load(f)
        else:
            # Create default computers file
            default_computers = {
                "computers": [
                    {
                        "name": "Computer1",
                        "ip": "192.168.1.100",
                        "user": "employee1",
                        "bot_path": "C:\\Users\\employee1\\Desktop\\In-Office Installation",
                        "status": "active"
                    },
                    {
                        "name": "Computer2", 
                        "ip": "192.168.1.101",
                        "user": "employee2",
                        "bot_path": "C:\\Users\\employee2\\Desktop\\In-Office Installation",
                        "status": "active"
                    }
                ]
            }
            self._save_computers(default_computers)
            return default_computers
    
    def _save_computers(self, computers):
        """Save computer list to file"""
        with open(self.computers_file, 'w') as f:
            json.dump(computers, f, indent=2)
    
    def add_computer(self, name, ip, user, bot_path):
        """Add a new computer to the deployment list"""
        new_computer = {
            "name": name,
            "ip": ip,
            "user": user,
            "bot_path": bot_path,
            "status": "active"
        }
        
        self.computers["computers"].append(new_computer)
        self._save_computers(self.computers)
        print(f"✅ Added computer: {name}")
    
    def list_computers(self):
        """List all computers in the deployment list"""
        print("\n📋 Computer List:")
        print("-" * 80)
        print(f"{'Name':<15} {'IP':<15} {'User':<15} {'Status':<10} {'Bot Path'}")
        print("-" * 80)
        
        for computer in self.computers["computers"]:
            print(f"{computer['name']:<15} {computer['ip']:<15} {computer['user']:<15} "
                  f"{computer['status']:<10} {computer['bot_path']}")
    
    def deploy_update(self, package_path, target_computers=None, dry_run=False):
        """Deploy update package to computers"""
        if not Path(package_path).exists():
            print(f"❌ Package not found: {package_path}")
            return False
        
        if target_computers is None:
            target_computers = [comp["name"] for comp in self.computers["computers"] 
                              if comp["status"] == "active"]
        
        print(f"🚀 Deploying update package: {package_path}")
        print(f"📦 Target computers: {', '.join(target_computers)}")
        
        if dry_run:
            print("🔍 DRY RUN - No actual deployment will occur")
            return True
        
        # Deploy to each computer
        results = []
        for computer_name in target_computers:
            computer = next((c for c in self.computers["computers"] if c["name"] == computer_name), None)
            if computer:
                result = self._deploy_to_computer(computer, package_path)
                results.append((computer_name, result))
            else:
                print(f"❌ Computer not found: {computer_name}")
                results.append((computer_name, False))
        
        # Print results
        self._print_deployment_results(results)
        return all(result for _, result in results)
    
    def _deploy_to_computer(self, computer, package_path):
        """Deploy update to a specific computer"""
        print(f"\n📡 Deploying to {computer['name']} ({computer['ip']})...")
        
        try:
            # Method 1: Network share deployment (recommended)
            if self._deploy_via_network_share(computer, package_path):
                return True
            
            # Method 2: Remote execution (alternative)
            if self._deploy_via_remote_execution(computer, package_path):
                return True
            
            # Method 3: Manual deployment instructions
            self._print_manual_deployment(computer, package_path)
            return False
            
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False
    
    def _deploy_via_network_share(self, computer, package_path):
        """Deploy via network share (recommended method)"""
        try:
            # Copy package to network share
            network_share = f"\\\\{computer['ip']}\\ccmd-bots\\updates\\"
            network_package_path = f"{network_share}{Path(package_path).name}"
            
            print(f"  📁 Copying to network share: {network_package_path}")
            
            # Create network share directory
            os.makedirs(network_share, exist_ok=True)
            
            # Copy package
            shutil.copy2(package_path, network_package_path)
            
            # Create deployment script
            deploy_script = f'''@echo off
echo Installing CCMD Bot update...
cd /d "{computer['bot_path']}"
python install_update.py
pause
'''
            
            script_path = f"{network_share}deploy_update.bat"
            with open(script_path, 'w') as f:
                f.write(deploy_script)
            
            print(f"  ✅ Package copied to network share")
            print(f"  📝 Deployment script created: {script_path}")
            print(f"  💡 User can run: {script_path}")
            
            return True
            
        except Exception as e:
            print(f"  ⚠️  Network share deployment failed: {e}")
            return False
    
    def _deploy_via_remote_execution(self, computer, package_path):
        """Deploy via remote execution (requires setup)"""
        try:
            # This would require PowerShell remoting or similar
            # For now, just return False to use manual deployment
            print(f"  ⚠️  Remote execution not configured for {computer['name']}")
            return False
            
        except Exception as e:
            print(f"  ❌ Remote execution failed: {e}")
            return False
    
    def _print_manual_deployment(self, computer, package_path):
        """Print manual deployment instructions"""
        print(f"  📋 Manual deployment instructions for {computer['name']}:")
        print(f"     1. Copy {Path(package_path).name} to {computer['bot_path']}")
        print(f"     2. Extract the package")
        print(f"     3. Run: python install_update.py")
        print(f"     4. Restart the CCMD Bot Launcher")
    
    def _print_deployment_results(self, results):
        """Print deployment results summary"""
        print("\n" + "=" * 60)
        print("📊 DEPLOYMENT RESULTS")
        print("=" * 60)
        
        successful = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"✅ Successful: {successful}/{total}")
        print(f"❌ Failed: {total - successful}/{total}")
        
        print("\nDetailed Results:")
        for computer_name, result in results:
            status = "✅ SUCCESS" if result else "❌ FAILED"
            print(f"  {computer_name:<15} {status}")
        
        # Log results
        self._log_deployment(results)
    
    def _log_deployment(self, results):
        """Log deployment results"""
        timestamp = datetime.now().isoformat()
        
        with open(self.deployment_log, 'a') as f:
            f.write(f"\n[{timestamp}] Deployment Results:\n")
            for computer_name, result in results:
                status = "SUCCESS" if result else "FAILED"
                f.write(f"  {computer_name}: {status}\n")
    
    def check_computer_status(self, computer_name):
        """Check if a computer is online and accessible"""
        computer = next((c for c in self.computers["computers"] if c["name"] == computer_name), None)
        if not computer:
            print(f"❌ Computer not found: {computer_name}")
            return False
        
        print(f"🔍 Checking status of {computer['name']} ({computer['ip']})...")
        
        try:
            # Ping the computer
            result = subprocess.run(['ping', '-n', '1', computer['ip']], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"  ✅ Computer is online")
                return True
            else:
                print(f"  ❌ Computer is offline or unreachable")
                return False
                
        except Exception as e:
            print(f"  ❌ Error checking status: {e}")
            return False
    
    def check_all_computers(self):
        """Check status of all computers"""
        print("🔍 Checking status of all computers...")
        
        results = []
        for computer in self.computers["computers"]:
            if computer["status"] == "active":
                is_online = self.check_computer_status(computer["name"])
                results.append((computer["name"], is_online))
        
        print("\n📊 Status Summary:")
        online_count = sum(1 for _, is_online in results if is_online)
        total_count = len(results)
        
        print(f"🟢 Online: {online_count}/{total_count}")
        print(f"🔴 Offline: {total_count - online_count}/{total_count}")
        
        return results

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Deploy CCMD Bot updates")
    parser.add_argument("--package", help="Update package path")
    parser.add_argument("--computers", nargs="+", help="Target computer names")
    parser.add_argument("--add-computer", nargs=4, metavar=("NAME", "IP", "USER", "PATH"),
                       help="Add a new computer to deployment list")
    parser.add_argument("--list", action="store_true", help="List all computers")
    parser.add_argument("--check-status", help="Check status of specific computer")
    parser.add_argument("--check-all", action="store_true", help="Check status of all computers")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deployment without actually deploying")
    
    args = parser.parse_args()
    
    deployer = UpdateDeployer()
    
    if args.add_computer:
        name, ip, user, path = args.add_computer
        deployer.add_computer(name, ip, user, path)
    
    elif args.list:
        deployer.list_computers()
    
    elif args.check_status:
        deployer.check_computer_status(args.check_status)
    
    elif args.check_all:
        deployer.check_all_computers()
    
    elif args.package:
        deployer.deploy_update(args.package, args.computers, args.dry_run)
    
    else:
        print("CCMD Bot Update Deployer")
        print("Use --help for available options")
        print("\nQuick start:")
        print("1. Add computers: --add-computer 'Computer1' '192.168.1.100' 'user1' 'C:\\path\\to\\bots'")
        print("2. List computers: --list")
        print("3. Deploy update: --package update_package.zip")

if __name__ == "__main__":
    main()
