import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from win32com.client import Dispatch

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thunderstorm Billing Setup")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        
        # Style
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6)
        
        # Variables
        self.install_dir = tk.StringVar(value=os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Thunderstorm Billing"))
        
        self.create_widgets()
        
    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#4A6CFA", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="Thunderstorm Billing Setup", bg="#4A6CFA", fg="white", font=("Arial", 16, "bold")).pack(pady=20)
        
        # Content
        content_frame = ttk.Frame(self.root, padding=20)
        content_frame.pack(fill="both", expand=True)
        
        tk.Label(content_frame, text="Select Installation Folder:", font=("Arial", 10)).pack(anchor="w", pady=(10, 5))
        
        path_frame = tk.Frame(content_frame)
        path_frame.pack(fill="x")
        
        tk.Entry(path_frame, textvariable=self.install_dir, width=40).pack(side="left", padx=(0, 10))
        tk.Button(path_frame, text="Browse...", command=self.browse_folder).pack(side="left")
        
        tk.Label(content_frame, text="The installer will copy all necessary files and create a desktop shortcut.", wraplength=450, justify="left").pack(anchor="w", pady=20)
        
        # Progress Bar
        self.progress = ttk.Progressbar(content_frame, orient="horizontal", length=450, mode="determinate")
        self.progress.pack(pady=(0, 20))
        
        # Footer
        footer_frame = tk.Frame(self.root)
        footer_frame.pack(fill="x", side="bottom", pady=20)
        
        self.install_btn = tk.Button(footer_frame, text="Install Now", bg="#4A6CFA", fg="white", font=("Arial", 10, "bold"), width=15, command=self.start_install)
        self.install_btn.pack(side="right", padx=20)
        
        tk.Button(footer_frame, text="Cancel", width=10, command=self.root.quit).pack(side="right")

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.install_dir.get())
        if folder:
            self.install_dir.set(folder)

    def start_install(self):
        target = self.install_dir.get()
        if not os.path.exists(target):
            try:
                os.makedirs(target)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create directory: {e}")
                return
        
        self.install_btn.config(state="disabled")
        self.run_installation(target)

    def run_installation(self, target_dir):
        try:
            # Source folder (where the app files are - usually same dir as this setup or bundled)
            if getattr(sys, 'frozen', False):
                # The build script adds data as 'Thunderstorm Billing' folder
                source_dir = os.path.join(sys._MEIPASS, "Thunderstorm Billing")
                if not os.path.exists(source_dir):
                    source_dir = sys._MEIPASS
            else:
                source_dir = r"d:\T.F.N Billing\dist\Thunderstorm Billing" # For testing in dev
            
            # Simple simulation of file copying
            files_to_copy = []
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    files_to_copy.append(os.path.join(root, file))
            
            total_files = len(files_to_copy)
            if total_files == 0:
                # If no files in dist, try parent dir for dev testing
                source_dir = r"d:\T.F.N Billing"
                files_to_copy = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
                total_files = len(files_to_copy)

            for i, src_file in enumerate(files_to_copy):
                # Update progress
                self.progress['value'] = (i + 1) / total_files * 100
                self.root.update_idletasks()
                
                # Copying logic
                rel_path = os.path.relpath(src_file, source_dir)
                dest_path = os.path.join(target_dir, rel_path)
                
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_file, dest_path)
            
            # Create Shortcut
            self.create_shortcut(target_dir)
            
            messagebox.showinfo("Success", "Thunderstorm Billing has been installed successfully!")
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("Installation Failed", str(e))
            self.install_btn.config(state="normal")

    def create_shortcut(self, target_dir):
        try:
            shell = Dispatch('WScript.Shell')
            desktop = shell.SpecialFolders("Desktop")
            path = os.path.join(desktop, "Thunderstorm Billing.lnk")
            target = os.path.join(target_dir, "Thunderstorm Billing.exe")
            icon = os.path.join(target_dir, "assets", "logo.ico")
            
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = target_dir
            if os.path.exists(icon):
                shortcut.IconLocation = icon
            shortcut.save()
        except Exception as e:
            print(f"Non-critical error creating shortcut: {e}")
            # We don't want to fail the whole install for just a shortcut

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
