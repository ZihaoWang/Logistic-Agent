"""Repository layer for the logistics API.

Usage:
    Import BaseRepository for typing and concrete implementations from
    this package, for example InMemoryLogisticsRepository.
"""

from apps.logistics_api.repository.base import BaseRepository
from apps.logistics_api.repository.business import RouteSearch, ShippingPolicy
from apps.logistics_api.repository.firestore import FirestoreLogisticsRepository
from apps.logistics_api.repository.in_memory import InMemoryLogisticsRepository

__all__ = [
    "BaseRepository",
    "FirestoreLogisticsRepository",
    "InMemoryLogisticsRepository",
    "RouteSearch",
    "ShippingPolicy",
]
