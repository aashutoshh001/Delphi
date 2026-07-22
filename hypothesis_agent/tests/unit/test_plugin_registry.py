import pytest

from hypothesis_agent.plugins.registry import (
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
    PluginRegistry,
)


def test_register_and_get():
    registry: PluginRegistry[str] = PluginRegistry()
    registry.register("a", "value-a")
    assert registry.get("a") == "value-a"


def test_duplicate_register_raises_without_override():
    registry: PluginRegistry[str] = PluginRegistry()
    registry.register("a", "value-a")
    with pytest.raises(PluginAlreadyRegisteredError):
        registry.register("a", "value-b")


def test_override_replaces_existing():
    registry: PluginRegistry[str] = PluginRegistry()
    registry.register("a", "value-a")
    registry.register("a", "value-b", override=True)
    assert registry.get("a") == "value-b"


def test_missing_key_raises_with_available_listed():
    registry: PluginRegistry[str] = PluginRegistry()
    registry.register("a", "value-a")
    with pytest.raises(PluginNotFoundError, match="a"):
        registry.get("missing")


def test_all_returns_a_copy_not_the_internal_dict():
    registry: PluginRegistry[str] = PluginRegistry()
    registry.register("a", "value-a")
    snapshot = registry.all()
    snapshot["b"] = "value-b"
    assert "b" not in registry
