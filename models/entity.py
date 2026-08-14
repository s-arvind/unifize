import time
from dataclasses import dataclass, field

import ulid


def ulid_new() -> str:
    return str(ulid.ULID())


@dataclass(kw_only=True)
class Entity:
    id: str = field(default_factory=ulid_new)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deleted: bool = False
