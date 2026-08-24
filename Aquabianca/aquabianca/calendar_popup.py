import calendar
from datetime import date
import tkinter as tk
from tkinter import ttk


def pick_date(parent, initial: date) -> date | None:
    """Show a small month-grid popup and return the picked date, or None if cancelled."""
    result: dict[str, date | None] = {"value": None}
    top = tk.Toplevel(parent)
    top.title("Pick a date")
    top.transient(parent)
    top.grab_set()
    top.resizable(False, False)

    state = {"year": initial.year, "month": initial.month}

    header = ttk.Frame(top, padding=(10, 10, 10, 4))
    header.pack(fill="x")
    label_var = tk.StringVar()
    ttk.Button(header, text="<", width=3, command=lambda: change_month(-1)).pack(side="left")
    ttk.Label(header, textvariable=label_var, anchor="center", width=18).pack(side="left", expand=True)
    ttk.Button(header, text=">", width=3, command=lambda: change_month(1)).pack(side="left")

    grid_frame = ttk.Frame(top, padding=(10, 0, 10, 10))
    grid_frame.pack()

    def change_month(delta: int) -> None:
        month = state["month"] + delta
        year = state["year"]
        if month < 1:
            month, year = 12, year - 1
        elif month > 12:
            month, year = 1, year + 1
        state["month"], state["year"] = month, year
        render()

    def choose(day: int) -> None:
        result["value"] = date(state["year"], state["month"], day)
        top.destroy()

    def render() -> None:
        for child in grid_frame.winfo_children():
            child.destroy()
        label_var.set(f"{calendar.month_name[state['month']]} {state['year']}")
        for col, name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            ttk.Label(grid_frame, text=name, width=4, anchor="center").grid(row=0, column=col, pady=(0, 4))
        for row, week in enumerate(calendar.monthcalendar(state["year"], state["month"]), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                is_today = date(state["year"], state["month"], day) == date.today()
                ttk.Button(
                    grid_frame,
                    text=str(day),
                    width=4,
                    style="Today.TButton" if is_today else "TButton",
                    command=lambda d=day: choose(d),
                ).grid(row=row, column=col, padx=1, pady=1)

    render()
    top.wait_window()
    return result["value"]
