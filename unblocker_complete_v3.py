import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import subprocess
import ctypes

# --- LOGGING SETUP ---
LOG_FILENAME = f"unblock_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_admin():
    """Checks if the script is running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class FileUnblockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deep File Unblocker & Permission Fixer - ver 2.0 (Admin)")
        self.root.geometry("750x600")
        
        # --- State Variables ---
        self.target_dir = tk.StringVar()
        self.dry_run = tk.BooleanVar(value=True)
        self.total_items = 0
        self.processed_items = 0
        self.success_count = 0
        self.error_count = 0
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
        ttk.Button(frame_top, text="Browse Folder", command=self.browse_folder).pack(side="right", padx=(2, 0))
        ttk.Button(frame_top, text="Select File", command=self.browse_file).pack(side="right", padx=(5, 2))
        
        # 2. Options
        frame_opts = ttk.Frame(self.root, padding=10)
        frame_opts.pack(fill="x", padx=5)
        ttk.Checkbutton(frame_opts, text="Dry Run (Simulate only)", variable=self.dry_run).pack(side="left")
        
        # 3. Control Buttons
        frame_ctrl = ttk.Frame(self.root, padding=10)
        frame_ctrl.pack(fill="x", padx=5)
        
        self.btn_start = ttk.Button(frame_ctrl, text="START", command=self.start_thread, width=12)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_pause = ttk.Button(frame_ctrl, text="PAUSE", command=self.toggle_pause, state="disabled", width=12)
        self.btn_pause.pack(side="left", padx=5)
        
        self.btn_cancel = ttk.Button(frame_ctrl, text="CANCEL", command=self.cancel_process, state="disabled", width=12)
        self.btn_cancel.pack(side="left", padx=5)
        
        self.btn_exit = ttk.Button(frame_ctrl, text="EXIT", command=self.root.destroy, width=12)
        self.btn_exit.pack(side="right", padx=5)

        self.btn_log = ttk.Button(frame_ctrl, text="OPEN LOG", command=self.open_log_file, width=12)
        self.btn_log.pack(side="right", padx=5)

        # 4. Progress Bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=10)
        
        self.lbl_status = ttk.Label(self.root, text="Ready. Running as Administrator.")
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

    def browse_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.target_dir.set(file_path)

    def open_log_file(self):
        if os.path.exists(LOG_FILENAME):
            os.startfile(LOG_FILENAME)
        else:
            messagebox.showinfo("Log Not Found", "No log file has been generated yet.")

    def log_msg(self, message, level="INFO"):
        if level == "ERROR":
            logging.error(message)
        else:
            logging.info(message)
            
        # Safely update Tkinter UI from background thread
        self.root.after(0, self._append_log_ui, f"[{level}] {message}\n")

    def _append_log_ui(self, msg):
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, msg)
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
            self.pause_event.set()  # Unpause to allow thread to exit
            self.log_msg("Cancelling process...")

    def start_thread(self):
        target_path = self.target_dir.get()
        if not os.path.exists(target_path):
            messagebox.showerror("Error", "Invalid File or Directory Path")
            return
        
        # Reset UI and state
        self.txt_log.config(state="normal")
        self.txt_log.delete(1.0, tk.END)
        self.txt_log.config(state="disabled")
        
        self.progress['value'] = 0
        self.stop_event.clear()
        self.pause_event.set()
        self.processed_items = 0
        self.success_count = 0
        self.error_count = 0
        
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="PAUSE")
        self.btn_cancel.config(state="normal")
        self.dry_run_active = self.dry_run.get()

        # Start background worker
        t = threading.Thread(target=self.process_logic, args=(target_path,), daemon=True)
        t.start()

    def process_logic(self, target_path):
        self.log_msg(f"Starting Scan: {target_path}")
        self.log_msg(f"Mode: {'DRY RUN (Simulation)' if self.dry_run_active else 'LIVE EXECUTION'}")

        # --- Handle Single File ---
        if os.path.isfile(target_path):
            self.total_items = 1
            self.root.after(0, lambda: self.lbl_status.config(text="Processing single file..."))
            
            if not self.stop_event.is_set():
                self.perform_file_ops(target_path)
                self.processed_items = 1
                self.root.after(0, self._update_progress_ui, 100, 1, 1)
            
            self.finish_process(cancelled=self.stop_event.is_set())
            return

        # --- Handle Directory ---
        self.root.after(0, lambda: self.lbl_status.config(text="Counting files..."))
        total_files = 0
        for _, dirs, files in os.walk(target_path):
            if self.stop_event.is_set(): break
            total_files += len(dirs) + len(files)
        
        self.total_items = total_files
        self.log_msg(f"Total items found: {total_files}")
        self.root.after(0, lambda: self.lbl_status.config(text="Processing..."))
        
        for root, dirs, files in os.walk(target_path):
            all_items = dirs + files
            
            for name in all_items:
                if self.stop_event.is_set():
                    self.finish_process(cancelled=True)
                    return

                self.pause_event.wait()

                full_path = os.path.join(root, name)
                self.perform_file_ops(full_path)
                
                self.processed_items += 1
                
                # Update UI periodically to prevent Tkinter from choking
                if self.processed_items % 10 == 0 or self.processed_items == self.total_items:
                    progress_pct = (self.processed_items / self.total_items) * 100 if self.total_items > 0 else 100
                    self.root.after(0, self._update_progress_ui, progress_pct, self.processed_items, self.total_items)

        self.finish_process(cancelled=False)

    def _update_progress_ui(self, pct, current, total):
        self.progress['value'] = pct
        self.lbl_status.config(text=f"Processing: {current}/{total}")

    def perform_file_ops(self, path):
        try:
            # 1. Remove Zone.Identifier (Protected View)
            zone_stream = f"{path}:Zone.Identifier"
            if not self.dry_run_active:
                try:
                    os.remove(zone_stream)
                    self.log_msg(f"Unblocked: {os.path.basename(path)}")
                except FileNotFoundError:
                    pass # File wasn't blocked

            # 2. Reset Permissions using native Windows tools
            if not self.dry_run_active:
                hide_window = 0x08000000 # Prevents black CMD boxes from flashing
                
                # --- THE FIX: Convert forward slashes (/) to Windows backslashes (\) ---
                win_path = os.path.normpath(path)
                
                # Take Ownership
                takeown_cmd = ["takeown", "/F", win_path, "/A"]
                result_takeown = subprocess.run(takeown_cmd, capture_output=True, text=True, creationflags=hide_window)
                if result_takeown.returncode != 0:
                    self.log_msg(f"Takeown failed on {os.path.basename(path)}: {result_takeown.stderr.strip()}", level="ERROR")
                
                # Reset Permissions
                icacls_cmd = ["icacls", win_path, "/grant", "Administrators:F", "/C", "/Q"]
                result_icacls = subprocess.run(icacls_cmd, capture_output=True, text=True, creationflags=hide_window)
                if result_icacls.returncode != 0:
                    self.log_msg(f"Icacls failed on {os.path.basename(path)}: {result_icacls.stderr.strip()}", level="ERROR")
            
            self.success_count += 1
            
        except Exception as e:
            self.error_count += 1
            self.log_msg(f"Error on {os.path.basename(path)}: {str(e)}", level="ERROR")

    def finish_process(self, cancelled):
        self.is_running = False
        self.root.after(0, lambda: self._reset_ui_state(cancelled))

    def _reset_ui_state(self, cancelled):
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        
        report = (
            f"Total Processed: {self.processed_items}\n"
            f"Successes: {self.success_count}\n"
            f"Errors: {self.error_count}\n\n"
            f"Check the log file for detailed error messages."
        )

        if cancelled:
            self.lbl_status.config(text="Operation Cancelled.")
            self.log_msg("--- PROCESS CANCELLED ---")
            messagebox.showwarning("Stopped", f"Process was cancelled by user.\n\n{report}")
        else:
            self.lbl_status.config(text="Done.")
            self.progress['value'] = 100
            self.log_msg("--- PROCESS COMPLETE ---")
            messagebox.showinfo("Finished", f"Operation completed successfully.\n\n{report}")

if __name__ == "__main__":
    if is_admin():
        # --- Run the application if already Admin ---
        root = tk.Tk()
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1) # Make UI crisp on high-DPI screens
        except:
            pass
            
        app = FileUnblockerApp(root)
        root.mainloop()
    else:
        # --- Relaunch the script with Admin rights ---
        # Note: In Python 3, sys.argv[0] is the script name. We re-run it via Windows ShellExecute.
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)