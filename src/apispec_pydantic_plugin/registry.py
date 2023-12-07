from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from apispec_pydantic_plugin.errors import ModelNotFoundError

if TYPE_CHECKING:
    from apispec_pydantic_plugin.models import BaseModelAlias


class Registry:
    # we're using BaseModel instead of ApiBaseModel so that users may manually
    # register classes with the registry, if they choose.
    registered: ClassVar[dict[str, type[BaseModelAlias]]] = {}

    @classmethod
    def register(cls, model: type[BaseModelAlias]) -> None:
        name = model.__name__
        if name in cls.registered:
            raise ValueError(f"Duplicate schema received by registry: {name}")
        cls.registered[name] = model

    @classmethod
    def get(cls, name: str) -> type[BaseModelAlias]:
        try:
            return cls.registered[name]
        except KeyError as e:
            raise ModelNotFoundError(f"Model not found: {name}") from e
