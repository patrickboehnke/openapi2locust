"""Tests for the OpenAPI parser module."""

import pytest
from pathlib import Path
import tempfile
import yaml

from openapi2locust.parser import OpenAPIParser


class TestOpenAPIParser:
    """Test cases for OpenAPIParser class."""
    
    def test_parser_initialization(self):
        """Test parser initialization with spec path."""
        spec_path = Path("test.yaml")
        parser = OpenAPIParser(spec_path)
        assert parser.spec_path == spec_path
        assert parser.spec == {}
        assert parser.servers == []
        assert parser.paths == {}
    
    def test_get_path_parameters(self):
        """Test extraction of path parameters."""
        parser = OpenAPIParser("dummy.yaml")
        
        # Test path with parameters
        path = "/users/{userId}/posts/{postId}"
        params = parser.get_path_parameters(path)
        assert params == ["userId", "postId"]
        
        # Test path without parameters
        path = "/users"
        params = parser.get_path_parameters(path)
        assert params == []
    
    def test_get_base_url_default(self):
        """Test getting base URL with default fallback."""
        parser = OpenAPIParser("dummy.yaml")
        assert parser.get_base_url() == "http://localhost"
    
    def test_get_base_url_from_servers(self):
        """Test getting base URL from servers list."""
        parser = OpenAPIParser("dummy.yaml")
        parser.servers = [{"url": "https://api.example.com"}]
        assert parser.get_base_url() == "https://api.example.com"
    
    def test_parse_valid_spec(self):
        """Test parsing a valid OpenAPI specification."""
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(spec_data, f)
            temp_path = f.name
        
        try:
            parser = OpenAPIParser(temp_path)
            result = parser.parse()
            
            assert result["openapi"] == "3.0.0"
            assert result["info"]["title"] == "Test API"
            assert "/users" in result["paths"]
        finally:
            Path(temp_path).unlink()
    
    def test_parse_invalid_spec(self):
        """Test parsing an invalid OpenAPI specification."""
        spec_data = {
            "invalid": "spec"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(spec_data, f)
            temp_path = f.name
        
        try:
            parser = OpenAPIParser(temp_path)
            with pytest.raises(ValueError, match="Failed to parse OpenAPI spec"):
                parser.parse()
        finally:
            Path(temp_path).unlink()
    
    def test_get_endpoints(self):
        """Test extraction of endpoints from parsed spec."""
        parser = OpenAPIParser("dummy.yaml")
        parser.paths = {
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users",
                    "responses": {"200": {"description": "Success"}}
                },
                "post": {
                    "summary": "Create user",
                    "responses": {"201": {"description": "Created"}}
                }
            },
            "/users/{id}": {
                "get": {
                    "summary": "Get user by ID",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }
        
        endpoints = parser.get_endpoints()
        
        assert len(endpoints) == 3
        
        # Check first endpoint
        get_users = next(e for e in endpoints if e["method"] == "GET" and e["path"] == "/users")
        assert get_users["operation_id"] == "getUsers"
        assert get_users["summary"] == "Get all users"
        
        # Check second endpoint
        post_users = next(e for e in endpoints if e["method"] == "POST" and e["path"] == "/users")
        assert post_users["summary"] == "Create user"
        
        # Check third endpoint with parameters
        get_user = next(e for e in endpoints if e["path"] == "/users/{id}")
        assert len(get_user["parameters"]) == 1
        assert get_user["parameters"][0]["name"] == "id"
    
    def test_get_schema_by_ref(self):
        """Test resolving schema references."""
        parser = OpenAPIParser("dummy.yaml")
        parser.spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        schema = parser.get_schema_by_ref("#/components/schemas/User")
        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "name" in schema["properties"]
        
        # Test invalid reference
        invalid_schema = parser.get_schema_by_ref("#/components/schemas/NonExistent")
        assert invalid_schema is None
    
    def test_get_request_schema(self):
        """Test extracting request body schema."""
        parser = OpenAPIParser("dummy.yaml")
        
        # Test request body with direct schema
        request_body = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}}
                    }
                }
            }
        }
        
        schema = parser.get_request_schema(request_body)
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        
        # Test request body with reference
        parser.spec = {
            "components": {
                "schemas": {
                    "CreateUser": {
                        "type": "object",
                        "properties": {"email": {"type": "string"}}
                    }
                }
            }
        }
        
        request_body_ref = {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/CreateUser"}
                }
            }
        }
        
        schema = parser.get_request_schema(request_body_ref)
        assert schema["type"] == "object"
        assert "email" in schema["properties"]
    
    def test_get_response_schema(self):
        """Test extracting response schema."""
        parser = OpenAPIParser("dummy.yaml")
        
        responses = {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "array",
                            "items": {"type": "object"}
                        }
                    }
                }
            }
        }
        
        schema = parser.get_response_schema(responses, "200")
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "object"
        
        # Test default response
        schema = parser.get_response_schema(responses)
        assert schema["type"] == "array"