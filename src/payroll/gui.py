"""Interfaz gráfica simple: elegir Excel, período y carpeta de salida, y generar."""
import os
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .main import generate

BLUE = "#3873b3"
LIGHT = "#e8f0fa"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Generador de Liquidaciones")
        self.geometry("600x620")
        self.minsize(560, 560)
        self.configure(bg="white")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="white")
        style.configure("TLabel", background="white", font=("Segoe UI", 10))
        style.configure("TEntry", padding=4)
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure(
            "Accent.TButton", font=("Segoe UI", 11, "bold"), foreground="white",
            background=BLUE, padding=10,
        )
        style.map("Accent.TButton", background=[("active", "#2d5e93"), ("disabled", "#9db8d6")])

        header = tk.Frame(self, bg=BLUE)
        header.pack(fill="x")
        tk.Label(
            header, text="Generador de Liquidaciones", bg=BLUE, fg="white",
            font=("Segoe UI", 16, "bold"), pady=14,
        ).pack()

        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        today = date.today()
        self.excel = tk.StringVar()
        self.periodo = tk.StringVar(value=f"{today.year}-{today.month:02d}")
        self.salida = tk.StringVar(value=str(Path.home() / "Documents" / "Liquidaciones"))

        ttk.Label(body, text="Planilla Excel").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=self.excel).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(body, text="Elegir…", command=self.pick_excel).grid(row=0, column=2)

        ttk.Label(body, text="Período (AAAA-MM)").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=self.periodo, width=12).grid(row=1, column=1, sticky="w", padx=8)

        ttk.Label(body, text="Carpeta de salida").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=self.salida).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(body, text="Elegir…", command=self.pick_output).grid(row=2, column=2)

        self.run_btn = ttk.Button(
            body, text="Generar liquidaciones", style="Accent.TButton", command=self.run
        )
        self.run_btn.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(16, 8))

        tabs = ttk.Notebook(body)
        tabs.grid(row=4, column=0, columnspan=3, sticky="nsew")
        body.rowconfigure(4, weight=1)

        self.log = tk.Text(
            tabs, height=9, state="disabled", bg=LIGHT, relief="flat",
            font=("Segoe UI", 10), padx=8, pady=8,
        )
        tabs.add(self.log, text="Resultado")

        detail = ttk.Frame(tabs, padding=8)
        tabs.add(detail, text="Detalle por día")
        detail.columnconfigure(0, weight=1)
        detail.rowconfigure(1, weight=1)
        self.tabs = tabs
        self.payslips: dict[str, object] = {}
        self.worker = tk.StringVar()
        self.worker_box = ttk.Combobox(detail, textvariable=self.worker, state="readonly")
        self.worker_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.worker_box.bind("<<ComboboxSelected>>", lambda _e: self.show_detail())
        self.tree = ttk.Treeview(detail, columns=("fecha", "dia", "monto"), show="headings", height=8)
        for col, text, width, anchor in (
            ("fecha", "Fecha", 110, "w"), ("dia", "Día", 110, "w"), ("monto", "Monto", 110, "e"),
        ):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(detail, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        self.total_lbl = ttk.Label(detail, text="Genera las liquidaciones para ver el detalle.")
        self.total_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.open_btn = ttk.Button(body, text="Abrir carpeta de salida", command=self.open_output)
        self.open_btn.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def pick_excel(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar planilla", filetypes=[("Excel", "*.xlsx *.xls"), ("Todos", "*.*")]
        )
        if path:
            self.excel.set(path)

    def pick_output(self) -> None:
        path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if path:
            self.salida.set(path)

    def open_output(self) -> None:
        folder = Path(self.salida.get())
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def write(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def run(self) -> None:
        excel, periodo, salida = self.excel.get().strip(), self.periodo.get().strip(), self.salida.get().strip()
        if not excel or not Path(excel).is_file():
            messagebox.showwarning("Falta la planilla", "Elige un archivo Excel válido.")
            return
        if len(periodo) != 7 or periodo[4] != "-" or not (periodo[:4] + periodo[5:]).isdigit():
            messagebox.showwarning("Período inválido", "Usa el formato AAAA-MM, por ejemplo 2026-11.")
            return
        if not salida:
            messagebox.showwarning("Falta la carpeta", "Elige una carpeta de salida.")
            return

        self.run_btn.configure(state="disabled")
        self.write("Generando…")
        threading.Thread(target=self._work, args=(excel, periodo, salida), daemon=True).start()

    def _work(self, excel: str, periodo: str, salida: str) -> None:
        payslips = []
        try:
            result = generate(excel, periodo, salida)
            payslips = result.payslips
            lines = [f"✔ {result.count} liquidaciones generadas", f"✔ Resumen: {result.summary_path.name}"]
            lines += [f"✘ {e}" for e in result.errors]
        except PermissionError:
            lines = ["✘ No se pudo escribir: cierra los PDF o el resumen si los tienes abiertos."]
        except Exception as e:  # noqa: BLE001 - se muestra al usuario
            lines = [f"✘ Error: {e}"]
        self.after(0, self._done, lines, payslips)

    def _done(self, lines: list[str], payslips: list) -> None:
        for line in lines:
            self.write(line)
        self.run_btn.configure(state="normal")
        self.payslips = {p.nombre: p for p in payslips}
        names = list(self.payslips)
        self.worker_box.configure(values=names)
        if names:
            self.worker.set(names[0])
            self.show_detail()
            if any(p.dias for p in payslips):
                self.tabs.select(1)

    def show_detail(self) -> None:
        self.tree.delete(*self.tree.get_children())
        payslip = self.payslips.get(self.worker.get())
        if payslip is None:
            return
        if not payslip.dias:
            self.total_lbl.configure(text="Esta planilla no trae hoja 'Detalle diario'.")
            return
        for d in payslip.dias:
            self.tree.insert("", "end", values=(
                d["fecha"].strftime("%d-%m-%Y"), d["dia"], "$" + f"{d['monto']:,}".replace(",", "."),
            ))
        total = sum(d["monto"] for d in payslip.dias)
        self.total_lbl.configure(
            text=f"{len(payslip.dias)} días trabajados · Total: $" + f"{total:,}".replace(",", ".")
        )


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
