from contextlib import suppress
from typing import Any, ClassVar

from apispec import APISpec
from apispec.exceptions import DuplicateComponentNameError
from packaging.version import Version
from pydantic import BaseModel

from apispec_pydantic_plugin.constants import OPENAPI_VERSION_MAJOR_V3
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
    """SchemaResolver is responsible for modifying a schema.

    This class relies heavily on the fact that dictionaries are mutable,
    so rather than catching a return value, we can often modify the object without
    a return statement.

    Proceed with caution as a result, as it can be somewhat confusing.
    """

    openapi_version: Version
    refs: ClassVar[dict[str, dict[str, Any]]] = {}

    def __init__(self, spec: APISpec) -> None:
        self.spec = spec
        self.openapi_version = spec.openapi_version

    def resolve_operations(
        self,
        operations: dict[str, Any] | None,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Resolves an operations dictionary into an OpenAPI operations object.

        https://spec.openapis.org/oas/v3.1.0#operation-object

        Args:
            operations (dict[str, Any] | None): The operations for a specific route,
                if documented.

                Example:
                {
                    'get': {
                        'description': 'Create a network quiet time announcement',
                        'tags': ['Announcements'],
                        'requestBody': {
                            'description': 'The details of the Network Quiet Time',
                            'content': {
                                'application/json': {
                                    'schema': 'CreateNetworkQuietTimeRequest'
                                }
                            }
                        },
                        'responses': {
                            '200': {
                                'description': 'Announcement successfully created.',
                                'content': {
                                    'application/json': {
                                        'schema': 'SerializedAnnouncement'
                                    }
                                }
                            },
                            '400': {
                                'description': 'An invalid request was received.',
                                'content': {'application/json': { 'schema': 'Problem'}}
                            },
                            '403': {
                                'description': 'The user was not authorized to perform this action.',
                                'content': {'application/json': {'schema': 'Problem'}}
                            },
                            '500': {
                                'description': 'An unexpected error occurred while retrieving the announcements',
                                'content': {'application/json': {'schema': 'Problem'}}
                            }
                        }
                    }
                }
        """  # noqa: E501
        if operations is None:
            return

        for operation in operations.values():
            if not isinstance(operation, dict):
                continue

            if "parameters" in operation:
                operation["parameters"] = self.resolve_parameters(
                    operation["parameters"]
                )
            if self.openapi_version.major >= OPENAPI_VERSION_MAJOR_V3:
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

    def resolve_parameters(self, parameters: list[dict[str, Any]]) -> list[Any]:
        """Resolves the parameters portion of an operation object.

        This method is called by resolve_operations.

        TODO: Finish implementing this.

        Args:
            parameters (list[dict[str, Any]]): The parameters section of the operation.

            Example:
                [{
                    'in': 'path',
                    'name': 'pageSize',
                    'schema': {
                        'type': 'integer'
                    },
                    'required': True,
                    'description': 'The size of an individual page'
                }, {
                    'in': 'path',
                    'name': 'page',
                    'schema': {
                        'type': 'integer'
                    },
                    'required': True,
                    'description': 'The page to begin on'
                }]

        Returns:
            list[Any]: The resolved parameters
        """
        resolved = []
        for parameter in parameters:
            if (
                isinstance(parameter, dict)
                and not isinstance(parameter.get("schema", {}), dict)
                and "in" in parameter
            ):
                raise NotImplementedError(
                    "Parameter schemas are not currently supported."
                )
                # https://github.com/marshmallow-code/apispec/blob/28a0f334fa474be6a84651b3b73c17fb3ee10137/src/apispec/ext/marshmallow/schema_resolver.py#L87
                # convert a schema to a definition
                schema_instance = resolve_schema_instance(parameter.pop("schema"))
                resolved += self.converter.schema2parameters(
                    schema_instance, location=parameter.pop("in"), **parameter
                )
            else:  # noqa: RET506
                self.resolve_schema(parameter)
                resolved.append(parameter)
        return resolved

    def resolve_response(self, response: Any) -> None:
        self.resolve_schema(response)
        if "headers" in response:
            for header in response["headers"].values():
                self.resolve_schema(header)

    def resolve_schema(self, data: dict[str, Any] | Any) -> None:
        """Resolves a Pydantic model in an OpenAPI component or header.

        This method modifies the input dictionary, data, to translate
        Pydantic models to OpenAPI schema objects or reference objects.

        Args:
            data (Any): _description_
        """
        if not isinstance(data, dict):
            return

        # OAS 2 component or OAS 3 parameter or header
        if "schema" in data:
            data["schema"] = self.resolve_schema_dict(data["schema"])

        # OAS 3 component except header
        if self.openapi_version.major >= OPENAPI_VERSION_MAJOR_V3 and "content" in data:
            for content in data["content"].values():
                if "schema" in content:
                    content["schema"] = self.resolve_schema_dict(content["schema"])

    def resolve_schema_dict(
        self, schema: dict[str, Any] | type[BaseModelAlias] | BaseModelAlias | str
    ) -> Any:
        if not isinstance(schema, dict):
            return self.resolve_nested_schema(schema)

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

    def resolve_nested_schema(self, schema: Any) -> dict[str, Any]:
        self.register_schema(schema=schema)
        return self.get_ref_dict(schema=schema)

    def register_schema(self, schema: Any) -> None:
        resolved = resolve_schema_instance(schema=schema)
        with suppress(DuplicateComponentNameError):
            self.spec.components.schema(component_id=schema, model=resolved)

    def get_ref_dict(self, schema: Any) -> dict[str, Any]:
        """This method is responsible for storing a ref dictionary
        when we've seen a schema.

        Returns:
            dict[str, str]: _description_
        """
        if schema in self.refs:
            return self.refs[schema]

        if getattr(schema, "many", False):
            self.refs[schema] = {
                "type": "array",
                "items": {"$ref": f"#/components/schemas/{schema}"},
            }
        else:
            self.refs[schema] = {"$ref": f"#/components/schemas/{schema}"}
        return self.refs[schema]
