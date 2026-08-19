import asyncio

from src.infrastructure.ingestion.product_ingestion import ProductIngestion


async def main():
    await ProductIngestion.run()


if __name__ == "__main__":
    asyncio.run(main())