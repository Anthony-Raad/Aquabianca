# Aquabianca POS

Simple desktop POS for Aquabianca, built with Python and `tkinter`.

## Features

- Admin and cashier login
- Sales screen with cart
- Inventory and price management
- Opening and closing cash sessions
- Daily sales report
- Dual prices in USD and LBP

## Default login

- Admin: `admin` / `admin123`
- Cashier: `cashier` / `cashier123`

Change these passwords after first use.

## Run

```powershell
python main.py
```

## Notes

- Default database: local SQLite file `aquabianca_pos.db`
- Exchange rate default: `1 USD = 89000 LBP`
- SQLite mode needs no external packages
