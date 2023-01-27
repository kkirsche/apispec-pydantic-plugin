from apispec_pydantic_plugin import ApiGenericModel, ApiBaseModel, Registry
from typing import Generic, TypeVar


_T = TypeVar("_T")


class ApiModel(ApiBaseModel):
    items: list[int]


class GenericApiModel(ApiGenericModel, Generic[_T]):
    items: list[_T]


def test_api_model_is_registered() -> None:
    assert Registry.get(name=ApiModel.__name__) is ApiModel


def test_generic_api_model_is_registered() -> None:
    assert Registry.get(name=GenericApiModel.__name__) is GenericApiModel
