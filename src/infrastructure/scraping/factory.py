from .base import BaseScraper
from .providers.raya import RayaScraper


class ScraperFactory:

    @staticmethod
    def create(source: str) -> BaseScraper:
        scrapers = {
            "raya": RayaScraper,
        }

        try:
            return scrapers[source.lower()]()
        except KeyError:
            raise ValueError(
                f"Unsupported scraper source: {source}"
            )