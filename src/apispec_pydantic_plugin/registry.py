from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from apispec_pydantic_plugin.errors import ModelNotFoundError

if TYPE_CHECKING:
    from apispec_pydantic_plugin.models import BaseModelAlias

_T = TypeVar("_T")


class Registry(Generic[_T]):
    # we're using BaseModel instead of ApiBaseModel so that users may manually
    # register classes with the registry, if they choose.
    registered: dict[str, type["BaseModelAlias[_T]"]] = {}

    @classmethod
    def register(cls, model: type["BaseModelAlias[_T]"]) -> None:
        name = model.__name__
        if name in cls.registered:
            raise ValueError(f"Duplicate schema received by registry: {name}")
        cls.registered[name] = model

    @classmethod
    def get(cls, name: str) -> type["BaseModelAlias[_T]"]:
        try:
            return cls.registered[name]
        except KeyError as e:
            raise ModelNotFoundError(f"Model not found: {name}") from e
