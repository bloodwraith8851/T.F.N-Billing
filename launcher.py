import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
import time
import warnings
import traceback
import logging

# Set up logging
logging.basicConfig(
    filename='tfn_billing_debug.log',
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

def install_requirements():
    """Install required packages"""
    logging.info("Starting requirements installation")
    try:
        # Create a simple GUI window to show progress
        root = tk.Tk()
        root.withdraw()
        
        # Create a custom dialog
        dialog = tk.Toplevel(root)
        dialog.title("Installing Requirements")
        dialog.geometry("300x150")
        
        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add message
        message = tk.Label(dialog, text="Installing required packages...\nPlease wait...", pady=20)
        message.pack()
        
        # Add progress message
        progress_msg = tk.Label(dialog, text="")
        progress_msg.pack()
        
        dialog.update()
        
        # Check if pip is installed
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "--version"])
        except subprocess.CalledProcessError:
            show_error_dialog("Error", "pip is not installed. Please install pip first.")
            return False
        
        # Install requirements
        progress_msg.config(text="Installing packages...")
        dialog.update()
        
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            show_error_dialog("Error", f"Failed to install requirements:\n{stderr}")
            return False
        
        progress_msg.config(text="Installation completed!")
        dialog.update()
        time.sleep(1)
        
        dialog.destroy()
        root.destroy()
        
        logging.info("Requirements installation completed successfully")
        return True
        
    except Exception as e:
        error_msg = f"Error installing requirements: {str(e)}\n{traceback.format_exc()}"
        show_error_dialog("Error", error_msg)
        return False

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
        
        # Create required directories
        dirs_to_create = ['output_invoices', 'assets']
        for dir_name in dirs_to_create:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
                logging.info(f"Created directory: {dir_name}")
                
        # Initialize database files
        db_files = {
            'users.json': '[{"username": "admin", "password": "admin", "role": "admin"}]',
            'customers.json': '[]',
            'invoice_tracker.json': '{"last_invoice_number": 2058}',
            'invoice_log.json': '[]'
        }
        
        for filename, content in db_files.items():
            if not os.path.exists(filename):
                with open(filename, 'w') as f:
                    f.write(content)
                logging.info(f"Created database file: {filename}")
                
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
        
    # Check if requirements are installed
    try:
        import reportlab
        import ttkbootstrap
        import pandas
        import matplotlib
        import PIL
        logging.info("All required packages are installed")
    except ImportError as e:
        logging.warning(f"Missing package: {str(e)}")
        if not install_requirements():
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

        # Import the main module
        logging.info("Importing main module")
        import main
        
        # Create and run the application through the login window
        logging.info("Starting main application")
        main.start_application()  # Use start_application instead of login_window
        
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