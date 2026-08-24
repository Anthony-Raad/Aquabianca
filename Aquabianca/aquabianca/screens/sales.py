import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ..models import CartItem, format_lbp, format_usd
from ..receipt import show_receipt_dialog
from ..widgets import create_scrollable_container


class SalesMixin:
    def build_sales_tab(self) -> None:
        left = ttk.Frame(self.sales_tab)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = ttk.Frame(self.sales_tab, width=500)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        header_row = ttk.Frame(left)
        header_row.pack(fill="x", pady=(0, 10))
        ttk.Label(header_row, text="Products", style="Header.TLabel").pack(side="left")

        search_row = ttk.Frame(left)
        search_row.pack(fill="x", pady=(0, 10))
        ttk.Label(search_row, text="Search:").pack(side="left")
        self.product_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.product_search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_products())

        product_area = ttk.Frame(left)
        product_area.pack(fill="both", expand=True)
        self.product_grid = create_scrollable_container(product_area)

        ttk.Label(right, text="Cart", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        self.customer_cart_var = tk.StringVar()
        ttk.Label(right, textvariable=self.customer_cart_var, style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        tree_wrap = ttk.Frame(right)
        tree_wrap.pack(fill="both", expand=True)

        columns = ("product", "qty", "lbp", "usd")
        self.cart_tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", height=8)
        for col, title, width in [
            ("product", "Product", 180),
            ("qty", "Qty", 60),
            ("lbp", "Total LBP", 120),
            ("usd", "Total USD", 100),
        ]:
            self.cart_tree.heading(col, text=title)
            self.cart_tree.column(col, width=width, anchor="center")
        cart_scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_scrollbar.set)
        self.cart_tree.pack(side="left", fill="both", expand=True)
        cart_scrollbar.pack(side="left", fill="y", padx=(6, 0))
        self.cart_tree.bind("<Delete>", self.remove_cart_item)
        self.cart_tree.bind("<BackSpace>", self.remove_cart_item)
        self.cart_tree.bind("<<TreeviewSelect>>", self.load_cart_selection)

        cart_panel = ttk.Frame(right)
        cart_panel.pack(fill="x", pady=(8, 0))

        cart_buttons = ttk.Frame(cart_panel)
        cart_buttons.pack(fill="x", pady=8)
        ttk.Button(cart_buttons, text="Add Qty", command=self.increment_cart_item).pack(side="left")
        ttk.Button(cart_buttons, text="Reduce Qty", command=self.decrement_cart_item).pack(side="left", padx=8)
        ttk.Button(cart_buttons, text="Remove Selected", command=self.remove_cart_item).pack(side="left")

        qty_row = ttk.Frame(cart_panel)
        qty_row.pack(fill="x", pady=(0, 8))
        ttk.Label(qty_row, text="Qty").pack(side="left")
        self.cart_qty_var = tk.StringVar()
        qty_entry = ttk.Entry(qty_row, textvariable=self.cart_qty_var, width=8)
        qty_entry.pack(side="left")
        qty_entry.bind("<Return>", self.set_cart_quantity)
        ttk.Button(qty_row, text="Set", command=self.set_cart_quantity).pack(side="left", padx=(6, 10))
        ttk.Button(qty_row, text="Proceed to Checkout", style="Primary.TButton", command=self.complete_sale).pack(side="left")
        ttk.Button(qty_row, text="USD Helper", command=self.open_usd_helper_alert).pack(side="left", padx=(8, 0))

        self.cart_total_var = tk.StringVar(value="LBP: 0 | USD: 0")
        ttk.Label(cart_panel, textvariable=self.cart_total_var, style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

        self.refresh_customer_cart_label()
        self.refresh_products()
        self.refresh_cart()

    def refresh_customer_cart_label(self) -> None:
        if hasattr(self, "customer_cart_var"):
            total_lbp, total_usd, _item_count = self.get_cart_totals()
            self.customer_cart_var.set(
                f"Current cart: Customer #{self.current_customer_no} | "
                f"Total: {format_lbp(total_lbp)} | {format_usd(total_usd)}"
            )

    def begin_next_customer(self) -> None:
        self.current_customer_no += 1
        self.clear_cart()
        self.refresh_customer_cart_label()

    def refresh_products(self) -> None:
        for child in self.product_grid.winfo_children():
            child.destroy()
        products = self.db.get_active_products()
        search = self.product_search_var.get().strip().lower() if hasattr(self, "product_search_var") else ""
        if search:
            products = [p for p in products if search in p["name"].lower()]

        if not products:
            message = "No products match your search." if search else "No products yet — add some from the Inventory tab."
            ttk.Label(self.product_grid, text=message, style="Sub.TLabel").grid(row=0, column=0, padx=14, pady=14, sticky="w")
            return

        low_stock_threshold = self.db.get_low_stock_threshold()
        columns = 3
        for index, product in enumerate(products):
            out_of_stock = product["stock_qty"] <= 0
            low_stock = 0 < product["stock_qty"] <= low_stock_threshold
            border_color = "#c0392b" if out_of_stock else ("#d68910" if low_stock else "#cbd5df")

            card = tk.Frame(self.product_grid, bg="#ffffff", highlightbackground=border_color, highlightthickness=2 if (out_of_stock or low_stock) else 1)
            row = index // columns
            col = index % columns
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.product_grid.grid_columnconfigure(col, weight=1)

            tk.Label(card, text=product["name"], bg="#ffffff", fg="#16324f", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
            tk.Label(card, text=f"{format_lbp(product['price_lbp'])} | {format_usd(product['price_usd'])}", bg="#ffffff", fg="#35526b", font=("Segoe UI", 10)).pack(anchor="w", padx=14)

            if out_of_stock:
                stock_text, stock_color = "Out of stock", "#c0392b"
            elif low_stock:
                stock_text, stock_color = f"Low stock: {product['stock_qty']} left", "#d68910"
            else:
                stock_text, stock_color = f"Stock: {product['stock_qty']}", "#35526b"
            tk.Label(card, text=stock_text, bg="#ffffff", fg=stock_color, font=("Segoe UI", 10, "bold" if (out_of_stock or low_stock) else "normal")).pack(anchor="w", padx=14, pady=(0, 10))

            button = ttk.Button(card, text="Add to Cart", command=lambda p=product: self.add_to_cart(p))
            if out_of_stock:
                button.configure(state="disabled")
            button.pack(fill="x", padx=14, pady=(0, 14))

    def add_to_cart(self, product) -> None:
        if product["stock_qty"] <= 0:
            messagebox.showwarning("Out of stock", f"{product['name']} is out of stock.")
            return
        item = self.cart.get(product["id"])
        next_qty = 1 if item is None else item.qty + 1
        if next_qty > product["stock_qty"]:
            messagebox.showwarning("Stock limit", "Not enough stock for this quantity.")
            return
        if item:
            item.qty += 1
        else:
            self.cart[product["id"]] = CartItem(
                product_id=product["id"],
                name=product["name"],
                qty=1,
                price_lbp=product["price_lbp"],
                price_usd=product["price_usd"],
            )
        self.refresh_cart()

    def refresh_cart(self) -> None:
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        total_lbp = 0.0
        total_usd = 0.0
        for item in self.cart.values():
            self.cart_tree.insert(
                "",
                "end",
                iid=str(item.product_id),
                values=(item.name, item.qty, format_lbp(item.total_lbp), format_usd(item.total_usd)),
            )
            total_lbp += item.total_lbp
            total_usd += item.total_usd
        self.cart_total_var.set(f"LBP: {format_lbp(total_lbp)} | USD: {format_usd(total_usd)}")
        self.refresh_customer_cart_label()

    def open_usd_helper_alert(self) -> None:
        total_lbp, _total_usd, _item_count = self.get_cart_totals()
        if total_lbp <= 0:
            messagebox.showinfo("USD Helper", "Cart is empty. Add products first.")
            return

        usd_received = simpledialog.askfloat(
            "USD Helper",
            "Enter USD amount received:",
            minvalue=0.0,
            parent=self.root,
        )
        if usd_received is None:
            return

        rate = self.db.get_exchange_rate()
        paid_lbp = usd_received * rate
        balance_lbp = paid_lbp - total_lbp
        result_line = (
            f"Return in LBP: {format_lbp(balance_lbp)}"
            if balance_lbp >= 0
            else f"Remaining in LBP: {format_lbp(abs(balance_lbp))}"
        )

        messagebox.showinfo(
            "USD Helper Result",
            "\n".join([
                f"Order total: {format_lbp(total_lbp)}",
                f"Paid (USD): {format_usd(usd_received)}",
                f"Paid in LBP: {format_lbp(paid_lbp)}",
                result_line,
            ]),
        )

    def get_selected_cart_item(self):
        selected = self.cart_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def load_cart_selection(self, _event=None) -> None:
        product_id = self.get_selected_cart_item()
        if product_id is None:
            self.cart_qty_var.set("")
            return
        item = self.cart.get(product_id)
        self.cart_qty_var.set(str(item.qty) if item else "")

    def increment_cart_item(self) -> None:
        product_id = self.get_selected_cart_item()
        if product_id is None:
            return
        products = {row["id"]: row for row in self.db.get_active_products()}
        product = products.get(product_id)
        item = self.cart.get(product_id)
        if not product or not item:
            return
        if item.qty >= product["stock_qty"]:
            messagebox.showwarning("Stock limit", "Cannot add more than available stock.")
            return
        item.qty += 1
        self.refresh_cart()

    def decrement_cart_item(self) -> None:
        product_id = self.get_selected_cart_item()
        if product_id is None:
            return
        item = self.cart.get(product_id)
        if not item:
            return
        item.qty -= 1
        if item.qty <= 0:
            self.cart.pop(product_id, None)
        self.refresh_cart()
        self.load_cart_selection()

    def set_cart_quantity(self, _event=None) -> None:
        product_id = self.get_selected_cart_item()
        if product_id is None:
            messagebox.showinfo("Select item", "Choose an item in the cart first.")
            return

        item = self.cart.get(product_id)
        products = {row["id"]: row for row in self.db.get_active_products()}
        product = products.get(product_id)
        if not item or not product:
            return

        try:
            qty = int(self.cart_qty_var.get())
        except ValueError:
            messagebox.showerror("Invalid quantity", "Enter a whole number quantity.")
            return

        if qty <= 0:
            self.cart.pop(product_id, None)
            self.refresh_cart()
            self.cart_qty_var.set("")
            return
        if qty > product["stock_qty"]:
            messagebox.showwarning("Stock limit", "Cannot set more than available stock.")
            return

        item.qty = qty
        self.refresh_cart()
        self.load_cart_selection()

    def remove_cart_item(self, _event=None) -> None:
        product_id = self.get_selected_cart_item()
        if product_id is None:
            messagebox.showinfo("Select item", "Choose an item in the cart to remove.")
            return
        self.cart.pop(product_id, None)
        self.refresh_cart()
        self.cart_qty_var.set("")

    def clear_cart(self) -> None:
        self.cart.clear()
        self.refresh_cart()

    def get_cart_totals(self) -> tuple[float, float, int]:
        total_lbp = sum(item.total_lbp for item in self.cart.values())
        total_usd = sum(item.total_usd for item in self.cart.values())
        item_count = sum(item.qty for item in self.cart.values())
        return total_lbp, total_usd, item_count

    def save_current_order(self) -> bool:
        if not self.current_session:
            messagebox.showwarning("Cash session required", "Open cash before saving a customer order.")
            return False
        if not self.cart:
            messagebox.showwarning("Empty cart", "Add products before saving the order.")
            return False

        self.db.create_sale(
            self.current_session["id"],
            self.current_user["id"],
            self.current_customer_no,
            list(self.cart.values()),
        )
        self.clear_cart()
        self.refresh_products()
        self.refresh_inventory()
        self.refresh_report()
        return True

    def start_new_customer(self) -> None:
        if not self.cart:
            self.begin_next_customer()
            messagebox.showinfo("New customer", f"Cart is ready for Customer #{self.current_customer_no}.")
            return

        should_save = messagebox.askyesnocancel(
            "New Customer",
            "Do you want to save this customer order before starting a new cart?\n\nYes = save order\nNo = clear cart without saving\nCancel = keep current cart",
        )
        if should_save is None:
            return
        if should_save:
            saved = self.save_current_order()
            if not saved:
                return
            self.begin_next_customer()
        else:
            self.begin_next_customer()

        messagebox.showinfo("New customer", f"Cart renewed for Customer #{self.current_customer_no}.")

    def complete_sale(self) -> None:
        if not self.current_session:
            messagebox.showwarning("Cash session required", "Open cash before saving a customer order.")
            return
        if not self.cart:
            messagebox.showwarning("Empty cart", "Add products before saving the order.")
            return

        customer_no = self.current_customer_no
        cashier_name = self.current_user["full_name"]
        items = list(self.cart.values())

        if not self.save_current_order():
            return

        show_receipt_dialog(self.root, customer_no, cashier_name, items, on_close=self.begin_next_customer)

    def open_today_orders(self) -> None:
        from datetime import datetime

        today = datetime.now().date().isoformat()
        self.report_date_var.set(today)
        self.refresh_report()
        if hasattr(self, "notebook"):
            self.notebook.select(self.report_tab)
        if hasattr(self, "report_tree"):
            rows = self.report_tree.get_children()
            if rows:
                self.report_tree.selection_set(rows[0])
                self.report_tree.focus(rows[0])
                self.report_tree.see(rows[0])
