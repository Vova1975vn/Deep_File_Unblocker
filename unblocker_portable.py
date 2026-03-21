import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import ctypes
import win32security

# --- CONFIGURATION & SETUP ---
# Generate a unique log file name based on start time
LOG_FILENAME = f"unblock_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logging to write to file
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FileUnblockerApp:
    def __init__(self, root):
        self.root = root
        # --- TITLE BAR UPDATE ---
        self.root.title("Portable File Unblocker & Fixer - Developed by Dr. Vova")
        self.root.geometry("720x580")
        
        # Variables
        self.target_dir = tk.StringVar()
        self.dry_run = tk.BooleanVar(value=True)
        self.total_items = 0
        self.processed_items = 0
        
        # Thread Control
        self.pause_event = threading.Event()
        self.pause_event.set() # True means "Running"
        self.stop_event = threading.Event()
        
        self._build_ui()

    def _build_ui(self):
        # 1. Header / Selection
        lbl_instr = ttk.Label(self.root, text="Select a folder to recursively unblock files and fix permissions.", font=("Segoe UI", 10))
        lbl_instr.pack(pady=(10, 5), padx=10, anchor="w")

        frame_sel = ttk.LabelFrame(self.root, text="Target Directory", padding=10)
        frame_sel.pack(fill="x", padx=10, pady=5)
        
        entry = ttk.Entry(frame_sel, textvariable=self.target_dir)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_sel, text="Browse...", command=self.browse_folder).pack(side="right")
        
        # 2. Options
        frame_opts = ttk.Frame(self.root)
        frame_opts.pack(fill="x", padx=15, pady=5)
        
        chk = ttk.Checkbutton(frame_opts, text="Dry Run Mode (Simulate without modifying files)", variable=self.dry_run)
        chk.pack(side="left")

        # 3. Action Buttons
        frame_btns = ttk.Frame(self.root, padding=10)
        frame_btns.pack(fill="x")
        
        self.btn_start = ttk.Button(frame_btns, text="START PROCESSING", command=self.start_thread)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_pause = ttk.Button(frame_btns, text="PAUSE", command=self.toggle_pause, state="disabled")
        self.btn_pause.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_cancel = ttk.Button(frame_btns, text="CANCEL", command=self.cancel_process, state="disabled")
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=5)

        # 4. Progress
        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=15, pady=(10, 5))
        
        self.lbl_status = ttk.Label(self.root, text="Waiting for user input...", font=("Segoe UI", 9))
        self.lbl_status.pack(anchor="w", padx=15)

        # 5. Log Output
        frame_log = ttk.LabelFrame(self.root, text="Execution Log", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.txt_log = scrolledtext.ScrolledText(frame_log, state="disabled", font=("Consolas", 9))
        self.txt_log.pack(fill="both", expand=True)

    # --- GUI Helpers ---
    def browse_folder(self):
        d = filedialog.askdirectory()
        if d: self.target_dir.set(d)

    def log_msg(self, msg, level="INFO"):
        # File Log
        if level == "ERROR": logging.error(msg)
        else: logging.info(msg)
        
        # GUI Log
        self.txt_log.config(state="normal")
        tag = "err" if level == "ERROR" else "norm"
        self.txt_log.tag_config("err", foreground="red")
        self.txt_log.insert(tk.END, f"[{level}] {msg}\n", tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text="RESUME")
            self.lbl_status.config(text="Status: Paused by user")
        else:
            self.pause_event.set()
            self.btn_pause.config(text="PAUSE")
            self.lbl_status.config(text="Status: Resuming...")

    def cancel_process(self):
        if messagebox.askyesno("Stop", "Abort current operation?"):
            self.stop_event.set()
            self.pause_event.set() # Unpause if paused so we can exit loop

    # --- Threading Logic ---
    def start_thread(self):
        path = self.target_dir.get()
        if not os.path.isdir(path):
            messagebox.showerror("Error", "Please select a valid directory first.")
            return

        # UI Lock
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="PAUSE")
        self.btn_cancel.config(state="normal")
        self.txt_log.config(state="normal"); self.txt_log.delete(1.0, tk.END); self.txt_log.config(state="disabled")
        
        self.stop_event.clear()
        self.pause_event.set()
        self.dry_run_active = self.dry_run.get()
        
        # Start Worker
        threading.Thread(target=self.worker, args=(path,), daemon=True).start()

    def worker(self, root_path):
        self.log_msg(f"STARTED processing: {root_path}")
        self.log_msg(f"Mode: {'SIMULATION (Dry Run)' if self.dry_run_active else 'LIVE (Changes Enabled)'}")

        # 1. Count
        self.lbl_status.config(text="Scanning file count...")
        total = 0
        for _, dirs, files in os.walk(root_path):
            if self.stop_event.is_set(): break
            total += len(dirs) + len(files)
        self.total_items = total
        self.processed_items = 0
        
        # 2. Process
        self.lbl_status.config(text="Processing...")
        for root, dirs, files in os.walk(root_path):
            if self.stop_event.is_set(): break
            
            for name in dirs + files:
                if self.stop_event.is_set(): break
                self.pause_event.wait() # Pause check

                full_path = os.path.join(root, name)
                self.process_item(full_path)
                
                self.processed_items += 1
                
                # Update UI occasionally
                if self.processed_items % 5 == 0:
                    pct = (self.processed_items / self.total_items) * 100
                    self.root.after(0, lambda p=pct: self.progress.configure(value=p))
                    self.root.after(0, lambda i=self.processed_items: self.lbl_status.configure(text=f"Processed: {i} / {self.total_items}"))

        # Finish
        is_cancelled = self.stop_event.is_set()
        self.root.after(0, lambda: self.reset_ui(is_cancelled))

    def process_item(self, path):
        try:
            # Unblock
            zone_id = f"{path}:Zone.Identifier"
            if os.path.exists(zone_id):
                if not self.dry_run_active:
                    os.remove(zone_id)
                self.log_msg(f"Unblocked: {os.path.basename(path)}")
            
            # Permissions
            if not self.dry_run_active:
                sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
                sd.SetSecurityDescriptorControl(win32security.SE_DACL_PROTECTED, win32security.SE_DACL_PROTECTED)
                win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)

        except Exception as e:
            self.log_msg(f"Error ({os.path.basename(path)}): {e}", "ERROR")

    def reset_ui(self, cancelled):
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        
        if cancelled:
            self.lbl_status.config(text="Operation Cancelled")
            self.log_msg("--- ABORTED BY USER ---")
        else:
            self.progress['value'] = 100
            self.lbl_status.config(text="Complete")
            self.log_msg("--- FINISHED ---")
            messagebox.showinfo("Done", "Processing complete.")

# --- ENTRY POINT & UAC CHECK ---
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if __name__ == "__main__":
    # 1. If we are Admin, run the App
    if is_admin():
        root = tk.Tk()
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass
        
        app = FileUnblockerApp(root)
        root.mainloop()
    
    # 2. If NOT Admin, restart ourselves with elevation
    else:
        if getattr(sys, 'frozen', False):
            executable = sys.executable
            args = sys.argv[1:]
        else:
            executable = sys.executable
            args = [sys.argv[0]] + sys.argv[1:]
            args[0] = f'"{args[0]}"'

        params = " ".join(args)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
        sys.exit()