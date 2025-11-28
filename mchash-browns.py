import matplotlib
matplotlib.use("TkAgg")

import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import os
import subprocess
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

C_SRC_DIR = os.path.join(SCRIPT_DIR, "src/c-hash")
C_MOUNT_DIR = os.path.join(SCRIPT_DIR, "mounts/c-hash")
C_MOUNT_FILE = os.path.join(C_MOUNT_DIR, "mcfrier")
C_EXECUTABLE = os.path.join(C_SRC_DIR, "fuse_mount")

RUST_SRC_DIR = os.path.join(SCRIPT_DIR, "src/rust-hash")
RUST_MOUNT_DIR = os.path.join(SCRIPT_DIR, "mounts/rust-hash")
RUST_MOUNT_FILE = os.path.join(RUST_MOUNT_DIR, "mcfrier")
RUST_EXECUTABLE = os.path.join(RUST_SRC_DIR, "target/release/fuse_mount")

# Note: 500M is the safe max for simultaneous runs on 64GB RAM.  Please reference the size chart in the README.md based on your RAM.
OPERATION_COUNTS = [100_000, 1_000_000, 10_000_000, 100_000_000, 500_000_000]

class McGui:
    def __init__(self, root):
        self.root = root
        self.root.title("McHash Browns")
        self.root.geometry("1600x1000")
        
        self.msg_queue = queue.Queue()
        self.c_results = {}    
        self.rust_results = {} 
        self.c_process = None
        self.rust_process = None
        self.is_running = False

        tk.Label(root, text="McHash Browns: C vs Rust - Hash Table (Linked List) Performance Comparison", font=("Arial", 22, "bold")).pack(pady=10)

        ctrl_frame = tk.LabelFrame(root, text="Control Center", font=("Arial", 12, "bold"))
        ctrl_frame.pack(pady=5, fill="x", padx=20)

        btn_frame = tk.Frame(ctrl_frame)
        btn_frame.pack(pady=15)
        
        self.btn_c = tk.Button(btn_frame, text="Run C Only", command=lambda: self.start_bench("C"),
                              bg="#ADD8E6", font=("Arial", 11, "bold"), width=15)
        self.btn_c.pack(side="left", padx=10)

        self.btn_rust = tk.Button(btn_frame, text="Run Rust Only", command=lambda: self.start_bench("Rust"),
                                 bg="#FFB347", font=("Arial", 11, "bold"), width=15)
        self.btn_rust.pack(side="left", padx=10)

        self.btn_race = tk.Button(btn_frame, text="⚔️ START RACE ⚔️", command=self.start_race,
                                 bg="#FF5555", fg="white", font=("Arial", 14, "bold"), width=20)
        self.btn_race.pack(side="left", padx=30)

        self.btn_clear = tk.Button(btn_frame, text="Clear Data", command=self.clear_data, font=("Arial", 11))
        self.btn_clear.pack(side="left", padx=10)

        tk.Label(ctrl_frame, text="⚠️ Race Mode runs both engines at once. High CPU/RAM usage expected.", 
                 fg="red", font=("Arial", 10)).pack(pady=5)

        log_frame = tk.LabelFrame(root, text="Live Log", font=("Arial", 12, "bold"))
        log_frame.pack(fill="x", padx=20, pady=5)
        self.output = ScrolledText(log_frame, height=12, font=("Consolas", 10), bg="#f0f0f0")
        self.output.pack(fill="both", expand=True, padx=5, pady=5)

        graph_frame = tk.LabelFrame(root, text="Live Results (Lower is Better)", font=("Arial", 12, "bold"))
        graph_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
        self.update_graph()
        self.check_queue()

    def log(self, msg):
        self.output.insert("end", f"{msg}\n")
        self.output.see("end")

    def clear_data(self):
        self.c_results = {}
        self.rust_results = {}
        self.update_graph()
        self.output.delete('1.0', tk.END)
        self.log("Arena cleared.")

    def set_buttons_state(self, state):
        self.btn_c.config(state=state)
        self.btn_rust.config(state=state)
        self.btn_race.config(state=state)
        self.btn_clear.config(state=state)

    def start_bench(self, lang):
        if self.is_running: return
        self.is_running = True
        self.set_buttons_state("disabled")
        threading.Thread(target=self.run_logic_single, args=(lang,), daemon=True).start()

    def start_race(self):
        if self.is_running: return
        self.is_running = True
        self.set_buttons_state("disabled")
        threading.Thread(target=self.run_logic_race, daemon=True).start()

    def cleanup_all(self):
        self.msg_queue.put("Cleaning up environment...")
        
        if self.c_process: 
            try: self.c_process.kill()
            except: pass
        if self.rust_process: 
            try: self.rust_process.kill()
            except: pass
        
        subprocess.run(["killall", "-q", "fuse_mount"], stderr=subprocess.DEVNULL)
        subprocess.run(["fusermount", "-u", "-z", C_MOUNT_DIR], stderr=subprocess.DEVNULL)
        subprocess.run(["fusermount", "-u", "-z", RUST_MOUNT_DIR], stderr=subprocess.DEVNULL)
        
        if os.path.exists(C_MOUNT_FILE): 
            try: os.remove(C_MOUNT_FILE)
            except: pass
        if os.path.exists(RUST_MOUNT_FILE):
            try: os.remove(RUST_MOUNT_FILE)
            except: pass

    def build_and_mount(self, lang):
        if lang == "C":
            src, mnt, exe = C_SRC_DIR, C_MOUNT_DIR, C_EXECUTABLE
            build = ["make"]
            clean = ["make", "clean"]
        else:
            src, mnt, exe = RUST_SRC_DIR, RUST_MOUNT_DIR, RUST_EXECUTABLE
            build = ["cargo", "build", "--release"]
            clean = ["cargo", "clean"] 

        self.msg_queue.put(f"[{lang}] Building...")
        if lang == "C": subprocess.run(clean, cwd=src, capture_output=True)
        
        res = subprocess.run(build, cwd=src, capture_output=True, text=True)
        if res.returncode != 0: raise Exception(f"{lang} Build Failed:\n{res.stderr}")

        self.msg_queue.put(f"[{lang}] Mounting...")
        os.makedirs(mnt, exist_ok=True)
        
        proc = subprocess.Popen([exe, "-f", "-s", mnt], cwd=src, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        for _ in range(10):
            time.sleep(0.5)
            if os.path.ismount(mnt): return proc
        
        proc.kill()
        raise Exception(f"{lang} Mount Timed Out")

    def run_logic_single(self, lang):
        try:
            self.cleanup_all()
            proc = self.build_and_mount(lang)
            if lang == "C": self.c_process = proc
            else: self.rust_process = proc
            
            mnt_file = C_MOUNT_FILE if lang == "C" else RUST_MOUNT_FILE
            
            self.msg_queue.put(f"--- Starting {lang} Benchmark ---")
            results = {}
            for count in OPERATION_COUNTS:
                t = self.perform_benchmark(mnt_file, count, lang)
                results[count] = t
                self.msg_queue.put(("RESULT", lang, results.copy()))
            
            self.msg_queue.put(f"--- {lang} Finished ---")

        except Exception as e:
            self.msg_queue.put(f"ERROR: {e}")
        finally:
            self.cleanup_all()
            self.msg_queue.put("FINISHED")

    def run_logic_race(self):
        try:
            self.cleanup_all()
            
            self.msg_queue.put("PREPARING ARENA: Building & Mounting both engines...")
            self.c_process = self.build_and_mount("C")
            self.rust_process = self.build_and_mount("Rust")
            
            self.msg_queue.put("ARENA READY! Starting simultaneous execution...")

            def worker(lang, mnt_file, result_dict):
                try:
                    for count in OPERATION_COUNTS:
                        t = self.perform_benchmark(mnt_file, count, lang)
                        result_dict[count] = t
                        self.msg_queue.put(("RESULT", lang, result_dict.copy()))
                except Exception as e:
                    self.msg_queue.put(f"{lang} CRASHED: {e}")

            t_c = threading.Thread(target=worker, args=("C", C_MOUNT_FILE, self.c_results))
            t_r = threading.Thread(target=worker, args=("Rust", RUST_MOUNT_FILE, self.rust_results))
            
            start_time = time.time()
            t_c.start()
            t_r.start()
            
            t_c.join()
            t_r.join()
            
            self.msg_queue.put("RACE COMPLETE!")
            self.msg_queue.put(("WINNER",))

        except Exception as e:
            self.msg_queue.put(f"RACE ERROR: {e}")
        finally:
            self.cleanup_all()
            self.msg_queue.put("FINISHED")

    def perform_benchmark(self, mnt_file, count, tag):
        self.msg_queue.put(f"[{tag}] Running {self.format_count(count)}...")
        
        fd = os.open(mnt_file, os.O_WRONLY)
        os.write(fd, f"INSERT_SEQ {count}".encode())
        os.close(fd)
        
        fd = os.open(mnt_file, os.O_RDONLY)
        resp = os.read(fd, 512).decode().strip()
        os.close(fd)
        if not resp.startswith("OK"): raise Exception("Insert failed")
        t_ins = float(resp.split()[1])

        fd = os.open(mnt_file, os.O_WRONLY)
        os.write(fd, f"LOOKUP_SEQ {count}".encode())
        os.close(fd)
        
        fd = os.open(mnt_file, os.O_RDONLY)
        resp = os.read(fd, 512).decode().strip()
        os.close(fd)
        if not resp.startswith("OK"): raise Exception("Lookup failed")
        t_look = float(resp.split()[1])
        
        total = t_ins + t_look
        self.msg_queue.put(f"  -> [{tag}] {self.format_count(count)} Done: {total:.4f}s")
        return total

    def format_count(self, n):
        if n >= 1_000_000_000: return f"{n//1_000_000_000}B"
        if n >= 1_000_000: return f"{n//1_000_000}M"
        if n >= 1_000: return f"{n//1_000}K"
        return str(n)

    def check_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                if isinstance(msg, tuple):
                    if msg[0] == "RESULT":
                        if msg[1] == "C": self.c_results = msg[2]
                        else: self.rust_results = msg[2]
                        self.update_graph()
                    elif msg[0] == "WINNER":
                        self.announce_winner()
                elif msg == "FINISHED":
                    self.is_running = False
                    self.set_buttons_state("normal")
                else:
                    self.log(msg)
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def announce_winner(self):
        c_total = sum(self.c_results.values()) if self.c_results else 0
        r_total = sum(self.rust_results.values()) if self.rust_results else 0
        
        if c_total == 0 or r_total == 0: return

        winner = "C" if c_total < r_total else "Rust"
        diff = abs(c_total - r_total)
        
        msg = f"🏆 WINNER: {winner}!\n\nC Total: {c_total:.4f}s\nRust Total: {r_total:.4f}s\nDifference: {diff:.4f}s"
        messagebox.showinfo("Race Results", msg)
        self.log(f"\n{msg}\n")

    def update_graph(self):
        self.ax.clear()
        
        x_indices = range(len(OPERATION_COUNTS))
        x_labels = [self.format_count(c) for c in OPERATION_COUNTS]
        
        has_data = False

        if self.c_results:
            y_vals = [self.c_results.get(c) for c in OPERATION_COUNTS]
            valid = [(i, y) for i, y in zip(x_indices, y_vals) if y is not None]
            if valid:
                xs, ys = zip(*valid)
                self.ax.plot(xs, ys, marker='o', linewidth=2, label="C", color="#4A90E2")
                has_data = True

        if self.rust_results:
            y_vals = [self.rust_results.get(c) for c in OPERATION_COUNTS]
            valid = [(i, y) for i, y in zip(x_indices, y_vals) if y is not None]
            if valid:
                xs, ys = zip(*valid)
                self.ax.plot(xs, ys, marker='s', linewidth=2, label="Rust", color="#E25A4A")
                has_data = True

        self.ax.set_xticks(x_indices)
        self.ax.set_xticklabels(x_labels)
        self.ax.set_xlabel("Operations (Insert + Lookup)", fontweight="bold")
        self.ax.set_ylabel("Total Time (s)", fontweight="bold")
        self.ax.grid(True, linestyle="--", alpha=0.7)
        if has_data: self.ax.legend()
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = McGui(root)
    root.mainloop()
