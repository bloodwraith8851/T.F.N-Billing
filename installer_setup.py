import os
import sys
import shutil
import random
import math
import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
from win32com.client import Dispatch
from PIL import Image

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SpaceCanvas(Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs, highlightthickness=0, bg="#0f172a") # Deep space blue
        self.stars = []
        self.clouds = []
        self.moon = None
        self.width = kwargs.get('width', 600)
        self.height = kwargs.get('height', 450)
        
        self.create_space()
        self.animate()
        
    def create_space(self):
        # Create Stars
        for _ in range(100):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.uniform(0.5, 2.5)
            alpha = random.uniform(0.3, 1.0)
            star = self.create_oval(x, y, x+size, y+size, fill="white", outline="")
            self.stars.append({
                "id": star,
                "speed": random.uniform(0.05, 0.15),
                "alpha": alpha,
                "blink": random.uniform(0.01, 0.05)
            })
            
        # Create Moon
        mx, my = self.width - 100, 80
        self.moon = self.create_oval(mx-40, my-40, mx+40, my+40, fill="#f1f5f9", outline="")
        # Simple crater
        self.create_oval(mx+5, my-10, mx+15, my, fill="#cbd5e1", outline="")
        self.create_oval(mx-15, my+5, mx-5, my+15, fill="#cbd5e1", outline="")
        
        # Create Clouds
        for _ in range(5):
            cx = random.randint(0, self.width)
            cy = random.randint(20, self.height-100)
            cloud_id = self.create_oval(cx-60, cy-20, cx+60, cy+20, fill="#334155", outline="", stipple="gray25")
            self.clouds.append({
                "id": cloud_id,
                "speed": random.uniform(0.2, 0.5),
                "x": cx
            })

    def animate(self):
        # Move Stars
        for star in self.stars:
            self.move(star["id"], -star["speed"], 0)
            coords = self.coords(star["id"])
            if coords[0] < -5:
                self.move(star["id"], self.width + 10, 0)
            
            # Twinkle
            if random.random() < 0.05:
                current_fill = self.itemcget(star["id"], "fill")
                self.itemconfig(star["id"], fill="white" if random.random() > 0.5 else "gray50")

        # Move Clouds
        for cloud in self.clouds:
            self.move(cloud["id"], cloud["speed"], 0)
            coords = self.coords(cloud["id"])
            if coords[0] > self.width + 70:
                self.move(cloud["id"], -self.width - 140, 0)
                
        self.after(50, self.animate)

class InstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Thunderstorm Billing Setup")
        self.geometry("600x450")
        self.resizable(False, False)
        
        # Background Animation
        self.bg_canvas = SpaceCanvas(self, width=600, height=450)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Variables
        default_path = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Thunderstorm Billing")
        self.install_dir = ctk.StringVar(value=default_path)
        
        self.create_widgets()
        
    def create_widgets(self):
        # Sidebar/Accent Frame (Glassmorphism effect simulation)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("rgba(30, 41, 59, 0.7)"))
        self.sidebar.pack(side="left", fill="y")
        
        # Logo or Icon Placeholder
        self.logo_label = ctk.CTkLabel(self.sidebar, text="⚡", font=("Arial", 60), fg_color="transparent")
        self.logo_label.pack(pady=(40, 10))
        
        self.title_label = ctk.CTkLabel(self.sidebar, text="Thunderstorm\nBilling", font=("Arial", 18, "bold"), fg_color="transparent")
        self.title_label.pack(pady=10)
        
        self.status_label = ctk.CTkLabel(self.sidebar, text="Version 1.0.1", font=("Arial", 11), text_color="gray", fg_color="transparent")
        self.status_label.pack(side="bottom", pady=20)
        
        # Main Content area
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=30, pady=40)
        
        ctk.CTkLabel(self.main_content, text="Installation Setup", font=("Arial", 28, "bold"), anchor="w").pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(self.main_content, text="Choose installation folder:", font=("Arial", 13), anchor="w").pack(fill="x", pady=(10, 5))
        
        self.path_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.path_frame.pack(fill="x", pady=5)
        
        self.path_entry = ctk.CTkEntry(self.path_frame, textvariable=self.install_dir, width=250)
        self.path_entry.pack(side="left", padx=(0, 10))
        
        self.browse_btn = ctk.CTkButton(self.path_frame, text="Browse", width=80, command=self.browse_folder)
        self.browse_btn.pack(side="left")
        
        self.info_label = ctk.CTkLabel(self.main_content, 
                                     text="The setup will install Thunderstorm Billing and create a desktop shortcut for quick access.", 
                                     wraplength=300, justify="left", font=("Arial", 12), text_color="#cbd5e1")
        self.info_label.pack(anchor="w", pady=30)
        
        # Progress Bar (initially hidden)
        self.progress = ctk.CTkProgressBar(self.main_content, width=340)
        self.progress.set(0)
        
        # Action Buttons
        self.button_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.button_frame.pack(side="bottom", fill="x")
        
        self.install_btn = ctk.CTkButton(self.button_frame, text="Install Now", command=self.start_install, font=("Arial", 13, "bold"), height=35)
        self.install_btn.pack(side="right")
        
        self.cancel_btn = ctk.CTkButton(self.button_frame, text="Cancel", fg_color="#475569", width=90, command=self.quit, height=35)
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
