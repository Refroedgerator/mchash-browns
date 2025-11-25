import tkinter
from tkinter.scrolledtext import ScrolledText

class McGui():
    def __init__(self, root):
        self.root = root
        self.root.title("McHash Browns - Benchmarking Tool")
        self.root.geometry("1920x1080")
        
        title = tkinter.Label(root, text="McHash Browns - C vs Rust", font=("Times New Roman", 20))
        title.pack(pady=10)

        btn_frame = tkinter.Frame(root)
        btn_frame.pack(pady=10)

        self.c_btn = tkinter.Button(btn_frame, text="Run C Performance Benchmark", command=self.run_c_benchmark)
        self.c_btn.grid(row=0, column=0, padx=10)

        self.rust_btn = tkinter.Button(btn_frame, text="Run Rust Performance Benchmark", command=self.run_rust_benchmark)
        self.rust_btn.grid(row=0, column=1, padx=10)

        self.output = ScrolledText(root, height=12, width=80, font=("Times New Roman", 12))
        self.output.pack(pady=10)

        graph_frame = tkinter.LabelFrame(root, text="Performance Graph")
        graph_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.graph_placeholder = tkinter.Label(graph_frame, text="Graph implementation TBD")
        self.graph_placeholder.pack(pady=40)

    def run_c_benchmark(self):
        self.output.insert("end", "[START] Running C Performance Benchmark...\n")
        self.output.insert("end", "[INSERT] Example Insert Operation...\n")
        with open("/dev/mc-frier", "w") as dev:
            dev.write("INSERT mykey 69\n")
            dev.flush()

        self.output.insert("end", "[READ] Example Read Operation...\n")
        with open("/dev/mc-frier", 'r') as dev:
            self.output.insert("end", dev.read(1024) + "\n")

        self.output.see("end")

    def run_rust_benchmark(self):
        self.output.insert("end", "[START] Running Rust Performance Benchmark...\n")
        self.output.see("end")

if __name__ == "__main__":
    root = tkinter.Tk()
    front_end = McGui(root)
    root.mainloop()
