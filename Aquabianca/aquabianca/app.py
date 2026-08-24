import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .database import DB_PATH, Database
from .models import CartItem
from .screens.login import LoginMixin
from .screens.sales import SalesMixin
from .screens.inventory import InventoryMixin
from .screens.report import ReportMixin
from .screens.settings import SettingsMixin
from .screens.users import UsersMixin


class AquabiancaPOS(LoginMixin, SalesMixin, InventoryMixin, ReportMixin, SettingsMixin, UsersMixin):
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
        self.style.configure("Today.TButton", font=("Segoe UI", 9, "bold"), foreground="#16324f")
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

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
        ttk.Button(top, text="Change Password", command=self.open_change_own_password_dialog).pack(side="right", padx=(0, 8))

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

            self.users_tab = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(self.users_tab, text="Users")
            self.build_users_tab()

            self.settings_tab = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(self.settings_tab, text="Settings")
            self.build_settings_tab()

    def logout(self) -> None:
        if self.cart:
            should_logout = messagebox.askyesno(
                "Cart not empty",
                "The current cart still has items that haven't been checked out.\n\n"
                "Log out anyway and discard this cart?",
            )
            if not should_logout:
                return
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


def main() -> None:
    root = tk.Tk()
    AquabiancaPOS(root)
    root.mainloop()
