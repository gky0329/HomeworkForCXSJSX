from typing import Any


class Container:
    _services: dict[type, Any] = {}

    @classmethod
    def register(cls, service_class: type, instance: Any) -> None:
        cls._services[service_class] = instance

    @classmethod
    def resolve(cls, service_class: type) -> Any:
        if service_class not in cls._services:
            raise KeyError(f"Service {service_class.__name__} not registered")
        return cls._services[service_class]

    @classmethod
    def reset(cls) -> None:
        cls._services.clear()
