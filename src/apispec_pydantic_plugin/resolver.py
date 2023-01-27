from typing import Any

from packaging.version import Version
from pydantic import BaseModel

from apispec_pydantic_plugin.models import BaseModelAlias
from apispec_pydantic_plugin.registry import Registry


def resolve_schema_instance(
    schema: type[BaseModelAlias] | BaseModelAlias | str,
) -> type[BaseModelAlias]:
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return Registry.get(name=schema.__name__)
    if isinstance(schema, BaseModel):
        return schema.__class__
    return Registry.get(name=schema)


class SchemaResolver:
    openapi_version: Version

    def __init__(self, openapi_version: Version) -> None:
        self.openapi_version = openapi_version

    def resolve_operations(
        self, operations: dict[str, Any] | None, **kwargs: Any
    ) -> None:
        if operations is None:
            return

        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            if "parameters" in operation:
                operation["parameters"] = self.resolve_parameters(
                    operation["parameters"]
                )
            if self.openapi_version.major >= 3:
                self.resolve_callback(operation.get("callbacks", {}))
                if "requestBody" in operation:
                    self.resolve_schema(operation["requestBody"])
            for response in operation.get("responses", {}).values():
                self.resolve_response(response)

    def resolve_callback(self, callbacks: Any) -> None:
        for callback in callbacks.values():
            if isinstance(callback, dict):
                for path in callback.values():
                    self.resolve_operations(path)

    def resolve_parameters(self, parameters: Any) -> Any | list[Any]:
        resolved = []
        for parameter in parameters:
            if (
                isinstance(parameter, dict)
                and not isinstance(parameter.get("schema", {}), dict)
                and "in" in parameter
            ):
                schema_instance = resolve_schema_instance(parameter.pop("schema"))
                raise NotImplementedError("This is still under development")
                resolved += self.converter.schema2parameters(
                    schema_instance, location=parameter.pop("in"), **parameter
                )
            else:
                self.resolve_schema(parameter)
                resolved.append(parameter)
        return resolved

    def resolve_response(self, response: Any) -> None:
        self.resolve_schema(response)
        if "headers" in response:
            for header in response["headers"].values():
                self.resolve_schema(header)

    def resolve_schema(self, data: Any) -> None:
        if not isinstance(data, dict):
            return

        # OAS 2 component or OAS 3 parameter or header
        if "schema" in data:
            data["schema"] = self.resolve_schema_dict(data["schema"])
        # OAS 3 component except header
        if self.openapi_version.major >= 3:
            if "content" in data:
                for content in data["content"].values():
                    if "schema" in content:
                        content["schema"] = self.resolve_schema_dict(content["schema"])

    def resolve_schema_dict(
        self, schema: dict[str, Any] | type[BaseModelAlias] | BaseModelAlias | str
    ) -> Any:
        if not isinstance(schema, dict):
            resolved = resolve_schema_instance(schema=schema).schema
            return resolved

        if schema.get("type") == "array" and "items" in schema:
            schema["items"] = self.resolve_schema_dict(schema["items"])
        if schema.get("type") == "object" and "properties" in schema:
            schema["properties"] = {
                k: self.resolve_schema_dict(v) for k, v in schema["properties"].items()
            }
        for keyword in ("oneOf", "anyOf", "allOf"):
            if keyword in schema:
                schema[keyword] = [self.resolve_schema_dict(s) for s in schema[keyword]]
        if "not" in schema:
            schema["not"] = self.resolve_schema_dict(schema["not"])
        return schema
        # return self.converter.resolve_nested_schema(schema)
