import tkinter as tk
from tkinter import messagebox, ttk

from ..widgets import create_scrollable_container


class SettingsMixin:
    def build_settings_tab(self) -> None:
        wrapper = create_scrollable_container(self.settings_tab)
        ttk.Label(wrapper, text="Exchange Rate", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(wrapper, text="Used to help you keep USD and LBP prices aligned.", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(wrapper)
        row.pack(anchor="w")
        self.exchange_rate_var = tk.StringVar(value=f"{self.db.get_exchange_rate():.0f}")
        ttk.Entry(row, textvariable=self.exchange_rate_var, width=18).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Save Rate", command=self.save_exchange_rate).pack(side="left")

        ttk.Label(wrapper, text="Low Stock Threshold", style="Header.TLabel").pack(anchor="w", pady=(24, 8))
        ttk.Label(
            wrapper,
            text="Products at or below this stock count are flagged as low stock on the Sales and Inventory tabs.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        threshold_row = ttk.Frame(wrapper)
        threshold_row.pack(anchor="w")
        self.low_stock_threshold_var = tk.StringVar(value=str(self.db.get_low_stock_threshold()))
        ttk.Entry(threshold_row, textvariable=self.low_stock_threshold_var, width=18).pack(side="left", padx=(0, 8))
        ttk.Button(threshold_row, text="Save Threshold", command=self.save_low_stock_threshold).pack(side="left")

    def save_exchange_rate(self) -> None:
        try:
            rate = float(self.exchange_rate_var.get())
            if rate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid rate", "Exchange rate must be a positive number.")
            return
        self.db.set_exchange_rate(rate)
        messagebox.showinfo("Saved", "Exchange rate updated successfully.")

    def save_low_stock_threshold(self) -> None:
        try:
            threshold = int(self.low_stock_threshold_var.get())
            if threshold < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid threshold", "Low stock threshold must be a non-negative whole number.")
            return
        self.db.set_low_stock_threshold(threshold)
        self.refresh_products()
        self.refresh_inventory()
        messagebox.showinfo("Saved", "Low stock threshold updated successfully.")
