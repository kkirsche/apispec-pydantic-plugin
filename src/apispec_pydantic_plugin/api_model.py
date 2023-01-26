from typing import TypeAlias

from pydantic import BaseModel

from apispec_pydantic_plugin.registry import Registry


class ApiBaseModel(BaseModel):
    def __init_subclass__(cls) -> None:
        Registry.register(cls)
        return super().__init_subclass__()


BaseModelAlias: TypeAlias = ApiBaseModel | BaseModel
