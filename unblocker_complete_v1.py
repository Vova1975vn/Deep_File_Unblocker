import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import win32security

# --- LOGGING SETUP ---
LOG_FILENAME = f"unblock_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FileUnblockerApp:
    def __init__(self, root):
        self.root = root
        # --- VERSION INFO ADDED HERE ---
        self.root.title("Deep File Unblocker & Permission Fixer - ver 1.0")
        self.root.geometry("700x550")
        
        # --- State Variables ---
        self.target_dir = tk.StringVar()
        self.dry_run = tk.BooleanVar(value=True)
        self.total_items = 0
        self.processed_items = 0
        self.is_running = False
        
        # Threading Events
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start as "not paused"
        self.stop_event = threading.Event()

        # --- UI Layout ---
        self._build_ui()

    def _build_ui(self):
        # 1. Selection Area
        frame_top = ttk.LabelFrame(self.root, text="Target Selection", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        ttk.Entry(frame_top, textvariable=self.target_dir).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_top, text="Browse Folder", command=self.browse_folder).pack(side="right")
        
        # 2. Options
        frame_opts = ttk.Frame(self.root, padding=10)
        frame_opts.pack(fill="x", padx=5)
        ttk.Checkbutton(frame_opts, text="Dry Run (Simulate only)", variable=self.dry_run).pack(side="left")
        
        # 3. Control Buttons
        frame_ctrl = ttk.Frame(self.root, padding=10)
        frame_ctrl.pack(fill="x", padx=5)
        
        self.btn_start = ttk.Button(frame_ctrl, text="START", command=self.start_thread, width=15)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_pause = ttk.Button(frame_ctrl, text="PAUSE", command=self.toggle_pause, state="disabled", width=15)
        self.btn_pause.pack(side="left", padx=5)
        
        self.btn_cancel = ttk.Button(frame_ctrl, text="CANCEL", command=self.cancel_process, state="disabled", width=15)
        self.btn_cancel.pack(side="left", padx=5)
        
        self.btn_exit = ttk.Button(frame_ctrl, text="FINISH / EXIT", command=self.root.destroy, width=15)
        self.btn_exit.pack(side="right", padx=5)

        # 4. Progress Bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=10)
        
        self.lbl_status = ttk.Label(self.root, text="Ready.")
        self.lbl_status.pack(anchor="w", padx=20)

        # 5. Log Window
        frame_log = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.txt_log = scrolledtext.ScrolledText(frame_log, height=10, state="disabled", font=("Consolas", 9))
        self.txt_log.pack(fill="both", expand=True)

    # --- Actions ---
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.target_dir.set(folder)

    def log_msg(self, message, level="INFO"):
        """Updates the GUI log and the file log."""
        if level == "ERROR":
            logging.error(message)
        else:
            logging.info(message)
            
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, f"[{level}] {message}\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text="RESUME")
            self.lbl_status.config(text="Status: Paused")
            self.log_msg("Process Paused.")
        else:
            self.pause_event.set()
            self.btn_pause.config(text="PAUSE")
            self.lbl_status.config(text="Status: Running...")
            self.log_msg("Process Resumed.")

    def cancel_process(self):
        if messagebox.askyesno("Cancel", "Are you sure you want to stop?"):
            self.stop_event.set()
            self.pause_event.set()
            self.log_msg("Cancelling process...")

    def start_thread(self):
        path = self.target_dir.get()
        if not os.path.exists(path):
            messagebox.showerror("Error", "Invalid Directory")
            return
        
        self.txt_log.config(state="normal")
        self.txt_log.delete(1.0, tk.END)
        self.txt_log.config(state="disabled")
        self.progress['value'] = 0
        self.stop_event.clear()
        self.pause_event.set()
        self.processed_items = 0
        
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="PAUSE")
        self.btn_cancel.config(state="normal")
        self.dry_run_active = self.dry_run.get()

        t = threading.Thread(target=self.process_logic, args=(path,), daemon=True)
        t.start()

    def process_logic(self, root_folder):
        self.log_msg(f"Starting Scan: {root_folder}")
        self.log_msg(f"Mode: {'DRY RUN (Simulation)' if self.dry_run_active else 'LIVE EXECUTION'}")

        self.lbl_status.config(text="Counting files...")
        total_files = 0
        for _, dirs, files in os.walk(root_folder):
            if self.stop_event.is_set(): break
            total_files += len(dirs) + len(files)
        
        self.total_items = total_files
        self.log_msg(f"Total items found: {total_files}")
        
        self.lbl_status.config(text="Processing...")
        
        for root, dirs, files in os.walk(root_folder):
            all_items = dirs + files
            
            for name in all_items:
                if self.stop_event.is_set():
                    self.finish_process(cancelled=True)
                    return

                self.pause_event.wait()

                full_path = os.path.join(root, name)
                self.perform_file_ops(full_path)
                
                self.processed_items += 1
                if self.total_items > 0:
                    progress_pct = (self.processed_items / self.total_items) * 100
                    self.progress['value'] = progress_pct
                
                if self.processed_items % 10 == 0:
                    self.lbl_status.config(text=f"Processing: {self.processed_items}/{self.total_items}")

        self.finish_process(cancelled=False)

    def perform_file_ops(self, path):
        try:
            zone_stream = f"{path}:Zone.Identifier"
            if os.path.exists(zone_stream):
                if not self.dry_run_active:
                    os.remove(zone_stream)
                self.log_msg(f"Unblocked: {os.path.basename(path)}")
            
            if not self.dry_run_active:
                sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
                sd.SetSecurityDescriptorControl(win32security.SE_DACL_PROTECTED, win32security.SE_DACL_PROTECTED)
                win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)
                 
        except Exception as e:
            self.log_msg(f"Error on {os.path.basename(path)}: {str(e)}", level="ERROR")

    def finish_process(self, cancelled):
        self.is_running = False
        self.root.after(0, lambda: self._reset_ui_state(cancelled))

    def _reset_ui_state(self, cancelled):
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        
        if cancelled:
            self.lbl_status.config(text="Operation Cancelled.")
            self.log_msg("--- PROCESS CANCELLED ---")
            messagebox.showwarning("Stopped", "Process was cancelled by user.")
        else:
            self.lbl_status.config(text="Done.")
            self.progress['value'] = 100
            self.log_msg("--- PROCESS COMPLETE ---")
            messagebox.showinfo("Finished", f"Successfully processed {self.processed_items} items.")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = FileUnblockerApp(root)
    root.mainloop()