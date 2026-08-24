from tkinter import messagebox, ttk


class LoginMixin:
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
            messagebox.showerror("Login failed", "Invalid username or password, or this account is deactivated.")
            return
        self.current_user = user
        self.current_session = self.db.get_open_session(user["id"])
        self.build_main_screen()
