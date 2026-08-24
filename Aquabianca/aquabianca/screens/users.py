import tkinter as tk
from tkinter import messagebox, ttk

from ..database import INTEGRITY_ERRORS
from ..widgets import create_scrollable_container


class UsersMixin:
    def build_users_tab(self) -> None:
        container = create_scrollable_container(self.users_tab)

        form = ttk.Frame(container)
        form.pack(fill="x", pady=(0, 12))

        self.user_username_var = tk.StringVar()
        self.user_full_name_var = tk.StringVar()
        self.user_role_var = tk.StringVar(value="cashier")
        self.user_password_var = tk.StringVar()

        ttk.Label(form, text="Username").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.user_username_var, width=20).grid(row=1, column=0, padx=(0, 8))
        ttk.Label(form, text="Full Name").grid(row=0, column=1, sticky="w")
        ttk.Entry(form, textvariable=self.user_full_name_var, width=22).grid(row=1, column=1, padx=(0, 8))
        ttk.Label(form, text="Role").grid(row=0, column=2, sticky="w")
        ttk.Combobox(form, textvariable=self.user_role_var, values=["admin", "cashier"], width=12, state="readonly").grid(row=1, column=2, padx=(0, 8))
        ttk.Label(form, text="Initial Password").grid(row=0, column=3, sticky="w")
        ttk.Entry(form, textvariable=self.user_password_var, width=18, show="*").grid(row=1, column=3, padx=(0, 8))
        ttk.Button(form, text="Add User", command=self.add_user_account).grid(row=1, column=4, padx=(0, 8))
        ttk.Button(form, text="Update Selected", command=self.update_user_account).grid(row=1, column=5, padx=(0, 8))

        columns = ("id", "username", "full_name", "role", "status")
        tree_wrap = ttk.Frame(container)
        tree_wrap.pack(fill="both", expand=True)
        self.users_tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", height=14)
        for col, title, width in [
            ("id", "ID", 50),
            ("username", "Username", 150),
            ("full_name", "Full Name", 200),
            ("role", "Role", 100),
            ("status", "Status", 100),
        ]:
            self.users_tree.heading(col, text=title)
            self.users_tree.column(col, width=width, anchor="center")
        self.users_tree.tag_configure("inactive", background="#f2f2f2", foreground="#888888")
        users_scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=users_scrollbar.set)
        self.users_tree.pack(side="left", fill="both", expand=True)
        users_scrollbar.pack(side="left", fill="y", padx=(6, 0))
        self.users_tree.bind("<<TreeviewSelect>>", self.load_user_selection)

        action_row = ttk.Frame(container)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="Reset Password", command=self.reset_selected_user_password).pack(side="left")
        ttk.Button(action_row, text="Deactivate", command=lambda: self.set_selected_user_active(False)).pack(side="left", padx=8)
        ttk.Button(action_row, text="Reactivate", command=lambda: self.set_selected_user_active(True)).pack(side="left")

        note = "Deactivated users can no longer log in, but their sales history is kept."
        ttk.Label(container, text=note, style="Sub.TLabel").pack(anchor="w", pady=(10, 0))

        self.refresh_users()

    def clear_user_form(self) -> None:
        self.user_username_var.set("")
        self.user_full_name_var.set("")
        self.user_role_var.set("cashier")
        self.user_password_var.set("")

    def add_user_account(self) -> None:
        username = self.user_username_var.get().strip()
        full_name = self.user_full_name_var.get().strip()
        role = self.user_role_var.get()
        password = self.user_password_var.get()

        if not username or not full_name or not password:
            messagebox.showerror("Missing data", "Username, full name, and initial password are required.")
            return
        if len(password) < 4:
            messagebox.showerror("Weak password", "Password must be at least 4 characters.")
            return

        try:
            self.db.add_user(username, full_name, role, password)
        except INTEGRITY_ERRORS:
            messagebox.showerror("Duplicate username", "A user with this username already exists.")
            return

        self.clear_user_form()
        self.refresh_users()
        messagebox.showinfo("User added", f"User '{username}' created successfully.")

    def load_user_selection(self, _event=None) -> None:
        selected = self.users_tree.selection()
        if not selected:
            return
        values = self.users_tree.item(selected[0], "values")
        self.user_username_var.set(values[1])
        self.user_full_name_var.set(values[2])
        self.user_role_var.set(values[3])
        self.user_password_var.set("")

    def get_selected_user_id(self):
        selected = self.users_tree.selection()
        if not selected:
            return None
        return int(self.users_tree.item(selected[0], "values")[0])

    def update_user_account(self) -> None:
        user_id = self.get_selected_user_id()
        if user_id is None:
            messagebox.showinfo("Select user", "Choose a user to update.")
            return
        full_name = self.user_full_name_var.get().strip()
        role = self.user_role_var.get()
        if not full_name:
            messagebox.showerror("Missing data", "Full name is required.")
            return
        if user_id == self.current_user["id"] and role != self.current_user["role"]:
            messagebox.showerror("Not allowed", "You cannot change your own role.")
            return
        self.db.update_user(user_id, full_name, role)
        self.clear_user_form()
        self.refresh_users()
        messagebox.showinfo("Saved", "User updated successfully.")

    def reset_selected_user_password(self) -> None:
        user_id = self.get_selected_user_id()
        if user_id is None:
            messagebox.showinfo("Select user", "Choose a user to reset the password for.")
            return
        new_password = self.ask_new_password(f"Reset password for user #{user_id}")
        if new_password is None:
            return
        self.db.change_password(user_id, new_password)
        messagebox.showinfo("Password reset", "Password updated successfully.")

    def set_selected_user_active(self, active: bool) -> None:
        user_id = self.get_selected_user_id()
        if user_id is None:
            messagebox.showinfo("Select user", "Choose a user first.")
            return
        if user_id == self.current_user["id"] and not active:
            messagebox.showerror("Not allowed", "You cannot deactivate your own account.")
            return
        self.db.set_user_active(user_id, active)
        self.refresh_users()

    def refresh_users(self) -> None:
        if not hasattr(self, "users_tree"):
            return
        for row in self.users_tree.get_children():
            self.users_tree.delete(row)
        for user in self.db.get_all_users():
            active = bool(user["active"])
            self.users_tree.insert(
                "",
                "end",
                values=(user["id"], user["username"], user["full_name"], user["role"], "Active" if active else "Deactivated"),
                tags=() if active else ("inactive",),
            )

    def ask_new_password(self, title: str):
        """Prompt for a new password with confirmation. Returns the password or None if cancelled."""
        result: dict[str, str | None] = {"value": None}
        top = tk.Toplevel(self.root)
        top.title(title)
        top.transient(self.root)
        top.grab_set()
        top.resizable(False, False)

        body = ttk.Frame(top, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="New password").grid(row=0, column=0, sticky="w")
        password_var = tk.StringVar()
        ttk.Entry(body, textvariable=password_var, show="*", width=26).grid(row=1, column=0, pady=(2, 10))

        ttk.Label(body, text="Confirm password").grid(row=2, column=0, sticky="w")
        confirm_var = tk.StringVar()
        confirm_entry = ttk.Entry(body, textvariable=confirm_var, show="*", width=26)
        confirm_entry.grid(row=3, column=0, pady=(2, 14))

        def submit(_event=None) -> None:
            password = password_var.get()
            confirm = confirm_var.get()
            if len(password) < 4:
                messagebox.showerror("Weak password", "Password must be at least 4 characters.", parent=top)
                return
            if password != confirm:
                messagebox.showerror("Mismatch", "Passwords do not match.", parent=top)
                return
            result["value"] = password
            top.destroy()

        confirm_entry.bind("<Return>", submit)
        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, sticky="e")
        ttk.Button(buttons, text="Cancel", command=top.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save", style="Primary.TButton", command=submit).pack(side="left")

        top.wait_window()
        return result["value"]

    def open_change_own_password_dialog(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("Change Password")
        top.transient(self.root)
        top.grab_set()
        top.resizable(False, False)

        body = ttk.Frame(top, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Current password").grid(row=0, column=0, sticky="w")
        current_var = tk.StringVar()
        ttk.Entry(body, textvariable=current_var, show="*", width=26).grid(row=1, column=0, pady=(2, 10))

        ttk.Label(body, text="New password").grid(row=2, column=0, sticky="w")
        new_var = tk.StringVar()
        ttk.Entry(body, textvariable=new_var, show="*", width=26).grid(row=3, column=0, pady=(2, 10))

        ttk.Label(body, text="Confirm new password").grid(row=4, column=0, sticky="w")
        confirm_var = tk.StringVar()
        confirm_entry = ttk.Entry(body, textvariable=confirm_var, show="*", width=26)
        confirm_entry.grid(row=5, column=0, pady=(2, 14))

        def submit(_event=None) -> None:
            if not self.db.verify_password(self.current_user["id"], current_var.get()):
                messagebox.showerror("Incorrect password", "Current password is incorrect.", parent=top)
                return
            new_password = new_var.get()
            if len(new_password) < 4:
                messagebox.showerror("Weak password", "New password must be at least 4 characters.", parent=top)
                return
            if new_password != confirm_var.get():
                messagebox.showerror("Mismatch", "New passwords do not match.", parent=top)
                return
            self.db.change_password(self.current_user["id"], new_password)
            messagebox.showinfo("Saved", "Password changed successfully.", parent=top)
            top.destroy()

        confirm_entry.bind("<Return>", submit)
        buttons = ttk.Frame(body)
        buttons.grid(row=6, column=0, sticky="e")
        ttk.Button(buttons, text="Cancel", command=top.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save", style="Primary.TButton", command=submit).pack(side="left")
