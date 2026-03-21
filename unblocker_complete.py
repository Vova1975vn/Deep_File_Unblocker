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
import win32api
import win32con
import ntsecuritycon as con

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
        self.root.title("Deep Unblocker & Ownership Fixer - Developed by Dr. Vova")
        self.root.geometry("850x700")
        
        # State
        self.monitor_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.is_monitoring = False
        self.stats_fixed = 0
        
        self._build_ui()

    def _build_ui(self):
        # 1. Header
        lbl_title = ttk.Label(self.root, text="File Permission & Ownership Fixer", font=("Segoe UI", 14, "bold"))
        lbl_title.pack(pady=(15, 5))
        
        lbl_desc = ttk.Label(self.root, text="Fixes 'Protected View', Takes Ownership, and Resets Permissions.", font=("Segoe UI", 10))
        lbl_desc.pack(pady=(0, 15))

        # 2. Monitor Section
        frame_mon = ttk.LabelFrame(self.root, text="Automatic Monitoring", padding=15)
        frame_mon.pack(fill="x", padx=20, pady=5)
        
        frame_input = ttk.Frame(frame_mon)
        frame_input.pack(fill="x", pady=5)
        ttk.Entry(frame_input, textvariable=self.monitor_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_input, text="Browse...", command=self.browse_folder).pack(side="right")
        
        self.btn_toggle_monitor = ttk.Button(frame_mon, text="START AUTO-MONITORING", command=self.toggle_monitoring)
        self.btn_toggle_monitor.pack(fill="x", pady=10)
        
        self.lbl_mon_status = ttk.Label(frame_mon, text="Status: Inactive", foreground="gray")
        self.lbl_mon_status.pack(anchor="w")

        # 3. Manual Section
        frame_manual = ttk.LabelFrame(self.root, text="Manual Deep Fix", padding=15)
        frame_manual.pack(fill="x", padx=20, pady=10)
        
        lbl_manual = ttk.Label(frame_manual, text="Select a file to Unblock + Take Ownership + Grant Full Control:", foreground="blue")
        lbl_manual.pack(anchor="w", pady=(0,5))
        
        ttk.Button(frame_manual, text="Select File to Fix", command=self.manual_select_file).pack(fill="x")
        
        # 4. Log Window
        frame_log = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        frame_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.txt_log = scrolledtext.ScrolledText(frame_log, state="disabled", font=("Arial", 9), height=10)
        self.txt_log.pack(fill="both", expand=True)

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
        
        self.txt_log.tag_config("success", foreground="green")
        self.txt_log.tag_config("error", foreground="red")
        
        self.txt_log.insert(tk.END, full_msg + "\n", tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def toggle_monitoring(self):
        if not self.is_monitoring:
            path = self.monitor_path.get()
            if not os.path.exists(path):
                messagebox.showerror("Error", "Folder does not exist.")
                return
            self.is_monitoring = True
            self.btn_toggle_monitor.config(text="STOP AUTO-MONITORING")
            self.lbl_mon_status.config(text="Status: Active", foreground="green")
            self.log_msg(f"Monitoring started: {path}", "INFO")
            threading.Thread(target=self.monitor_loop, args=(path,), daemon=True).start()
        else:
            self.is_monitoring = False
            self.btn_toggle_monitor.config(text="START AUTO-MONITORING")
            self.lbl_mon_status.config(text="Status: Inactive", foreground="gray")
            self.log_msg("Monitoring stopped.", "INFO")

    def monitor_loop(self, folder_path):
        while self.is_monitoring:
            try:
                for root, _, files in os.walk(folder_path):
                    if not self.is_monitoring: break
                    for name in files:
                        self.process_file(os.path.join(root, name), manual=False)
                time.sleep(3)
            except Exception as e:
                self.log_msg(f"Monitor error: {e}", "ERROR")
                time.sleep(5)

    def manual_select_file(self):
        f = filedialog.askopenfilename(filetypes=[("All Files", "*.*")])
        if f:
            self.process_file(f, manual=True)

    # --- CORE FIXING LOGIC ---
    def process_file(self, path, manual=False):
        filename = os.path.basename(path)
        zone_id = f"{path}:Zone.Identifier"
        needs_fix = False
        
        # Check 1: Does it have Mark of the Web?
        if os.path.exists(zone_id):
            needs_fix = True

        # Check 2: Manual override always attempts fix (to fix permissions)
        if manual:
            needs_fix = True

        if needs_fix:
            try:
                # A. Unblock (Remove Zone.Identifier)
                if os.path.exists(zone_id):
                    os.remove(zone_id)
                    self.log_msg(f"Unblocked: {filename}", "INFO")

                # B. Take Ownership (Set Owner to Current User)
                self.take_ownership(path)
                
                # C. Grant Full Control (Add ACE for Current User)
                self.grant_full_control(path)
                
                self.log_msg(f"SUCCESS: Fixed Permissions & Owner for '{filename}'", "SUCCESS")
                
                if manual:
                    messagebox.showinfo("Success", f"Deep Fix Complete!\n\nFile: {filename}\n- Unblocked\n- Owner Set to You\n- Full Control Granted")
            
            except PermissionError:
                msg = f"LOCKED: Close '{filename}' in Word/Excel first!"
                self.log_msg(msg, "ERROR")
                if manual: messagebox.showerror("File Locked", msg)
            except Exception as e:
                self.log_msg(f"Error on '{filename}': {e}", "ERROR")
                if manual: messagebox.showerror("Error", str(e))
        
        elif manual:
             self.log_msg(f"File appears safe: {filename}", "INFO")
             messagebox.showinfo("Info", "File is already unblocked.")

    def get_current_user_sid(self):
        """Returns the SID of the currently logged in user"""
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        return user_sid

    def take_ownership(self, path):
        """Forces the current user to become the owner"""
        try:
            user_sid = self.get_current_user_sid()
            sd = win32security.SECURITY_DESCRIPTOR()
            sd.SetSecurityDescriptorOwner(user_sid, False)
            # OWNER_SECURITY_INFORMATION requires special privilege, usually available to Admin
            win32security.SetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION, sd)
        except Exception as e:
            # If this fails, we might just not have SeTakeOwnershipPrivilege enabled, but often works if Admin
            print(f"Ownership warning: {e}")

    def grant_full_control(self, path):
        """Adds a specific rule giving Current User 'Full Control'"""
        try:
            user_sid = self.get_current_user_sid()
            
            # Get existing DACL
            sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
            dacl = sd.GetSecurityDescriptorDacl()
            if dacl is None:
                dacl = win32security.ACL()
            
            # Add 'Allowed' ACE for Current User with FULL ACCESS
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, user_sid)
            
            # Apply it back
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)
        except Exception as e:
            raise e

# --- ENTRY POINT & UAC CHECK ---
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
        # Re-launch as Admin
        if getattr(sys, 'frozen', False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
        sys.exit()