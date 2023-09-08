from typing import TypeAlias, TypeVar

from pydantic import BaseModel, RootModel

from apispec_pydantic_plugin.registry import Registry

_T = TypeVar("_T")


class ApiBaseModel(BaseModel):
    def __init_subclass__(cls) -> None:
        Registry.register(cls)
        return super().__init_subclass__()


class ApiRootModel(RootModel[_T]):
    def __init_subclass__(cls) -> None:
        Registry.register(cls)
        return super().__init_subclass__()


BaseModelAlias: TypeAlias = ApiBaseModel | ApiRootModel | BaseModel
