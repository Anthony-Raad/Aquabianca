import tkinter as tk
from tkinter import ttk


def create_scrollable_container(parent):
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


def make_sortable(tree: ttk.Treeview, columns: list[tuple[str, str]]) -> None:
    """Bind click-to-sort behaviour to a Treeview's headings.

    columns: list of (column_id, kind) where kind is "text" or "number".
    Numbers are parsed by stripping any non-digit/decimal/minus characters,
    so formatted values like "12,345 LBP" or "$3.50" sort correctly.
    """
    sort_state = {"column": None, "reverse": False}

    def _sort_key(value: str, kind: str):
        if kind != "number":
            return value.lower()
        cleaned = "".join(ch for ch in value if ch.isdigit() or ch in ".-")
        try:
            return float(cleaned) if cleaned not in ("", "-", ".") else 0.0
        except ValueError:
            return 0.0

    def sort_by(col: str, kind: str) -> None:
        reverse = sort_state["column"] == col and not sort_state["reverse"]
        rows = [(tree.set(item, col), item) for item in tree.get_children("")]
        rows.sort(key=lambda pair: _sort_key(pair[0], kind), reverse=reverse)
        for index, (_value, item) in enumerate(rows):
            tree.move(item, "", index)
        sort_state["column"] = col
        sort_state["reverse"] = reverse
        for other_col, _kind in columns:
            heading_text = tree.heading(other_col)["text"].rstrip(" ▲▼")
            if other_col == col:
                heading_text += " ▼" if reverse else " ▲"
            tree.heading(other_col, text=heading_text)

    for col, kind in columns:
        tree.heading(col, command=lambda c=col, k=kind: sort_by(c, k))
