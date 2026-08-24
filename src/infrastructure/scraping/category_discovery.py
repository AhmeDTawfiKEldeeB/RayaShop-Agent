from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    uid: str
    name: str
    product_count: int