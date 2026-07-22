"""Generic plugin registry used for every extension point in the system:
business lenses, evaluators, critics, search heuristics, memory policies, and
(in di/container.py) infrastructure backend factories. Adding a new plugin of
any kind is one `register()` call — never a change to a consumer."""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class PluginAlreadyRegisteredError(KeyError):
    pass


class PluginNotFoundError(KeyError):
    pass


class PluginRegistry(Generic[T]):
    def __init__(self, kind: str = "plugin") -> None:
        self._kind = kind
        self._items: dict[str, T] = {}

    def register(self, key: str, plugin: T, *, override: bool = False) -> None:
        if not override and key in self._items:
            raise PluginAlreadyRegisteredError(
                f"{self._kind} '{key}' is already registered; pass override=True to replace it"
            )
        self._items[key] = plugin

    def get(self, key: str) -> T:
        try:
            return self._items[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._items)) or "<none>"
            raise PluginNotFoundError(
                f"{self._kind} '{key}' not found. Available: {available}"
            ) from exc

    def has(self, key: str) -> bool:
        return key in self._items

    def all(self) -> dict[str, T]:
        return dict(self._items)

    def keys(self) -> list[str]:
        return list(self._items)

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)
