from datetime import datetime
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from .models import CartItem, format_lbp, format_usd

SHOP_NAME = "Aquabianca"
LINE_WIDTH = 42


def build_receipt_text(customer_no: int, cashier_name: str, items: list[CartItem]) -> str:
    total_lbp = sum(item.total_lbp for item in items)
    total_usd = sum(item.total_usd for item in items)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        SHOP_NAME.center(LINE_WIDTH),
        "Water Refilling Station".center(LINE_WIDTH),
        "-" * LINE_WIDTH,
        f"Date: {now}",
        f"Customer: #{customer_no}",
        f"Cashier: {cashier_name}",
        "-" * LINE_WIDTH,
    ]
    for item in items:
        lines.append(f"{item.name} x{item.qty}")
        lines.append(f"  {format_lbp(item.total_lbp):>18} | {format_usd(item.total_usd):>10}")
    lines.append("-" * LINE_WIDTH)
    lines.append(f"TOTAL: {format_lbp(total_lbp)} | {format_usd(total_usd)}")
    lines.append("-" * LINE_WIDTH)
    lines.append("Thank you for your business!".center(LINE_WIDTH))
    return "\n".join(lines)


def show_receipt_dialog(root, customer_no: int, cashier_name: str, items: list[CartItem], on_close=None) -> None:
    text = build_receipt_text(customer_no, cashier_name, items)

    top = tk.Toplevel(root)
    top.title(f"Receipt - Customer #{customer_no}")
    top.transient(root)
    top.grab_set()
    top.resizable(False, False)

    body = ttk.Frame(top, padding=14)
    body.pack(fill="both", expand=True)

    text_widget = tk.Text(body, width=LINE_WIDTH + 4, height=min(24, len(text.splitlines()) + 2), font=("Consolas", 10))
    text_widget.insert("1.0", text)
    text_widget.configure(state="disabled")
    text_widget.pack(fill="both", expand=True, pady=(0, 10))

    def copy_to_clipboard() -> None:
        root.clipboard_clear()
        root.clipboard_append(text)
        messagebox.showinfo("Copied", "Receipt copied to clipboard.", parent=top)

    def save_as_file() -> None:
        path = filedialog.asksaveasfilename(
            parent=top,
            title="Save receipt",
            defaultextension=".txt",
            initialfile=f"receipt_customer{customer_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text file", "*.txt")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        messagebox.showinfo("Saved", f"Receipt saved to {path}", parent=top)

    def close() -> None:
        top.destroy()
        if on_close:
            on_close()

    buttons = ttk.Frame(body)
    buttons.pack(fill="x")
    ttk.Button(buttons, text="Copy to Clipboard", command=copy_to_clipboard).pack(side="left")
    ttk.Button(buttons, text="Save as .txt", command=save_as_file).pack(side="left", padx=8)
    ttk.Button(buttons, text="Close", style="Primary.TButton", command=close).pack(side="right")

    top.protocol("WM_DELETE_WINDOW", close)
