import pkgutil
from abc import ABC, abstractmethod
from enum import Enum


class PluginType(Enum):
    SOURCE = 1
    SINK = 2


class BasePlugin(ABC):
    class Unknown(Exception):
        pass

    _registry = {}  # Registered subclasses.

    def __init_subclass__(cls) -> None:
        """Register subclasses for later instantiation."""
        super().__init_subclass__()
        cls._registry[cls.plugin_name] = cls  # Add class to registry.

    def __new__(cls, plugin_name):
        """Create instance of appropriate subclass."""
        subclass = cls._registry.get(plugin_name.upper())
        if subclass:
            return object.__new__(subclass)
        else:
            # No subclass with matching prefix found (and no default).
            raise cls.Unknown(f'plugin "{plugin_name}" not found')

    @abstractmethod
    def configure():
        pass

    @abstractmethod
    def process():
        pass


def plugin_factory(plugin_name):
    return BasePlugin(plugin_name)


def load_plugin_modules():
    for module_finder, module_name, ispkg in pkgutil.iter_modules(__path__):
        if ispkg:
            continue

        # Only auto-load dynamic modules.
        if not module_name.startswith(("plugin_", "source_", "sink_")):
            continue

        # See PEP 302 for details.
        module_loader = module_finder.find_module(module_name)
        module_loader.load_module(module_name)


load_plugin_modules()
