# Aquabianca POS

Desktop POS for Aquabianca, built with Python and `tkinter`. No external
packages required — everything runs on the Python standard library.

## Features

- Admin and cashier login, with per-user active/deactivated status
- **User management** (admin): add cashiers/admins, reset passwords, deactivate accounts
- **Change your own password** from the top bar, any role
- Sales screen with cart, live **product search**, and **low-stock badges**
- Printable/saveable **receipt** shown after every checkout (copy to clipboard or save as `.txt`)
- Inventory and price management with sortable columns and a stock-value total
- Opening and closing cash sessions
- Daily sales report with a **date picker**, sortable columns, and **CSV export**
- Dual prices in USD and LBP, with a configurable **low-stock threshold**

## Default login

- Admin: `admin` / `admin123`
- Cashier: `cashier` / `cashier123`

Change these from inside the app: log in, use **Change Password** in the top
bar for your own account, or the **Users** tab (admin only) to reset any
user's password or add new accounts.

## Run

```powershell
python main.py
```

## Project layout

```
main.py                    Entry point
aquabianca/
  app.py                   Main application window
  database.py              SQLite access layer
  models.py                Cart item + currency formatting helpers
  widgets.py                Scrollable container + sortable-table helper
  receipt.py                Receipt text + dialog
  calendar_popup.py         Dependency-free date picker
  screens/                  One module per tab (login, sales, inventory,
                             report, settings, users)
```

## Notes

- Default database: local SQLite file `aquabianca_pos.db` (kept at the project root)
- Exchange rate default: `1 USD = 89000 LBP`
- Low stock threshold default: `5` units, editable in Settings
- No external packages needed — the date picker and sorting are implemented
  with the standard library only
