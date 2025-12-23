import requests
import threading
import os
import sys
import tempfile
import subprocess
from tkinter import messagebox
import json

class UpdateManager:
    def __init__(self, root, status_callback):
        self.root = root
        self.status_callback = status_callback
        
        # Find the project root directory
        current_file_dir = os.path.dirname(os.path.abspath(__file__))  # src/core/
        src_dir = os.path.dirname(current_file_dir)  # src/
        project_root = os.path.dirname(src_dir)  # Torrent_downloader/
        
        # Look for config.json in project root
        config_path = os.path.join(project_root, 'config.json')
        
        print(f"Looking for config at: {config_path}")  # Debug line
        
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
                
            self.current_version = self.config['app']['version']
            self.github_repo = self.config['app']['github_repo']
            self.latest_version = self.current_version
            self.update_available = False
            
            print(f"Loaded config: version={self.current_version}, repo={self.github_repo}")  # Debug
            
        except FileNotFoundError:
            print(f"Config file not found at: {config_path}")
            # Set defaults
            self.current_version = "1.0.0"
            self.github_repo = "fonker001/Tkinter_Torrent_downloader"
            self.latest_version = self.current_version
            self.update_available = False
            self.status_callback("Config not found - using defaults")
        except Exception as e:
            print(f"Error loading config: {e}")
            # Set defaults
            self.current_version = "1.0.0"
            self.github_repo = "fonker001/Tkinter_Torrent_downloader"
            self.latest_version = self.current_version
            self.update_available = False
            self.status_callback("Error loading config - using defaults")
        
    def check_for_updates(self, silent=False):
        """Check GitHub for newer versions"""
        try:
            # If no repo configured, skip update check
            if not self.github_repo or self.github_repo == "yourusername/your-repo-name":
                if not silent:
                    self.status_callback("Update checking not configured")
                return False
                
            repo_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
            
            print(f"Checking updates from: {repo_url}")  # Debug
            
            # Add proper headers for GitHub API
            headers = {
                'User-Agent': 'YTS-Browser-App',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(repo_url, headers=headers, timeout=10)
            
            # Handle different HTTP status codes
            if response.status_code == 404:
                error_msg = f"Repository not found: {self.github_repo}"
                if not silent:
                    self.status_callback(error_msg)
                return False
            elif response.status_code == 403:
                error_msg = "GitHub API rate limit exceeded"
                if not silent:
                    self.status_callback(error_msg)
                return False
                
            response.raise_for_status()
            release_data = response.json()
            
            self.latest_version = release_data['tag_name'].lstrip('v')
            
            if self.is_newer_version(self.latest_version, self.current_version):
                self.update_available = True
                if not silent:
                    self.root.after(0, self.show_update_prompt, release_data)
                return True
            else:
                if not silent:
                    self.status_callback(f"Your app is up to date (v{self.current_version})")
                return False
                
        except Exception as e:
            if not silent:
                self.status_callback(f"Update check failed: {str(e)}")
            return False
    
    def is_newer_version(self, latest, current):
        """Compare version strings to see if latest is newer than current"""
        try:
            latest_parts = list(map(int, latest.split('.')))
            current_parts = list(map(int, current.split('.')))
            
            for i in range(max(len(latest_parts), len(current_parts))):
                l = latest_parts[i] if i < len(latest_parts) else 0
                c = current_parts[i] if i < len(current_parts) else 0
                if l > c:
                    return True
                elif l < c:
                    return False
            return False
        except:
            return False
    
    def show_update_prompt(self, release_data):
        """Show a dialog asking user if they want to update"""
        message = (
            f"A new version (v{self.latest_version}) is available!\n\n"
            f"Current version: v{self.current_version}\n\n"
            f"Release notes:\n{release_data.get('body', 'No description provided')}\n\n"
            "Would you like to update now?"
        )
        
        if messagebox.askyesno("Update Available", message):
            self.download_and_install_update(release_data)
    
    def download_and_install_update(self, release_data):
        """Download and install the update"""
        try:
            # Find the asset (assuming it's a Python script)
            asset = None
            for a in release_data.get('assets', []):
                if a['name'].endswith('.py'):
                    asset = a
                    break
            
            if not asset:
                self.status_callback("No suitable update file found")
                return
            
            # Download the update
            self.status_callback("Downloading update...")
            response = requests.get(asset['browser_download_url'], timeout=30)
            response.raise_for_status()
            
            # Save the update
            temp_dir = tempfile.gettempdir()
            update_path = os.path.join(temp_dir, "yts_browser_update.py")
            
            with open(update_path, 'wb') as f:
                f.write(response.content)
            
            # Create an updater script
            updater_script = self.create_updater_script(update_path)
            
            # Launch the updater and exit
            self.status_callback("Update downloaded. Restarting to apply update...")
            subprocess.Popen([sys.executable, updater_script])
            sys.exit(0)
            
        except Exception as e:
            self.status_callback(f"Update failed: {str(e)}")
    
    def create_updater_script(self, update_path):
        """Create a script that will handle the update process"""
        script_content = f'''
import os
import shutil
import time
import sys

# Wait a moment to ensure the main app has closed
time.sleep(2)

# Get the current script path
current_script = "{sys.argv[0]}"
update_script = "{update_path}"

try:
    # Replace the old file with the new one
    shutil.copy(update_script, current_script)
    print("Update successful! Starting the application...")
    
    # Start the updated application
    os.execl(sys.executable, sys.executable, current_script)
    
except Exception as e:
    print(f"Update failed: {{e}}")
    input("Press Enter to exit...")
'''
        
        temp_dir = tempfile.gettempdir()
        updater_path = os.path.join(temp_dir, "updater.py")
        
        with open(updater_path, 'w') as f:
            f.write(script_content)
            
        return updater_path