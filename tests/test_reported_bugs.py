from apispec import APISpec

from apispec_pydantic_plugin import ApiBaseModel, PydanticPlugin


def test_issue_22() -> None:
    """Test the bug reported in issue 22.

    https://github.com/kkirsche/apispec-pydantic-plugin/issues/22
    """

    # Define your Pydantic models
    class Item(ApiBaseModel):
        id: int
        name: str
        description: str | None = None

    class Error(ApiBaseModel):
        code: int
        message: str

    # Create an APISpec instance with the Pydantic plugin
    spec = APISpec(
        title="Test Issue 22",
        version="1.0.0",
        openapi_version="3.0.2",
        plugins=[PydanticPlugin()],
    )

    # Add your Pydantic models to the spec
    spec.components.schema("Item", schema=Item)
    spec.components.schema("Error", schema=Error)

    # Generate the OpenAPI spec
    assert spec.to_dict() == {
        "components": {
            "schemas": {
                "Error": {
                    "properties": {
                        "code": {"title": "Code", "type": "integer"},
                        "message": {"title": "Message", "type": "string"},
                    },
                    "required": ["code", "message"],
                    "title": "Error",
                    "type": "object",
                },
                "Item": {
                    "properties": {
                        "description": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                            "default": None,
                            "title": "Description",
                        },
                        "id": {"title": "Id", "type": "integer"},
                        "name": {"title": "Name", "type": "string"},
                    },
                    "required": ["id", "name"],
                    "title": "Item",
                    "type": "object",
                },
            }
        },
        "info": {"title": "Test Issue 22", "version": "1.0.0"},
        "openapi": "3.0.2",
        "paths": {},
    }
