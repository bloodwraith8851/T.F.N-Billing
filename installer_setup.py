import os
import sys
import shutil
import customtkinter as ctk
from tkinter import filedialog, messagebox
from win32com.client import Dispatch
from PIL import Image

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class InstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Thunderstorm Billing Setup")
        self.geometry("600x450")
        self.resizable(False, False)
        
        # Variables
        default_path = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Thunderstorm Billing")
        self.install_dir = ctk.StringVar(value=default_path)
        
        self.create_widgets()
        
    def create_widgets(self):
        # Sidebar/Accent Frame
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        # Logo or Icon Placeholder
        self.logo_label = ctk.CTkLabel(self.sidebar, text="⚡", font=("Arial", 60))
        self.logo_label.pack(pady=(40, 10))
        
        self.title_label = ctk.CTkLabel(self.sidebar, text="Thunderstorm\nBilling", font=("Arial", 18, "bold"))
        self.title_label.pack(pady=10)
        
        self.status_label = ctk.CTkLabel(self.sidebar, text="Version 1.0.0", font=("Arial", 11), text_color="gray")
        self.status_label.pack(side="bottom", pady=20)
        
        # Main Content area
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=30, pady=40)
        
        ctk.CTkLabel(self.main_content, text="Installation Setup", font=("Arial", 24, "bold"), anchor="w").pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(self.main_content, text="Choose installation folder:", font=("Arial", 13), anchor="w").pack(fill="x", pady=(10, 5))
        
        self.path_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.path_frame.pack(fill="x", pady=5)
        
        self.path_entry = ctk.CTkEntry(self.path_frame, textvariable=self.install_dir, width=250)
        self.path_entry.pack(side="left", padx=(0, 10))
        
        self.browse_btn = ctk.CTkButton(self.path_frame, text="Browse", width=80, command=self.browse_folder)
        self.browse_btn.pack(side="left")
        
        self.info_label = ctk.CTkLabel(self.main_content, 
                                     text="The setup will install Thunderstorm Billing and create a desktop shortcut for quick access.", 
                                     wraplength=300, justify="left", font=("Arial", 12), text_color="gray")
        self.info_label.pack(anchor="w", pady=30)
        
        # Progress Bar (initially hidden)
        self.progress = ctk.CTkProgressBar(self.main_content, width=340)
        self.progress.set(0)
        
        # Action Buttons
        self.button_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.button_frame.pack(side="bottom", fill="x")
        
        self.install_btn = ctk.CTkButton(self.button_frame, text="Install Now", command=self.start_install, font=("Arial", 13, "bold"), height=35)
        self.install_btn.pack(side="right")
        
        self.cancel_btn = ctk.CTkButton(self.button_frame, text="Cancel", fg_color="gray", width=90, command=self.quit, height=35)
        self.cancel_btn.pack(side="right", padx=10)

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
        
        self.install_btn.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.path_entry.configure(state="disabled")
        
        self.progress.pack(pady=10)
        self.run_installation(target)

    def run_installation(self, target_dir):
        try:
            # Source folder (where the app files are)
            if getattr(sys, 'frozen', False):
                source_dir = os.path.join(sys._MEIPASS, "Thunderstorm Billing")
                if not os.path.exists(source_dir):
                    source_dir = sys._MEIPASS
            else:
                source_dir = r"d:\T.F.N Billing\dist\Thunderstorm Billing"
            
            files_to_copy = []
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    files_to_copy.append(os.path.join(root, file))
            
            total_files = len(files_to_copy)
            if total_files == 0:
                # Fallback for dev testing if dist is empty
                source_dir = r"d:\T.F.N Billing"
                files_to_copy = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
                total_files = len(files_to_copy)

            for i, src_file in enumerate(files_to_copy):
                # Update progress
                self.progress.set((i + 1) / total_files)
                self.update_idletasks()
                
                rel_path = os.path.relpath(src_file, source_dir)
                dest_path = os.path.join(target_dir, rel_path)
                
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_file, dest_path)
            
            self.create_shortcut(target_dir)
            
            messagebox.showinfo("Success", "Thunderstorm Billing has been installed successfully!")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Installation Failed", str(e))
            self.install_btn.configure(state="normal")

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

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
