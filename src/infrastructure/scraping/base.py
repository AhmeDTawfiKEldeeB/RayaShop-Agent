from abc import ABC, abstractmethod

from .models import ScrapedProduct


class BaseScraper(ABC):

    @abstractmethod
    async def scrape_products(self) -> list[ScrapedProduct]:
        pass