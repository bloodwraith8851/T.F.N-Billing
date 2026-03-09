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
        super().__init__(master, **kwargs, highlightthickness=0, bg="#1a1c23") # Dark space matching dashboard exactly
        self.particles = []
        self.clouds = []
        self.moon = None
        self.width = kwargs.get('width', 600)
        self.height = kwargs.get('height', 450)
        
        # Colors from dashboard particles-js
        self.colors = ["#ffffff", "#a8d8ff", "#ffd6a5", "#c8b8ff", "#b8f5e0"]
        self.create_space()
        self.animate()
        
    def create_space(self):
        # 1. 3D Particles / Stars (Smaller, denser, like particles-js)
        for _ in range(150):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.uniform(0.5, 2.0)
            color = random.choice(self.colors)
            
            p = self.create_oval(x, y, x+size, y+size, fill=color, outline="")
            
            # Subtle glow for larger particles
            if size > 1.2:
                self.create_oval(x-1, y-1, x+size+1, y+size+1, fill="", outline=color, stipple="gray25")
                
            self.particles.append({
                "id": p,
                "dx": random.uniform(-0.2, 0.2), # slower movement
                "dy": random.uniform(-0.2, 0.2),
                "speed_factor": random.uniform(0.3, 1.0),
                "color": color
            })
            
        # 2. Glowing Moon (Moved to match dashboard generally)
        mx, my = self.width - 60, 100
        # Halos for glow effect - matching the CSS radial gradients
        self.create_oval(mx-45, my-45, mx+45, my+45, fill="#232731", outline="", stipple="gray25")
        self.create_oval(mx-35, my-35, mx+35, my+35, fill="#2a2f3a", outline="")
        # Core
        self.moon = self.create_oval(mx-22, my-22, mx+22, my+22, fill="#fffbe6", outline="")
        
        # 3. Fluffy Clouds (Simulating CSS clouds format - soft ethereal)
        cloud_configs = [
            {"x": -50, "y": 80, "speed": 0.2, "scale": 1.2, "color": "#1f222b", "stipple": "gray50"},
            {"x": 200, "y": 180, "speed": 0.15, "scale": 0.9, "color": "#1d2028", "stipple": "gray50"},
            {"x": 400, "y": 280, "speed": 0.25, "scale": 1.1, "color": "#21252f", "stipple": "gray50"},
            {"x": -100, "y": 350, "speed": 0.3, "scale": 1.0, "color": "#242934", "stipple": "gray25"},
            {"x": 300, "y": 60, "speed": 0.1, "scale": 0.7, "color": "#1c1f26", "stipple": "gray50"}
        ]
        
        for c in cloud_configs:
            x, y = c["x"], c["y"]
            s = c["scale"]
            col = c["color"]
            stip = c["stipple"]
            
            # Base oval body
            p1 = self.create_oval(x, y, x + 100*s, y + 35*s, fill=col, outline="", stipple=stip)
            # Puffs (top)
            p2 = self.create_oval(x + 15*s, y - 20*s, x + 50*s, y + 25*s, fill=col, outline="", stipple=stip)
            p3 = self.create_oval(x + 40*s, y - 15*s, x + 80*s, y + 25*s, fill=col, outline="", stipple=stip)
            
            self.clouds.append({
                "parts": [p1, p2, p3],
                "speed": c["speed"]
            })

    def animate(self):
        # Move Particles
        for p in self.particles:
            self.move(p["id"], p["dx"] * p["speed_factor"], p["dy"] * p["speed_factor"])
            coords = self.coords(p["id"])
            if not coords: continue
            
            # Wrap around boundaries
            if coords[0] < -5: self.move(p["id"], self.width + 10, 0)
            elif coords[2] > self.width + 5: self.move(p["id"], -self.width - 10, 0)
            
            if coords[1] < -5: self.move(p["id"], 0, self.height + 10)
            elif coords[3] > self.height + 5: self.move(p["id"], 0, -self.height - 10)
            
            # Twinkle
            if random.random() < 0.01: # Slower twinkle
                current_fill = self.itemcget(p["id"], "fill")
                self.itemconfig(p["id"], fill="#1a1c23" if current_fill != "#1a1c23" else p["color"])

        # Move Fluffy Clouds
        for c in self.clouds:
            for part in c["parts"]:
                self.move(part, c["speed"], 0)
            
            # Wrap wrap logic
            first_part_coords = self.coords(c["parts"][0])
            if first_part_coords and first_part_coords[0] > self.width + 50:
                for part in c["parts"]:
                    self.move(part, -self.width - 250, 0)
                
        self.after(50, self.animate)

class InstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Thunderstorm Billing Setup")
        self.geometry("600x450")
        self.resizable(False, False)
        
        # Set main window background strictly to match space so text bounding boxes blend in
        self.configure(fg_color="#1a1c23")
        
        # Background Animation
        self.bg_canvas = SpaceCanvas(self, width=600, height=450)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Variables
        default_path = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Thunderstorm Billing")
        self.install_dir = ctk.StringVar(value=default_path)
        
        self.create_widgets()
        
    def create_widgets(self):
        # Draw a translucent overlay on the canvas for the sidebar area to separate it
        self.bg_canvas.create_rectangle(0, 0, 180, 450, fill="#13151b", outline="", stipple="gray50")
        
        # Sidebar Elements
        self.logo_label = ctk.CTkLabel(self, text="⚡", font=("Arial", 60), fg_color="transparent")
        self.logo_label.place(x=90, y=90, anchor="center")
        
        self.title_label = ctk.CTkLabel(self, text="Thunderstorm\nBilling", font=("Arial", 18, "bold"), fg_color="transparent")
        self.title_label.place(x=90, y=170, anchor="center")
        
        self.status_label = ctk.CTkLabel(self, text="Version 1.0.2", font=("Arial", 11), text_color="gray", fg_color="transparent")
        self.status_label.place(x=90, y=410, anchor="center")
        
        # Main Content Elements
        # Using exact placement to avoid massive frames blocking the background
        self.title_main = ctk.CTkLabel(self, text="Installation Setup", font=("Arial", 32, "bold"), text_color="white", fg_color="transparent")
        self.title_main.place(x=220, y=40, anchor="nw")
        
        self.choose_label = ctk.CTkLabel(self, text="Choose installation folder:", font=("Arial", 14), text_color="white", fg_color="transparent")
        self.choose_label.place(x=220, y=120, anchor="nw")
        
        self.path_entry = ctk.CTkEntry(self, textvariable=self.install_dir, width=240, fg_color="#22252e", border_color="#333845", text_color="white")
        self.path_entry.place(x=220, y=150, anchor="nw")
        
        self.browse_btn = ctk.CTkButton(self, text="Browse", width=80, command=self.browse_folder, fg_color="#1d72b8")
        self.browse_btn.place(x=470, y=150, anchor="nw")
        
        self.info_label = ctk.CTkLabel(self, 
                                     text="The setup will install Thunderstorm Billing and create a desktop shortcut for quick access.", 
                                     wraplength=320, justify="left", font=("Arial", 14), text_color="#cbd5e1", fg_color="transparent")
        self.info_label.place(x=220, y=210, anchor="nw")
        
        # Progress Bar (initially hidden)
        self.progress = ctk.CTkProgressBar(self, width=330, fg_color="#22252e", progress_color="#1d72b8")
        self.progress.set(0)
        
        self.cancel_btn = ctk.CTkButton(self, text="Cancel", fg_color="#4b5563", width=90, command=self.quit, height=40)
        self.cancel_btn.place(x=350, y=370, anchor="nw")
        
        self.install_btn = ctk.CTkButton(self, text="Install Now", command=self.start_install, font=("Arial", 14, "bold"), height=40, fg_color="#1d72b8")
        self.install_btn.place(x=450, y=370, anchor="nw")

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
        
        self.progress.place(x=220, y=290, anchor="nw")
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
            
            # Restart Application
            try:
                exe_name = "Thunderstorm Billing.exe"
                if not getattr(sys, 'frozen', False):
                    exe_name = "launcher.py" # For dev testing
                
                app_path = os.path.join(target_dir, exe_name)
                if os.path.exists(app_path):
                    if app_path.endswith(".py"):
                        subprocess.Popen([sys.executable, app_path], cwd=target_dir)
                    else:
                        os.startfile(app_path)
                    print(f"Restarting app from {app_path}")
            except Exception as ree:
                print(f"Failed to restart app: {ree}")

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
