from pydantic import BaseModel, Field

from src.api.schemas.base import StandardResponse


class ProductResult(BaseModel):
    id: int | str | None = Field(None, description="Product ID from catalog")
    name: str = Field("", description="Product name")
    sku: str = Field("", description="Product SKU")
    price: float = Field(0, description="Current price in EGP")
    old_price: float | None = Field(None, description="Price before discount")
    stock_status: str = Field("", description="e.g. IN_STOCK")
    url: str = Field("", description="Product page URL")
    thumbnail: str | None = Field(None, description="Product image URL")
    score: float = Field(0, description="Hybrid search relevance score")


class ProductSearchData(BaseModel):
    query: str
    total: int
    products: list[ProductResult]


class ProductSearchResponse(StandardResponse[ProductSearchData]):
    data: ProductSearchData
