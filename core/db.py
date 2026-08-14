"""Singleton in-memory store, keyed by entity name then record key.

Pattern carried over from an earlier practice project: `InMemoryDB.__new__`
enforces a single instance even if someone calls the class directly, and
`db` is the shared instance modules should import. Each entity gets its
own {key -> record} dict plus an insertion-order index list.
"""

import time
from typing import Any, Dict, List

__all__ = ["db", "InMemoryDB"]


class InMemoryDB:
    _instance = None

    def __new__(cls) -> "InMemoryDB":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = {}
        return cls._instance

    def _entity(self, entity: str) -> Dict[str, Any]:
        return self._store.setdefault(entity, {"data": {}, "index": []})

    def insert(self, entity: str, key: str, record: Any) -> Any:
        edb = self._entity(entity)
        if key in edb["data"]:
            raise KeyError(f"{entity} with key '{key}' already exists")
        edb["data"][key] = record
        edb["index"].append(key)
        return record

    def find_one(self, entity: str, key: str) -> Any:
        edb = self._entity(entity)
        if key not in edb["data"]:
            raise KeyError(f"{entity} with key '{key}' not found")
        return edb["data"][key]

    def find(self, entity: str) -> List[Any]:
        edb = self._entity(entity)
        return [edb["data"][key] for key in edb["index"]]

    def update(self, entity: str, key: str, record: Any) -> Any:
        edb = self._entity(entity)
        if key not in edb["data"]:
            raise KeyError(f"{entity} with key '{key}' not found")
        if hasattr(record, "updated_at"):
            record.updated_at = time.time()
        edb["data"][key] = record
        return record

    def delete(self, entity: str, key: str) -> None:
        edb = self._entity(entity)
        if key not in edb["data"]:
            raise KeyError(f"{entity} with key '{key}' not found")
        del edb["data"][key]
        edb["index"].remove(key)

    def clear(self, entity: str) -> None:
        self._store[entity] = {"data": {}, "index": []}


db = InMemoryDB()
