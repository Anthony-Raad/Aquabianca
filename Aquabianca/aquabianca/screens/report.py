import csv
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..calendar_popup import pick_date
from ..models import format_lbp, format_usd
from ..widgets import create_scrollable_container, make_sortable


class ReportMixin:
    def build_report_tab(self) -> None:
        container = create_scrollable_container(self.report_tab)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Report Date (YYYY-MM-DD)").pack(side="left")
        self.report_date_var = tk.StringVar(value=datetime.now().date().isoformat())
        ttk.Entry(header, textvariable=self.report_date_var, width=16).pack(side="left", padx=8)
        ttk.Button(header, text="<", width=3, command=lambda: self.shift_report_date(-1)).pack(side="left")
        ttk.Button(header, text=">", width=3, command=lambda: self.shift_report_date(1)).pack(side="left", padx=(2, 8))
        ttk.Button(header, text="Pick Date...", command=self.open_report_date_picker).pack(side="left")
        ttk.Button(header, text="Refresh Report", command=self.refresh_report).pack(side="left", padx=(8, 0))
        ttk.Button(header, text="Export CSV", command=self.export_report_csv).pack(side="left", padx=(8, 0))

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
        make_sortable(self.report_tree, [
            ("order_id", "number"), ("customer", "text"), ("time", "text"), ("cashier", "text"),
            ("items", "number"), ("lbp", "number"), ("usd", "number"),
        ])
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

    def shift_report_date(self, delta_days: int) -> None:
        try:
            current = datetime.strptime(self.report_date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            current = datetime.now().date()
        self.report_date_var.set((current + timedelta(days=delta_days)).isoformat())
        self.refresh_report()

    def open_report_date_picker(self) -> None:
        try:
            current = datetime.strptime(self.report_date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            current = datetime.now().date()
        picked = pick_date(self.root, current)
        if picked is not None:
            self.report_date_var.set(picked.isoformat())
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

        self._last_report_rows = order_rows

        if hasattr(self, "report_tree"):
            for row in self.report_tree.get_children():
                self.report_tree.delete(row)
            if not order_rows:
                self.report_tree.insert("", "end", values=("-", "-", "No orders for this date", "-", "-", "-", "-", ""))
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

    def export_report_csv(self) -> None:
        rows = getattr(self, "_last_report_rows", [])
        if not rows:
            messagebox.showinfo("Export CSV", "No orders to export for this date.")
            return

        default_name = f"aquabianca_report_{self.report_date_var.get()}.csv"
        path = filedialog.asksaveasfilename(
            title="Export daily report",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Order", "Customer", "Time", "Cashier", "Items", "Total LBP", "Total USD", "Products"])
            for order in rows:
                writer.writerow([
                    order["id"],
                    f"#{order['customer_no']}",
                    order["sold_at"].replace("T", " "),
                    order["username"] or "-",
                    order["items_count"],
                    order["total_lbp"],
                    order["total_usd"],
                    order["items_text"] or "",
                ])
        messagebox.showinfo("Exported", f"Report saved to {path}")

    def get_selected_report_order(self):
        if not hasattr(self, "report_tree"):
            return None
        selected = self.report_tree.selection()
        if not selected:
            return None
        try:
            return int(selected[0])
        except ValueError:
            return None

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
