"""Tests for the data faker module."""

import pytest
from openapi2locust.data_faker import DataFaker


class TestDataFaker:
    """Test cases for DataFaker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.faker = DataFaker()
    
    def test_generate_string_basic(self):
        """Test basic string generation."""
        schema = {"type": "string"}
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, str)
        assert len(result) >= 1
    
    def test_generate_string_with_length_constraints(self):
        """Test string generation with length constraints."""
        schema = {
            "type": "string",
            "minLength": 5,
            "maxLength": 10
        }
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, str)
        assert 5 <= len(result) <= 10
    
    def test_generate_string_with_format(self):
        """Test string generation with specific formats."""
        # Email format
        schema = {"type": "string", "format": "email"}
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, str)
        assert "@" in result
        
        # URI format
        schema = {"type": "string", "format": "uri"}
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, str)
        assert result.startswith(("http://", "https://"))
        
        # UUID format
        schema = {"type": "string", "format": "uuid"}
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, str)
        assert len(result) == 36  # UUID length with dashes
    
    def test_generate_integer(self):
        """Test integer generation."""
        schema = {"type": "integer"}
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, int)
        
        # With constraints
        schema = {
            "type": "integer",
            "minimum": 10,
            "maximum": 20
        }
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, int)
        assert 10 <= result <= 20
    
    def test_generate_number(self):
        """Test number generation."""
        schema = {"type": "number"}
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, (int, float))
        
        # With constraints
        schema = {
            "type": "number",
            "minimum": 1.5,
            "maximum": 5.5
        }
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, (int, float))
        assert 1.5 <= result <= 5.5
    
    def test_generate_boolean(self):
        """Test boolean generation."""
        schema = {"type": "boolean"}
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, bool)
    
    def test_generate_enum(self):
        """Test enum value generation."""
        schema = {
            "type": "string",
            "enum": ["red", "blue", "green"]
        }
        result = self.faker.generate_from_schema(schema)
        assert result in ["red", "blue", "green"]
    
    def test_generate_array(self):
        """Test array generation."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4
        }
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, list)
        assert 2 <= len(result) <= 4
        assert all(isinstance(item, str) for item in result)
    
    def test_generate_object(self):
        """Test object generation."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "email"]
        }
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, dict)
        assert "name" in result
        assert "email" in result
        assert isinstance(result["name"], str)
        assert "@" in result["email"]
    
    def test_generate_nested_object(self):
        """Test nested object generation."""
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "profile": {
                            "type": "object",
                            "properties": {
                                "bio": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, dict)
        if "user" in result:  # Optional property
            assert isinstance(result["user"], dict)
    
    def test_generate_path_param(self):
        """Test path parameter generation."""
        # With schema
        schema = {"type": "integer"}
        result = self.faker.generate_path_param("userId", schema)
        assert isinstance(result, str)
        assert result.isdigit()
        
        # Without schema, based on name
        result = self.faker.generate_path_param("id")
        assert isinstance(result, str)
        assert result.isdigit()
        
        result = self.faker.generate_path_param("uuid")
        assert isinstance(result, str)
        assert len(result) == 36  # UUID format
        
        result = self.faker.generate_path_param("name")
        assert isinstance(result, str)
    
    def test_generate_query_param(self):
        """Test query parameter generation."""
        # With schema
        schema = {"type": "string"}
        result = self.faker.generate_query_param("search", schema)
        assert isinstance(result, str)
        
        # Without schema, based on name
        result = self.faker.generate_query_param("limit")
        assert isinstance(result, str)
        assert result.isdigit()
        
        result = self.faker.generate_query_param("sort")
        assert result in ["asc", "desc"]
    
    def test_generate_header_value(self):
        """Test header value generation."""
        # With schema
        schema = {"type": "string"}
        result = self.faker.generate_header_value("X-Custom-Header", schema)
        assert isinstance(result, str)
        
        # Without schema, based on name
        result = self.faker.generate_header_value("Authorization")
        assert isinstance(result, str)
        assert result.startswith("Bearer ")
        
        result = self.faker.generate_header_value("Content-Type")
        assert result == "application/json"
        
        result = self.faker.generate_header_value("User-Agent")
        assert isinstance(result, str)
    
    def test_generate_by_pattern(self):
        """Test pattern-based string generation."""
        # Digits only
        result = self.faker._generate_by_pattern(r"^\d+$", 3, 5)
        assert isinstance(result, str)
        assert result.isdigit()
        assert 3 <= len(result) <= 5
        
        # Letters only
        result = self.faker._generate_by_pattern(r"^[a-zA-Z]+$", 4, 6)
        assert isinstance(result, str)
        assert result.isalpha()
        assert 4 <= len(result) <= 6
        
        # Alphanumeric
        result = self.faker._generate_by_pattern(r"^[a-zA-Z0-9]+$", 5, 8)
        assert isinstance(result, str)
        assert result.isalnum()
        assert 5 <= len(result) <= 8
    
    def test_generate_from_empty_schema(self):
        """Test generation from empty or None schema."""
        result = self.faker.generate_from_schema(None)
        assert result is None
        
        result = self.faker.generate_from_schema({})
        assert result is not None  # Should generate something reasonable
    
    def test_generate_complex_schema(self):
        """Test generation from a complex schema."""
        schema = {
            "type": "object",
            "properties": {
                "users": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["active", "inactive", "pending"]
                            },
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "created": {"type": "string", "format": "date-time"},
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["id", "name", "status"]
                    }
                }
            },
            "required": ["users"]
        }
        
        result = self.faker.generate_from_schema(schema)
        assert isinstance(result, dict)
        assert "users" in result
        assert isinstance(result["users"], list)
        
        if result["users"]:  # If array is not empty
            user = result["users"][0]
            assert isinstance(user, dict)
            assert "id" in user
            assert "name" in user
            assert "status" in user
            assert user["status"] in ["active", "inactive", "pending"]