import os
import subprocess
import shutil
import sys

def build_app():
    print("Building application bundle...")
    # Step 1: Build the main application
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "launcher.spec"
    ]
    subprocess.run(build_cmd, check=True)
    print("Application built successfully in dist/Thunderstorm Billing")

def build_installer():
    print("\nBuilding installer executable...")
    # Step 2: Build the installer setup
    # We add the entire dist/Thunderstorm Billing folder into the installer
    dist_path = os.path.join("dist", "Thunderstorm Billing")
    
    if not os.path.exists(dist_path):
        print(f"Error: {dist_path} not found. Build the app first.")
        return

    # Create the installer
    setup_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--add-data={dist_path};Thunderstorm Billing",  # App bundle
        "--add-data=installer_web;installer_web",         # HTML/CSS/JS frontend
        "--add-data=version.json;.",                      # Version display
        "--hidden-import=eel",
        "--hidden-import=bottle",
        "--hidden-import=bottle_websocket",
        "--hidden-import=geventwebsocket",
        "--hidden-import=whichcraft",
        "--name=Thunderstorm_Billing_Setup",
        "installer_setup.py"
    ]
    # Optionally bundle existing settings.json so first-run has correct defaults
    if os.path.exists("settings.json"):
        setup_cmd.insert(-1, "--add-data=settings.json;.")
    subprocess.run(setup_cmd, check=True)
    print("\nInstaller built successfully: dist/Thunderstorm_Billing_Setup.exe")

if __name__ == "__main__":
    try:
        # Check if PyInstaller is installed
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], check=True, capture_output=True)
        
        # Build app first
        build_app()
        
        # Then build installer
        build_installer()
        
        print("\nAll done! You can find the installer in the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)
