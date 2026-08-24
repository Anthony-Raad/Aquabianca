from dataclasses import dataclass


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
