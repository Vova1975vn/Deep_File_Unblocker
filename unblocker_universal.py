import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import ctypes
import win32security

# --- CONFIGURATION ---
# Generate a log file name. 
LOG_FILENAME = f"unblock_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# [CRITICAL UPDATE] encoding='utf-8' is required to support Vietnamese/Japanese/etc filenames
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode='a',
    encoding='utf-8',  # <--- THIS FIXES THE CRASH ON NON-ENGLISH NAMES
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FileUnblockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal File Unblocker - Developed by Dr. Vova")
        self.root.geometry("750x620")
        
        # Variables
        self.target_path = tk.StringVar()
        self.is_folder_mode = tk.BooleanVar(value=True) 
        self.dry_run = tk.BooleanVar(value=True)
        self.total_items = 0
        self.processed_items = 0
        
        # Thread Control
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_event = threading.Event()
        
        self._build_ui()

    def _build_ui(self):
        # 1. Instructions
        lbl_instr = ttk.Label(self.root, text="Supports all languages and special characters.", font=("Segoe UI", 10))
        lbl_instr.pack(pady=(10, 5), padx=10, anchor="w")

        # 2. Selection Area
        frame_sel = ttk.LabelFrame(self.root, text="Target Selection", padding=10)
        frame_sel.pack(fill="x", padx=10, pady=5)
        
        entry = ttk.Entry(frame_sel, textvariable=self.target_path)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(frame_sel, text="Select Folder", command=self.browse_folder).pack(side="right", padx=2)
        ttk.Button(frame_sel, text="Select Single File", command=self.browse_file).pack(side="right", padx=2)
        
        # 3. Options
        frame_opts = ttk.Frame(self.root)
        frame_opts.pack(fill="x", padx=15, pady=5)
        
        chk = ttk.Checkbutton(frame_opts, text="Dry Run (Check this to Simulate only)", variable=self.dry_run)
        chk.pack(side="left")

        # 4. Action Buttons
        frame_btns = ttk.Frame(self.root, padding=10)
        frame_btns.pack(fill="x")
        
        self.btn_start = ttk.Button(frame_btns, text="START FIX", command=self.start_thread)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_pause = ttk.Button(frame_btns, text="PAUSE", command=self.toggle_pause, state="disabled")
        self.btn_pause.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_cancel = ttk.Button(frame_btns, text="CANCEL", command=self.cancel_process, state="disabled")
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=5)

        # 5. Progress
        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=15, pady=(10, 5))
        
        self.lbl_status = ttk.Label(self.root, text="Ready.", font=("Segoe UI", 9))
        self.lbl_status.pack(anchor="w", padx=15)

        # 6. Log
        frame_log = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Changed font to 'Arial' which has better Unicode support than 'Consolas'
        self.txt_log = scrolledtext.ScrolledText(frame_log, state="disabled", font=("Arial", 9))
        self.txt_log.pack(fill="both", expand=True)

    # --- Actions ---
    def browse_folder(self):
        d = filedialog.askdirectory()
        if d: 
            self.target_path.set(d)
            self.is_folder_mode.set(True)

    def browse_file(self):
        # Added .doc, .xls, .ppt for older file support
        f = filedialog.askopenfilename(filetypes=[
            ("All Files", "*.*"), 
            ("Office Files", "*.docx;*.doc;*.xlsx;*.xls;*.pptx;*.ppt;*.pdf")
        ])
        if f: 
            self.target_path.set(f)
            self.is_folder_mode.set(False)

    def log_msg(self, msg, level="INFO"):
        # Log to file (safe with utf-8 encoding)
        if level == "ERROR": logging.error(msg)
        else: logging.info(msg)
        
        # Log to GUI
        self.txt_log.config(state="normal")
        tag = "err" if level == "ERROR" else ("success" if "SUCCESS" in msg else "norm")
        
        self.txt_log.tag_config("err", foreground="red")
        self.txt_log.tag_config("success", foreground="green")
        
        self.txt_log.insert(tk.END, f"[{level}] {msg}\n", tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text="RESUME")
            self.lbl_status.config(text="Paused")
        else:
            self.pause_event.set()
            self.btn_pause.config(text="PAUSE")
            self.lbl_status.config(text="Resuming...")

    def cancel_process(self):
        if messagebox.askyesno("Stop", "Abort current operation?"):
            self.stop_event.set()
            self.pause_event.set()

    # --- Processing Logic ---
    def start_thread(self):
        path = self.target_path.get()
        # os.path.exists works with Unicode natively in Python 3
        if not os.path.exists(path):
            messagebox.showerror("Error", "Invalid Path")
            return

        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="PAUSE")
        self.btn_cancel.config(state="normal")
        self.txt_log.config(state="normal"); self.txt_log.delete(1.0, tk.END); self.txt_log.config(state="disabled")
        
        self.stop_event.clear()
        self.pause_event.set()
        self.dry_run_active = self.dry_run.get()
        
        threading.Thread(target=self.worker, args=(path,), daemon=True).start()

    def worker(self, target):
        self.log_msg(f"Target: {target}")
        self.log_msg(f"Mode: {'SIMULATION' if self.dry_run_active else 'LIVE FIX'}")

        items_to_process = []
        if os.path.isfile(target):
            items_to_process = [target]
        else:
            self.lbl_status.config(text="Scanning directory...")
            for root, dirs, files in os.walk(target):
                if self.stop_event.is_set(): break
                for name in files:
                    items_to_process.append(os.path.join(root, name))
                for name in dirs:
                    items_to_process.append(os.path.join(root, name))

        self.total_items = len(items_to_process)
        self.processed_items = 0
        self.log_msg(f"Items found: {self.total_items}")

        self.lbl_status.config(text="Processing...")
        for full_path in items_to_process:
            if self.stop_event.is_set(): break
            self.pause_event.wait()
            
            self.process_item(full_path)
            self.processed_items += 1
            
            # UI Update Throttling
            if self.processed_items % 5 == 0 or self.total_items < 20:
                pct = (self.processed_items / self.total_items) * 100
                self.root.after(0, lambda p=pct: self.progress.configure(value=p))
                self.root.after(0, lambda i=self.processed_items: self.lbl_status.configure(text=f"Processed: {i} / {self.total_items}"))

        self.root.after(0, lambda: self.reset_ui(self.stop_event.is_set()))

    def process_item(self, path):
        fname = os.path.basename(path).lower()
        is_office = fname.endswith(('.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.pdf'))
        
        try:
            zone_id = f"{path}:Zone.Identifier"
            if os.path.exists(zone_id):
                if not self.dry_run_active:
                    try:
                        os.remove(zone_id)
                        # os.path.basename handles unicode automatically
                        display_name = os.path.basename(path) 
                        msg = f"SUCCESS: Removed Protected View from {display_name}" if is_office else f"Unblocked: {display_name}"
                        self.log_msg(msg)
                    except PermissionError:
                        self.log_msg(f"LOCKED: Close '{os.path.basename(path)}' and try again!", "ERROR")
                        return
                else:
                    msg = f"[DRY RUN] Would fix: {os.path.basename(path)}"
                    self.log_msg(msg)
            else:
                 # Logic for single file selection feedback
                if not self.is_folder_mode.get():
                     self.log_msg(f"File is already safe: {os.path.basename(path)}")

            if not self.dry_run_active and os.path.exists(path):
                if os.path.isfile(path):
                    sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
                    sd.SetSecurityDescriptorControl(win32security.SE_DACL_PROTECTED, win32security.SE_DACL_PROTECTED)
                    win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)

        except Exception as e:
            # Handle error strings that might contain unicode
            self.log_msg(f"Error: {str(e)}", "ERROR")

    def reset_ui(self, cancelled):
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        if cancelled:
            self.lbl_status.config(text="Cancelled")
            self.log_msg("--- CANCELLED ---")
        else:
            self.progress['value'] = 100
            self.lbl_status.config(text="Done")
            self.log_msg("--- FINISHED ---")
            messagebox.showinfo("Done", "Process complete.")

# --- AUTO-UAC ELEVATION ---
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if __name__ == "__main__":
    if is_admin():
        root = tk.Tk()
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass
        app = FileUnblockerApp(root)
        root.mainloop()
    else:
        if getattr(sys, 'frozen', False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
        sys.exit()