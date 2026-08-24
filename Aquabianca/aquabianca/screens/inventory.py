import tkinter as tk
from tkinter import messagebox, ttk

from ..models import format_lbp, format_usd
from ..widgets import create_scrollable_container, make_sortable
from ..database import INTEGRITY_ERRORS


class InventoryMixin:
    def build_inventory_tab(self) -> None:
        container = create_scrollable_container(self.inventory_tab)

        form = ttk.Frame(container)
        form.pack(fill="x", pady=(0, 12))

        self.inventory_name_var = tk.StringVar()
        self.inventory_lbp_var = tk.StringVar()
        self.inventory_usd_var = tk.StringVar()
        self.inventory_stock_var = tk.StringVar()

        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.inventory_name_var, width=26).grid(row=1, column=0, padx=(0, 8))
        ttk.Label(form, text="Price LBP").grid(row=0, column=1, sticky="w")
        ttk.Entry(form, textvariable=self.inventory_lbp_var, width=16).grid(row=1, column=1, padx=(0, 8))
        ttk.Label(form, text="Price USD").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.inventory_usd_var, width=16).grid(row=1, column=2, padx=(0, 8))
        ttk.Label(form, text="Stock Qty").grid(row=0, column=3, sticky="w")
        ttk.Entry(form, textvariable=self.inventory_stock_var, width=12).grid(row=1, column=3, padx=(0, 8))
        ttk.Button(form, text="Auto USD from LBP", command=self.calculate_usd_from_lbp).grid(row=1, column=4, padx=(0, 8))
        ttk.Button(form, text="Add Product", command=self.add_inventory_product).grid(row=1, column=5, padx=(0, 8))
        ttk.Button(form, text="Update Selected", command=self.update_inventory_product).grid(row=1, column=6, padx=(0, 8))
        ttk.Button(form, text="Remove Product", command=self.delete_inventory_product).grid(row=1, column=7)

        columns = ("id", "name", "lbp", "usd", "stock")
        tree_wrap = ttk.Frame(container)
        tree_wrap.pack(fill="both", expand=True)
        self.inventory_tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", height=18)
        for col, title, width in [
            ("id", "ID", 50),
            ("name", "Product", 220),
            ("lbp", "Price LBP", 150),
            ("usd", "Price USD", 120),
            ("stock", "Stock", 100),
        ]:
            self.inventory_tree.heading(col, text=title)
            self.inventory_tree.column(col, width=width, anchor="center")
        self.inventory_tree.tag_configure("out_of_stock", background="#fadbd8")
        self.inventory_tree.tag_configure("low_stock", background="#fdebd0")
        make_sortable(self.inventory_tree, [
            ("id", "number"), ("name", "text"), ("lbp", "number"), ("usd", "number"), ("stock", "number"),
        ])
        inventory_scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscrollcommand=inventory_scrollbar.set)
        self.inventory_tree.pack(side="left", fill="both", expand=True)
        inventory_scrollbar.pack(side="left", fill="y", padx=(6, 0))
        self.inventory_tree.bind("<<TreeviewSelect>>", self.load_inventory_selection)

        action_row = ttk.Frame(container)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="Refresh", command=self.refresh_inventory).pack(side="left", padx=8)

        self.inventory_totals_var = tk.StringVar()
        ttk.Label(container, textvariable=self.inventory_totals_var, style="Sub.TLabel").pack(anchor="w", pady=(10, 0))

        self.refresh_inventory()

    def calculate_usd_from_lbp(self) -> None:
        try:
            lbp_value = float(self.inventory_lbp_var.get())
            usd_value = lbp_value / self.db.get_exchange_rate()
            self.inventory_usd_var.set(f"{usd_value:.2f}")
        except ValueError:
            messagebox.showerror("Invalid value", "Enter a valid LBP price first.")

    def add_inventory_product(self) -> None:
        try:
            self.db.add_product(
                self.inventory_name_var.get(),
                float(self.inventory_lbp_var.get()),
                float(self.inventory_usd_var.get()),
                int(self.inventory_stock_var.get()),
            )
        except ValueError:
            messagebox.showerror("Invalid data", "Check the price and stock values.")
            return
        except INTEGRITY_ERRORS:
            messagebox.showerror("Duplicate name", "A product with this name already exists.")
            return
        self.clear_inventory_form()
        self.refresh_inventory()
        self.refresh_products()

    def load_inventory_selection(self, _event=None) -> None:
        selected = self.inventory_tree.selection()
        if not selected:
            return
        values = self.inventory_tree.item(selected[0], "values")
        self.inventory_name_var.set(values[1])
        self.inventory_lbp_var.set(str(values[2]).replace(",", "").replace(" LBP", ""))
        self.inventory_usd_var.set(str(values[3]).replace("$", ""))
        self.inventory_stock_var.set(values[4])

    def update_inventory_product(self) -> None:
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showinfo("Select product", "Choose a product to update.")
            return
        product_id = int(self.inventory_tree.item(selected[0], "values")[0])
        try:
            self.db.update_product(
                product_id,
                self.inventory_name_var.get(),
                float(self.inventory_lbp_var.get()),
                float(self.inventory_usd_var.get()),
                int(self.inventory_stock_var.get()),
            )
        except ValueError:
            messagebox.showerror("Invalid data", "Check the price and stock values.")
            return
        self.clear_inventory_form()
        self.refresh_inventory()
        self.refresh_products()

    def delete_inventory_product(self) -> None:
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showinfo("Select product", "Choose a product to delete.")
            return

        values = self.inventory_tree.item(selected[0], "values")
        product_id = int(values[0])
        product_name = values[1]
        should_delete = messagebox.askyesno(
            "Delete product",
            f"Delete '{product_name}' from the database?\n\nThis cannot be undone.",
        )
        if not should_delete:
            return

        self.db.delete_product(product_id)
        self.cart.pop(product_id, None)
        self.refresh_cart()
        self.clear_inventory_form()
        self.refresh_inventory()
        self.refresh_products()

    def clear_inventory_form(self) -> None:
        self.inventory_name_var.set("")
        self.inventory_lbp_var.set("")
        self.inventory_usd_var.set("")
        self.inventory_stock_var.set("")

    def refresh_inventory(self) -> None:
        if not hasattr(self, "inventory_tree"):
            return
        for row in self.inventory_tree.get_children():
            self.inventory_tree.delete(row)

        threshold = self.db.get_low_stock_threshold()
        total_units = 0
        total_value_lbp = 0.0
        total_value_usd = 0.0
        for product in self.db.get_all_products():
            stock = product["stock_qty"]
            tag = "out_of_stock" if stock <= 0 else ("low_stock" if stock <= threshold else "")
            self.inventory_tree.insert(
                "",
                "end",
                values=(
                    product["id"],
                    product["name"],
                    format_lbp(product["price_lbp"]),
                    format_usd(product["price_usd"]),
                    stock,
                ),
                tags=(tag,) if tag else (),
            )
            total_units += stock
            total_value_lbp += stock * product["price_lbp"]
            total_value_usd += stock * product["price_usd"]

        self.inventory_totals_var.set(
            f"Total units in stock: {total_units} | Stock value: {format_lbp(total_value_lbp)} | {format_usd(total_value_usd)}"
        )
