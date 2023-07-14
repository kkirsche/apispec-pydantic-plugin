from typing import Generic, TypeVar

from apispec_pydantic_plugin import ApiBaseModel, Registry

_T = TypeVar("_T")


class ApiModel(ApiBaseModel):
    items: list[int]


class GenericApiModel(ApiBaseModel, Generic[_T]):
    items: list[_T]


def test_api_model_is_registered() -> None:
    assert Registry.get(name=ApiModel.__name__) is ApiModel


def test_generic_api_model_is_registered() -> None:
    assert Registry.get(name=GenericApiModel.__name__) is GenericApiModel
