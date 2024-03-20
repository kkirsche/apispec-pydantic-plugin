from contextlib import suppress
from typing import TYPE_CHECKING, Any

from apispec import APISpec, BasePlugin
from apispec.exceptions import DuplicateComponentNameError
from packaging.version import Version

from apispec_pydantic_plugin.errors import ResolverNotFoundError
from apispec_pydantic_plugin.resolver import SchemaResolver

if TYPE_CHECKING:
    from apispec_pydantic_plugin.models import BaseModelAlias


class PydanticPlugin(BasePlugin):
    """APISpec plugin for translating pydantic models to OpenAPI/JSONSchema format."""

    spec: APISpec | None
    openapi_version: Version | None
    resolver: SchemaResolver | None

    def __init__(self) -> None:
        self.spec = None
        self.openapi_version = None

        self.resolver = None

    def init_spec(self, spec: APISpec) -> None:
        """Initialize plugin with APISpec object

        :param APISpec spec: APISpec object this plugin instance is attached to
        """
        super().init_spec(spec=spec)
        self.spec = spec
        self.resolver = SchemaResolver(spec=self.spec)

    def schema_helper(
        self,
        name: str,  # noqa: ARG002
        definition: dict[Any, Any],  # noqa: ARG002
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Return the schema of the requested identifier.

        Parameters:
            name: The identifier which a schema can be referenced.
            definition: Schema definition
            kwargs: All additional keyword arguments sent to `APISpec.schema()`
        """
        model: BaseModelAlias | None = kwargs.pop("model", None)
        if model:
            schema = model.model_json_schema(
                ref_template="#/components/schemas/{model}"  # noqa: RUF027
            )

            # definitions is for Pydantic v1
            # $defs is for Pydantic v2
            # I kept both because this used to work, but I don't remember if it was
            # on an earlier version of v2 or the last version of 1. It shouldn't harm
            # anything though other than a slight performance hit for the looping
            for key in ("definitions", "$defs"):
                if self.spec and key in schema:
                    for k, v in schema[key].items():
                        with suppress(DuplicateComponentNameError):
                            self.spec.components.schema(k, v)

                if key in schema:
                    del schema[key]

            return schema

        return None

    def operation_helper(
        self,
        path: str | None = None,  # noqa: ARG002
        operations: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if self.resolver is None:
            raise ResolverNotFoundError("SchemaResolver was not initialized")
        self.resolver.resolve_operations(operations=operations, kwargs=kwargs)
