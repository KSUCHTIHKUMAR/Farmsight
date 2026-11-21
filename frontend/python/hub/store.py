"""Persistent key/value store (port of src/hub/store.ts; localStorage -> JSON file)."""
from __future__ import annotations

import json
import os
import random
import string
from dataclasses import asdict, dataclass
from typing import Any, Callable, Literal, Optional, TypeVar, Union

T = TypeVar("T")

STORE_PATH = os.environ.get("FARMSIGHT_STORE_FILE", os.path.join(os.path.expanduser("~"), ".farmsight_store.json"))


def _probe() -> bool:
    try:
        d = os.path.dirname(STORE_PATH) or "."
        return os.path.isdir(d) and os.access(d, os.W_OK)
    except OSError:
        return False


# True only if we can write the store file. Data is never synced to a server.
storage_available: bool = _probe()

_cache: dict[str, Any] = {}
_listeners: set[Callable[[], None]] = set()


def _read_file() -> dict[str, Any]:
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(key: str, init: T) -> T:
    if key in _cache:
        return _cache[key]
    v = init
    if storage_available:
        raw = _read_file().get(key)
        if raw:
            v = raw
    _cache[key] = v
    return v


def set(key: str, v: Any) -> None:  # noqa: A001 - mirrors the TS API
    _cache[key] = v
    if storage_available:
        try:
            data = _read_file()
            data[key] = v
            with open(STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except (OSError, TypeError, ValueError):
            pass  # value stays in memory for this session
    for l in list(_listeners):
        l()


def subscribe(l: Callable[[], None]) -> Callable[[], None]:
    _listeners.add(l)

    def unsubscribe() -> None:
        _listeners.discard(l)

    return unsubscribe


def use_stored(key: str, init: T) -> tuple[T, Callable[[Union[T, Callable[[T], T]]], None]]:
    """Return (current value, update). update accepts a value or a function of the previous value."""

    def update(u: Union[T, Callable[[T], T]]) -> None:
        set(key, u(get(key, init)) if callable(u) else u)

    return get(key, init), update


JOURNAL_KEY = "farmsight.journal.v1"
PLANS_KEY = "farmsight.plans.v1"

JournalType = Literal["observation", "scan", "watering", "fertilizer", "harvest", "note"]


@dataclass
class JournalEntry:
    id: str
    date: str
    type: JournalType
    crop: str
    title: str
    notes: str
    source: Literal["manual", "scan", "demo"]
    quantity: Optional[float] = None
    unit: Optional[str] = None
    ai_suggestion: Optional[bool] = None
    confirmed: Optional[bool] = None


def uid() -> str:
    chars = string.digits + string.ascii_lowercase
    return "".join(random.choice(chars) for _ in range(8))


def add_journal_entry(e: Union[dict[str, Any], JournalEntry]) -> None:
    """Prepend an entry (without id, or any id which is replaced) to the journal."""
    entry = asdict(e) if isinstance(e, JournalEntry) else dict(e)
    entry = {k: v for k, v in entry.items() if v is not None}
    entry["id"] = uid()
    set(JOURNAL_KEY, [entry, *get(JOURNAL_KEY, [])])
