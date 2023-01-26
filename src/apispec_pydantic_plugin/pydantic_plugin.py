from typing import Any

from apispec import APISpec, BasePlugin
from packaging.version import Version

from apispec_pydantic_plugin.errors import ResolverNotFound
from apispec_pydantic_plugin.registry import Registry
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
        self.openapi_version = spec.openapi_version
        self.resolver = SchemaResolver(openapi_version=self.openapi_version)

    def schema_helper(
        self, name: str, definition: dict[Any, Any], **kwargs: Any
    ) -> dict[str, Any] | None:
        """Return the schema of the requested identifier.

        Parameters:
            name: The identifier which a schema can be referenced.
            definition: Schema definition
            kwargs: All additional keyword arguments sent to `APISpec.schema()`
        """
        schema = kwargs.get("schema")
        model = Registry.get(name)
        schema = model.schema(ref_template="#/components/schemas/{model}")
        if "definitions" in schema:
            del schema["definitions"]
        return schema

    def operation_helper(
        self,
        path: str | None = None,
        operations: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if self.resolver is None:
            raise ResolverNotFound("SchemaResolver was not initialized")
        self.resolver.resolve_operations(operations=operations, kwargs=kwargs)
