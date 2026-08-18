from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Distance(str, Enum):
    COSINE = "cosine"
    DOT = "dot"
    EUCLID = "euclid"


@dataclass
class Filter:
    must: list[dict[str, str]] = field(default_factory=list)


@dataclass
class VectorRecord:
    id: str | int
    vector: list[float]
    payload: dict | None = None


@dataclass
class SearchResult:
    id: str | int
    score: float
    payload: dict


@dataclass
class StoredRecord:
    id: str | int
    payload: dict


class VectorStore(ABC):
    @abstractmethod
    def ping(self, timeout: float = 5.0) -> bool:
        ...

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        ...

    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> None:
        ...

    @abstractmethod
    def ensure_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> bool:
        ...

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        ...

    @abstractmethod
    def upsert(self, collection_name: str, records: list[VectorRecord]) -> None:
        ...

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filter: Filter | None = None,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        ...

    @abstractmethod
    def retrieve(
        self,
        collection_name: str,
        ids: list[str | int],
    ) -> list[StoredRecord]:
        ...

    @abstractmethod
    def delete_points(
        self,
        collection_name: str,
        ids: list[str | int] | None = None,
        filter: Filter | None = None,
    ) -> None:
        ...

    @abstractmethod
    def count(
        self,
        collection_name: str,
        filter: Filter | None = None,
        exact: bool = True,
    ) -> int:
        ...

    @abstractmethod
    def list_collections(self) -> list[str]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...
