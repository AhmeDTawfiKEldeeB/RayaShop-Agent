import logging

from fastapi import APIRouter, Query

from src.Agent.tools.retrieval_tool import search_products_raw
from src.api.schemas.product import (
    ProductResult,
    ProductSearchData,
    ProductSearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("/search", response_model=ProductSearchResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Natural language product search"),
    limit: int = Query(default=7, ge=1, le=20, description="Max results to return"),
) -> ProductSearchResponse:
    results = search_products_raw(q, limit=limit)
    products = [ProductResult(**item) for item in results]
    return ProductSearchResponse(
        status="success",
        message=f"Found {len(products)} product(s)",
        data=ProductSearchData(query=q, total=len(products), products=products),
    )
