from contextlib import suppress
from typing import Any

from apispec import APISpec, BasePlugin
from apispec.exceptions import DuplicateComponentNameError
from packaging.version import Version

from apispec_pydantic_plugin.errors import ResolverNotFound
from apispec_pydantic_plugin.models import BaseModelAlias
from apispec_pydantic_plugin.resolver import SchemaResolver


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
        self, name: str, definition: dict[Any, Any], **kwargs: Any
    ) -> dict[str, Any] | None:
        """Return the schema of the requested identifier.

        Parameters:
            name: The identifier which a schema can be referenced.
            definition: Schema definition
            kwargs: All additional keyword arguments sent to `APISpec.schema()`
        """
        model: BaseModelAlias | None = kwargs.pop("model", None)
        if model:
            schema = model.schema(ref_template="#/components/schemas/{model}")

            if self.spec and "definitions" in schema:
                for (k, v) in schema["definitions"].items():
                    with suppress(DuplicateComponentNameError):
                        self.spec.components.schema(k, v)

            if "definitions" in schema:
                del schema["definitions"]

            return schema

        return None

    def operation_helper(
        self,
        path: str | None = None,
        operations: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if self.resolver is None:
            raise ResolverNotFound("SchemaResolver was not initialized")
        self.resolver.resolve_operations(operations=operations, kwargs=kwargs)
