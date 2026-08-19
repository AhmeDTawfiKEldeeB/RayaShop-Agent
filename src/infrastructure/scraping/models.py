from dataclasses import dataclass, field


@dataclass
class ScrapedProduct:
    id: int
    name: str
    sku: str
    url: str

    price: float
    old_price: float | None

    thumbnail: str | None
    images: list[str] = field(default_factory=list)

    stock_status: str | None = None