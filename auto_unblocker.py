import os
import sys
import time
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import ctypes
import win32security

# --- CONFIGURATION ---
LOG_FILENAME = f"autofix_log_{datetime.now().strftime('%Y%m%d')}.txt"
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode='a',
    encoding='utf-8', 
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class AutoUnblockerApp:
    def __init__(self, root):
        self.root = root
        # [UPDATED] Title bar with your signature
        self.root.title("Auto-Unblocker & Office Fixer - Developed by Dr. Vova")
        self.root.geometry("800x650")
        
        # --- State Variables ---
        self.monitor_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.is_monitoring = False
        self.stats_fixed = 0
        
        self._build_ui()

    def _build_ui(self):
        # 1. Header
        lbl_title = ttk.Label(self.root, text="Protected View Remover", font=("Segoe UI", 14, "bold"))
        lbl_title.pack(pady=(15, 5))
        
        lbl_desc = ttk.Label(self.root, text="Automatically detects and unblocks files to remove the yellow 'Protected View' bar.", font=("Segoe UI", 10))
        lbl_desc.pack(pady=(0, 15))

        # 2. Monitor Section
        frame_mon = ttk.LabelFrame(self.root, text="Automatic Monitoring", padding=15)
        frame_mon.pack(fill="x", padx=20, pady=5)
        
        lbl_mon = ttk.Label(frame_mon, text="Monitored Folder (e.g., Downloads):")
        lbl_mon.pack(anchor="w")
        
        frame_input = ttk.Frame(frame_mon)
        frame_input.pack(fill="x", pady=5)
        
        ttk.Entry(frame_input, textvariable=self.monitor_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_input, text="Browse...", command=self.browse_folder).pack(side="right")
        
        self.btn_toggle_monitor = ttk.Button(frame_mon, text="START AUTO-MONITORING", command=self.toggle_monitoring)
        self.btn_toggle_monitor.pack(fill="x", pady=10)
        
        self.lbl_mon_status = ttk.Label(frame_mon, text="Status: Inactive", foreground="gray")
        self.lbl_mon_status.pack(anchor="w")

        # 3. Manual Section
        frame_manual = ttk.LabelFrame(self.root, text="Manual Fix (Single File)", padding=15)
        frame_manual.pack(fill="x", padx=20, pady=10)
        
        ttk.Button(frame_manual, text="Select Specific File to Unblock", command=self.manual_select_file).pack(fill="x")
        
        # 4. Log Window
        frame_log = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        frame_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.txt_log = scrolledtext.ScrolledText(frame_log, state="disabled", font=("Arial", 9), height=10)
        self.txt_log.pack(fill="both", expand=True)

    # --- Actions ---
    def browse_folder(self):
        d = filedialog.askdirectory()
        if d: self.monitor_path.set(d)

    def log_msg(self, msg, type="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}"
        logging.info(full_msg)
        
        self.txt_log.config(state="normal")
        tag = "norm"
        if type == "SUCCESS": tag = "success"
        elif type == "ERROR": tag = "error"
        elif type == "WARN": tag = "warn"
        
        self.txt_log.tag_config("success", foreground="green")
        self.txt_log.tag_config("error", foreground="red")
        self.txt_log.tag_config("warn", foreground="orange")
        
        self.txt_log.insert(tk.END, full_msg + "\n", tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    # --- Automatic Monitoring Logic ---
    def toggle_monitoring(self):
        if not self.is_monitoring:
            path = self.monitor_path.get()
            if not os.path.exists(path):
                messagebox.showerror("Error", "Folder does not exist.")
                return
            
            self.is_monitoring = True
            self.btn_toggle_monitor.config(text="STOP AUTO-MONITORING")
            self.lbl_mon_status.config(text="Status: Active - Scanning...", foreground="green")
            self.log_msg(f"Started monitoring: {path}", "INFO")
            threading.Thread(target=self.monitor_loop, args=(path,), daemon=True).start()
        else:
            self.is_monitoring = False
            self.btn_toggle_monitor.config(text="START AUTO-MONITORING")
            self.lbl_mon_status.config(text="Status: Inactive", foreground="gray")
            self.log_msg("Stopped monitoring.", "WARN")

    def monitor_loop(self, folder_path):
        while self.is_monitoring:
            try:
                for root, _, files in os.walk(folder_path):
                    if not self.is_monitoring: break
                    for name in files:
                        full_path = os.path.join(root, name)
                        self.check_and_fix(full_path, manual=False)
                time.sleep(3)
            except Exception as e:
                self.log_msg(f"Monitor Error: {e}", "ERROR")
                time.sleep(5)

    # --- Manual Logic ---
    def manual_select_file(self):
        f = filedialog.askopenfilename(filetypes=[("Office Files", "*.doc;*.docx;*.xls;*.xlsx;*.ppt;*.pptx"), ("All Files", "*.*")])
        if f:
            self.check_and_fix(f, manual=True)

    # --- The Fix Core ---
    def check_and_fix(self, path, manual=False):
        zone_id = f"{path}:Zone.Identifier"
        filename = os.path.basename(path)
        
        if os.path.exists(zone_id):
            try:
                # 1. Unblock
                os.remove(zone_id)
                
                # 2. Explicit Permissions
                sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
                sd.SetSecurityDescriptorControl(win32security.SE_DACL_PROTECTED, win32security.SE_DACL_PROTECTED)
                win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)
                
                self.stats_fixed += 1
                self.log_msg(f"FIXED: {filename}", "SUCCESS")
                
                # [UPDATED] Show Success Message
                if manual:
                    messagebox.showinfo("Process Finished Successfully", 
                                      f"Success!\n\nThe file '{filename}' has been unblocked.\nYou can now open it.")
                    
            except PermissionError:
                msg = f"LOCKED: Could not fix '{filename}'."
                self.log_msg(msg, "ERROR")
                # [UPDATED] Show Failure Message
                if manual:
                    messagebox.showerror("Process Failed", 
                                       f"Failed to unblock '{filename}'.\n\nThe file is currently OPEN in another program (like Word or Excel).\n\nPlease CLOSE the file and try again.")
            except Exception as e:
                self.log_msg(f"Error on '{filename}': {e}", "ERROR")
                if manual:
                    messagebox.showerror("Process Failed", f"An unexpected error occurred:\n{e}")
        
        elif manual:
             # [UPDATED] Show Already Safe Message
             self.log_msg(f"File is already safe: {filename}", "INFO")
             messagebox.showinfo("Process Finished", f"No action needed.\n\nThe file '{filename}' is already unblocked and safe.")

# --- ENTRY POINT ---
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if __name__ == "__main__":
    if is_admin():
        root = tk.Tk()
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass
        app = AutoUnblockerApp(root)
        root.mainloop()
    else:
        if getattr(sys, 'frozen', False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
        sys.exit()