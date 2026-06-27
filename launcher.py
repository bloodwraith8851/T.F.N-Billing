import os
import sys

# No longer importing numpy here to prevent bloat.

import subprocess
import tkinter as tk
from tkinter import messagebox
import time
import warnings
import traceback
import logging

# Set up logging in local app data
_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ThunderstormBilling')
os.makedirs(_data_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(_data_dir, 'tfn_billing_debug.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Suppress setuptools deprecation warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pkg_resources')
warnings.filterwarnings('ignore', category=DeprecationWarning)

def show_error_dialog(title, message):
    """Show error in both GUI and log"""
    logging.error(f"{title}: {message}")
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except:
        print(f"ERROR - {title}: {message}")

def initialize_directories():
    """Initialize required directories"""
    logging.info("Initializing directories and files")
    try:
        # Get the application directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            app_dir = os.path.dirname(os.path.abspath(__file__))
            
        logging.info(f"Application directory: {app_dir}")
        
        # Change to the application directory
        os.chdir(app_dir)
        logging.info(f"Changed working directory to: {os.getcwd()}")
        
        # Initialize data directories and migrate legacy files
        try:
            current_dir = os.getcwd()
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            import backend
            backend.migrate_legacy_data(app_dir)
            logging.info("Data directory initialized and legacy data migrated.")
        except Exception as e:
            logging.error(f"Migration error: {e}")
        
        # Create local required directories for static assets
        dirs_to_create = ['assets', os.path.join('web', 'static', 'assets')]
        for dir_name in dirs_to_create:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
                logging.info(f"Created directory: {dir_name}")
                
        # Copy default assets from bundled _MEIPASS if they don't exist locally
        try:
            import shutil
            bundled_assets = os.path.join(getattr(sys, '_MEIPASS', app_dir), 'assets')
            if os.path.exists(bundled_assets) and bundled_assets != os.path.abspath('assets'):
                for filename in ['logo.png', 'logo.ico']:
                    bundled_file = os.path.join(bundled_assets, filename)
                    local_root_file = os.path.join('assets', filename)
                    local_web_file = os.path.join('web', 'static', 'assets', filename)
                    
                    if os.path.exists(bundled_file):
                        if not os.path.exists(local_root_file):
                            shutil.copy2(bundled_file, local_root_file)
                            logging.info(f"Copied bundled {filename} to root assets.")
                        if filename == 'logo.png' and not os.path.exists(local_web_file):
                            shutil.copy2(bundled_file, local_web_file)
                            logging.info(f"Copied bundled logo to web/static/assets.")
        except Exception as e:
            logging.error(f"Error copying bundled assets: {str(e)}")
                
        return True
        
    except Exception as e:
        error_msg = f"Failed to initialize directories: {str(e)}\n{traceback.format_exc()}"
        show_error_dialog("Error", error_msg)
        return False

def main():
    """Main function to run the application"""
    logging.info("Starting TFN Billing application")
    
    # Initialize required directories and files
    if not initialize_directories():
        return
    # Import and run the main application
    try:
        # Add the current directory to Python path
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        logging.info(f"Python path: {sys.path}")
        logging.info(f"Current directory: {current_dir}")
        logging.info(f"Directory contents: {os.listdir('.')}")

        # Import the eel module
        logging.info("Importing app_eel module")
        import app_eel
        
        # Create and run the application
        logging.info("Starting main application")
        app_eel.start_app()
        
    except Exception as e:
        error_msg = f"Failed to start application:\n{str(e)}\n\nDetails:\n"
        error_msg += f"Current directory: {os.getcwd()}\n"
        error_msg += f"Python path: {sys.path}\n"
        error_msg += f"Files in directory: {os.listdir('.')}\n"
        error_msg += f"\nFull traceback:\n{traceback.format_exc()}"
        show_error_dialog("Error", error_msg)
        logging.error(error_msg)
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Unhandled exception: {str(e)}\n{traceback.format_exc()}")
        show_error_dialog("Critical Error", f"Unhandled exception: {str(e)}") 