from typing import Iterable

from .category_discovery import Category


class CategoryScraper:

    def __init__(self, client):
        self.client = client

    async def scrape_category(
        self,
        category: Category,
    ) -> list[dict]:
        ...