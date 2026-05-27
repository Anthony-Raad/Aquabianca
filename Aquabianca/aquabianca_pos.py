from dataclasses import dataclass
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from database import DB_PATH, Database, INTEGRITY_ERRORS

def format_lbp(value: float) -> str:
    return f"{value:,.0f} LBP"


def format_usd(value: float) -> str:
    return f"${value:,.2f}"


@dataclass
class CartItem:
    product_id: int
    name: str
    qty: int
    price_lbp: float
    price_usd: float

    @property
    def total_lbp(self) -> float:
        return self.qty * self.price_lbp

    @property
    def total_usd(self) -> float:
        return self.qty * self.price_usd


class AquabiancaPOS:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Aquabianca POS")
        self.root.geometry("1180x720")
        self.root.minsize(1050, 650)
        self.db = Database(DB_PATH)
        self.current_user = None
        self.cart: dict[int, CartItem] = {}
        self.current_session = None
        self.current_customer_no = 1

        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")
        self.configure_styles()
        self.build_login_screen()

    def configure_styles(self) -> None:
        self.root.configure(bg="#eef3f8")
        self.style.configure("TFrame", background="#eef3f8")
        self.style.configure("Header.TLabel", background="#eef3f8", foreground="#16324f", font=("Segoe UI", 20, "bold"))
        self.style.configure("Sub.TLabel", background="#eef3f8", foreground="#35526b", font=("Segoe UI", 10))
        self.style.configure("Card.TFrame", background="#ffffff")
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def create_scrollable_container(self, parent):
        outer = ttk.Frame(parent)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg="#eef3f8", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas)

        content.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def resize_content(_event):
            canvas.itemconfigure(window_id, width=_event.width)

        canvas.bind("<Configure>", resize_content)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if getattr(event, "delta", 0):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")

        for widget in (canvas, content):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel)
            widget.bind("<Button-5>", _on_mousewheel)
        return content

    def build_login_screen(self) -> None:
        self.clear_root()
        frame = ttk.Frame(self.root, padding=40)
        frame.pack(fill="both", expand=True)

        card = ttk.Frame(frame, style="Card.TFrame", padding=30)
        card.place(relx=0.5, rely=0.5, anchor="center", width=420, height=320)

        ttk.Label(card, text="Aquabianca POS", style="Header.TLabel").pack(anchor="center", pady=(10, 6))
        ttk.Label(card, text="Local water shop point of sale", style="Sub.TLabel").pack(anchor="center", pady=(0, 24))

        ttk.Label(card, text="Username").pack(anchor="w")
        self.username_entry = ttk.Entry(card, font=("Segoe UI", 11))
        self.username_entry.pack(fill="x", pady=(6, 12))

        ttk.Label(card, text="Password").pack(anchor="w")
        self.password_entry = ttk.Entry(card, show="*", font=("Segoe UI", 11))
        self.password_entry.pack(fill="x", pady=(6, 18))

        ttk.Button(card, text="Login", style="Primary.TButton", command=self.login).pack(fill="x")

        helper = "Default admin: admin / admin123\nDefault cashier: cashier / cashier123"
        ttk.Label(card, text=helper, style="Sub.TLabel", justify="center").pack(anchor="center", pady=(18, 0))

        self.username_entry.focus_set()
        self.root.bind("<Return>", lambda _event: self.login())

    def login(self) -> None:
        username = self.username_entry.get()
        password = self.password_entry.get()
        user = self.db.authenticate_user(username, password)
        if not user:
            messagebox.showerror("Login failed", "Invalid username or password.")
            return
        self.current_user = user
        self.current_session = self.db.get_open_session(user["id"])
        self.build_main_screen()

    def build_main_screen(self) -> None:
        self.clear_root()
        wrapper = ttk.Frame(self.root, padding=18)
        wrapper.pack(fill="both", expand=True)

        top = ttk.Frame(wrapper)
        top.pack(fill="x", pady=(0, 12))

        ttk.Label(top, text="Aquabianca POS", style="Header.TLabel").pack(side="left")
        user_text = f"{self.current_user['full_name']} ({self.current_user['role'].title()})"
        ttk.Label(top, text=user_text, style="Sub.TLabel").pack(side="left", padx=(14, 0), pady=(8, 0))
        ttk.Button(top, text="Logout", command=self.logout).pack(side="right")

        self.session_status_var = tk.StringVar()
        self.refresh_session_status()
        ttk.Label(wrapper, textvariable=self.session_status_var, style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        controls = ttk.Frame(wrapper)
        controls.pack(fill="x", pady=(0, 10))
        ttk.Button(controls, text="Open Cash", command=self.prompt_open_session).pack(side="left")
        ttk.Button(controls, text="Close Cash", command=self.prompt_close_session).pack(side="left", padx=8)
        ttk.Button(controls, text="Edit Open Cash", command=self.prompt_edit_open_cash).pack(side="left")
        ttk.Button(controls, text="Edit Close Cash", command=self.prompt_edit_close_cash).pack(side="left", padx=8)

        self.notebook = ttk.Notebook(wrapper)
        self.notebook.pack(fill="both", expand=True)

        self.sales_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.sales_tab, text="Sales")
        self.build_sales_tab()

        self.report_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.report_tab, text="Daily Report")
        self.build_report_tab()

        if self.current_user["role"] == "admin":
            self.inventory_tab = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(self.inventory_tab, text="Inventory")
            self.build_inventory_tab()

            self.settings_tab = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(self.settings_tab, text="Settings")
            self.build_settings_tab()

    def logout(self) -> None:
        self.current_user = None
        self.current_session = None
        self.current_customer_no = 1
        self.cart.clear()
        self.build_login_screen()

    def refresh_session_status(self) -> None:
        if self.current_session:
            opened_at = self.current_session["opened_at"].replace("T", " ")
            text = f"Cash session open since {opened_at}"
        else:
            text = "No open cash session. Open cash before making sales."
        self.session_status_var.set(text)

    def prompt_open_session(self) -> None:
        if self.current_session:
            messagebox.showinfo("Cash session", "A cash session is already open.")
            return
        opening_lbp = simpledialog.askfloat("Open Cash", "Opening cash in LBP:", minvalue=0.0, parent=self.root)
        if opening_lbp is None:
            return
        opening_usd = simpledialog.askfloat("Open Cash", "Opening cash in USD:", minvalue=0.0, parent=self.root)
        if opening_usd is None:
            return
        self.db.open_session(self.current_user["id"], opening_lbp, opening_usd)
        self.current_session = self.db.get_open_session(self.current_user["id"])
        self.refresh_session_status()
        self.refresh_report()

    def prompt_close_session(self) -> None:
        if not self.current_session:
            messagebox.showinfo("Cash session", "No open cash session found.")
            return
        closing_lbp = simpledialog.askfloat("Close Cash", "Closing cash in LBP:", minvalue=0.0, parent=self.root)
        if closing_lbp is None:
            return
        closing_usd = simpledialog.askfloat("Close Cash", "Closing cash in USD:", minvalue=0.0, parent=self.root)
        if closing_usd is None:
            return
        self.db.close_session(self.current_session["id"], closing_lbp, closing_usd)
        self.current_session = None
        self.refresh_session_status()
        self.refresh_report()

    def prompt_edit_open_cash(self) -> None:
        session = self.current_session or self.db.get_latest_session(self.current_user["id"])
        if not session:
            messagebox.showinfo("Edit open cash", "No cash session found to edit.")
            return

        opening_lbp = simpledialog.askfloat(
            "Edit Open Cash",
            "Correct opening cash in LBP:",
            minvalue=0.0,
            parent=self.root,
            initialvalue=float(session["opening_cash_lbp"] or 0.0),
        )
        if opening_lbp is None:
            return

        opening_usd = simpledialog.askfloat(
            "Edit Open Cash",
            "Correct opening cash in USD:",
            minvalue=0.0,
            parent=self.root,
            initialvalue=float(session["opening_cash_usd"] or 0.0),
        )
        if opening_usd is None:
            return

        self.db.update_session_opening(session["id"], opening_lbp, opening_usd)
        self.current_session = self.db.get_open_session(self.current_user["id"])
        self.refresh_session_status()
        self.refresh_report()
        messagebox.showinfo("Saved", "Opening cash updated successfully.")

    def prompt_edit_close_cash(self) -> None:
        if self.current_session:
            messagebox.showinfo("Edit close cash", "This session is still open. Use Close Cash first.")
            return

        session = self.db.get_latest_session(self.current_user["id"])
        if not session:
            messagebox.showinfo("Edit close cash", "No cash session found to edit.")
            return
        if session["status"] != "closed":
            messagebox.showinfo("Edit close cash", "No closed session found to edit yet.")
            return

        closing_lbp = simpledialog.askfloat(
            "Edit Close Cash",
            "Correct closing cash in LBP:",
            minvalue=0.0,
            parent=self.root,
            initialvalue=float(session["closing_cash_lbp"] or 0.0),
        )
        if closing_lbp is None:
            return

        closing_usd = simpledialog.askfloat(
            "Edit Close Cash",
            "Correct closing cash in USD:",
            minvalue=0.0,
            parent=self.root,
            initialvalue=float(session["closing_cash_usd"] or 0.0),
        )
        if closing_usd is None:
            return

        self.db.update_session_closing(session["id"], closing_lbp, closing_usd)
        self.refresh_report()
        messagebox.showinfo("Saved", "Closing cash updated successfully.")

    def build_sales_tab(self) -> None:
        left = ttk.Frame(self.sales_tab)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = ttk.Frame(self.sales_tab, width=500)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ttk.Label(left, text="Products", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        product_area = ttk.Frame(left)
        product_area.pack(fill="both", expand=True)
        self.product_grid = self.create_scrollable_container(product_area)

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
        columns = 3
        for index, product in enumerate(products):
            card = tk.Frame(self.product_grid, bg="#ffffff", highlightbackground="#cbd5df", highlightthickness=1)
            row = index // columns
            col = index % columns
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.product_grid.grid_columnconfigure(col, weight=1)

            tk.Label(card, text=product["name"], bg="#ffffff", fg="#16324f", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
            tk.Label(card, text=f"{format_lbp(product['price_lbp'])} | {format_usd(product['price_usd'])}", bg="#ffffff", fg="#35526b", font=("Segoe UI", 10)).pack(anchor="w", padx=14)
            tk.Label(card, text=f"Stock: {product['stock_qty']}", bg="#ffffff", fg="#35526b", font=("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(0, 10))
            ttk.Button(card, text="Add to Cart", command=lambda p=product: self.add_to_cart(p)).pack(fill="x", padx=14, pady=(0, 14))

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
        if not self.save_current_order():
            return
        self.begin_next_customer()

    def open_today_orders(self) -> None:
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

    def build_inventory_tab(self) -> None:
        container = self.create_scrollable_container(self.inventory_tab)

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
        inventory_scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscrollcommand=inventory_scrollbar.set)
        self.inventory_tree.pack(side="left", fill="both", expand=True)
        inventory_scrollbar.pack(side="left", fill="y", padx=(6, 0))
        self.inventory_tree.bind("<<TreeviewSelect>>", self.load_inventory_selection)

        action_row = ttk.Frame(container)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="Refresh", command=self.refresh_inventory).pack(side="left", padx=8)

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
        for product in self.db.get_all_products():
            self.inventory_tree.insert(
                "",
                "end",
                values=(
                    product["id"],
                    product["name"],
                    format_lbp(product["price_lbp"]),
                    format_usd(product["price_usd"]),
                    product["stock_qty"],
                ),
            )

    def build_report_tab(self) -> None:
        container = self.create_scrollable_container(self.report_tab)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Report Date (YYYY-MM-DD)").pack(side="left")
        self.report_date_var = tk.StringVar(value=datetime.now().date().isoformat())
        ttk.Entry(header, textvariable=self.report_date_var, width=16).pack(side="left", padx=8)
        ttk.Button(header, text="Refresh Report", command=self.refresh_report).pack(side="left")

        cards = ttk.Frame(container)
        cards.pack(fill="x", pady=(8, 14))

        self.report_vars = {
            "opening": tk.StringVar(value="-"),
            "closing": tk.StringVar(value="-"),
            "items": tk.StringVar(value="0"),
            "sales": tk.StringVar(value="0"),
            "totals": tk.StringVar(value="-"),
        }

        for idx, (title, key) in enumerate([
            ("Opening Cash", "opening"),
            ("Closing Cash", "closing"),
            ("Items Sold", "items"),
            ("Sales Count", "sales"),
            ("Total Sales", "totals"),
        ]):
            card = tk.Frame(cards, bg="#ffffff", highlightbackground="#cbd5df", highlightthickness=1)
            card.grid(row=0, column=idx, padx=6, sticky="nsew")
            cards.grid_columnconfigure(idx, weight=1)
            tk.Label(card, text=title, bg="#ffffff", fg="#35526b", font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(12, 6))
            tk.Label(card, textvariable=self.report_vars[key], bg="#ffffff", fg="#16324f", font=("Segoe UI", 12, "bold"), justify="left").pack(anchor="w", padx=12, pady=(0, 14))

        ttk.Label(container, text="Orders", style="Header.TLabel").pack(anchor="w", pady=(10, 8))
        report_table_wrap = ttk.Frame(container)
        report_table_wrap.pack(fill="both", expand=True, pady=(0, 10))

        report_columns = ("order_id", "customer", "time", "cashier", "items", "lbp", "usd", "details")
        self.report_tree = ttk.Treeview(report_table_wrap, columns=report_columns, show="headings", height=12)
        for col, title, width in [
            ("order_id", "Order", 70),
            ("customer", "Customer", 85),
            ("time", "Time", 150),
            ("cashier", "Cashier", 100),
            ("items", "Items", 70),
            ("lbp", "Total LBP", 120),
            ("usd", "Total USD", 100),
            ("details", "Products", 420),
        ]:
            self.report_tree.heading(col, text=title)
            self.report_tree.column(col, width=width, anchor="center")
        self.report_tree.column("details", anchor="w")
        report_scrollbar = ttk.Scrollbar(report_table_wrap, orient="vertical", command=self.report_tree.yview)
        self.report_tree.configure(yscrollcommand=report_scrollbar.set)
        self.report_tree.pack(side="left", fill="both", expand=True)
        report_scrollbar.pack(side="left", fill="y", padx=(6, 0))
        self.report_tree.bind("<Delete>", self.delete_selected_order)

        report_actions = ttk.Frame(container)
        report_actions.pack(fill="x", pady=(0, 8))
        ttk.Button(report_actions, text="Remove Selected Order", command=self.delete_selected_order).pack(side="left")

        self.report_orders_total_var = tk.StringVar(value="Orders Total: 0 LBP | $0.00")
        ttk.Label(container, textvariable=self.report_orders_total_var, style="Sub.TLabel").pack(anchor="e", pady=(0, 8))

        note = "This report shows opening cash, closing cash, items sold, and total sales for the selected day."
        ttk.Label(container, text=note, style="Sub.TLabel").pack(anchor="w")
        self.refresh_report()

    def refresh_report(self) -> None:
        if not hasattr(self, "report_vars"):
            return
        try:
            datetime.strptime(self.report_date_var.get(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Use the format YYYY-MM-DD.")
            return
        sales_summary, cash_summary, order_rows = self.db.get_daily_report(self.report_date_var.get())
        self.report_vars["opening"].set(
            f"{format_lbp(cash_summary['opening_lbp'])}\n{format_usd(cash_summary['opening_usd'])}"
        )
        self.report_vars["closing"].set(
            f"{format_lbp(cash_summary['closing_lbp'])}\n{format_usd(cash_summary['closing_usd'])}"
        )
        self.report_vars["items"].set(str(sales_summary["items_sold"]))
        self.report_vars["sales"].set(str(sales_summary["sale_count"]))
        self.report_vars["totals"].set(
            f"{format_lbp(sales_summary['total_lbp'])}\n{format_usd(sales_summary['total_usd'])}"
        )
        if hasattr(self, "report_orders_total_var"):
            self.report_orders_total_var.set(
                f"Orders Total: {format_lbp(sales_summary['total_lbp'])} | {format_usd(sales_summary['total_usd'])}"
            )

        if hasattr(self, "report_tree"):
            for row in self.report_tree.get_children():
                self.report_tree.delete(row)
            for order in order_rows:
                sold_at = order["sold_at"].replace("T", " ")
                self.report_tree.insert(
                    "",
                    "end",
                    iid=str(order["id"]),
                    values=(
                        order["id"],
                        f"#{order['customer_no']}",
                        sold_at,
                        order["username"] or "-",
                        order["items_count"],
                        format_lbp(order["total_lbp"]),
                        format_usd(order["total_usd"]),
                        order["items_text"] or "",
                    ),
                )

    def get_selected_report_order(self):
        if not hasattr(self, "report_tree"):
            return None
        selected = self.report_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def delete_selected_order(self, _event=None) -> None:
        sale_id = self.get_selected_report_order()
        if sale_id is None:
            messagebox.showinfo("Select order", "Choose an order in Daily Report to remove.")
            return

        order_values = self.report_tree.item(str(sale_id), "values")
        customer_label = order_values[1] if order_values else "-"
        total_lbp = order_values[5] if order_values else "-"
        total_usd = order_values[6] if order_values else "-"
        should_delete = messagebox.askyesno(
            "Remove order",
            f"Remove order #{sale_id} for customer {customer_label}?\n\n"
            f"This will restore stock for that order.\n\n"
            f"Total: {total_lbp} | {total_usd}",
        )
        if not should_delete:
            return

        self.db.delete_sale(sale_id)
        self.refresh_products()
        self.refresh_inventory()
        self.refresh_report()
        messagebox.showinfo("Order removed", f"Order #{sale_id} was removed successfully.")

    def build_settings_tab(self) -> None:
        wrapper = self.create_scrollable_container(self.settings_tab)
        ttk.Label(wrapper, text="Exchange Rate", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(wrapper, text="Used to help you keep USD and LBP prices aligned.", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(wrapper)
        row.pack(anchor="w")
        self.exchange_rate_var = tk.StringVar(value=f"{self.db.get_exchange_rate():.0f}")
        ttk.Entry(row, textvariable=self.exchange_rate_var, width=18).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Save Rate", command=self.save_exchange_rate).pack(side="left")

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


def main() -> None:
    root = tk.Tk()
    AquabiancaPOS(root)
    root.mainloop()

