"""Test data generation module using Faker and JSON schemas."""

import random
import string
from typing import Any, Dict, List, Optional, Union
from faker import Faker
import re


class DataFaker:
    """Generate fake data based on OpenAPI schemas."""
    
    def __init__(self, locale: str = "en_US") -> None:
        self.fake = Faker(locale)
    
    def generate_from_schema(self, schema: Dict[str, Any]) -> Any:
        """Generate fake data based on JSON schema."""
        if not schema:
            return None
        
        schema_type = schema.get("type")
        
        if schema_type == "object":
            return self._generate_object(schema)
        elif schema_type == "array":
            return self._generate_array(schema)
        elif schema_type == "string":
            return self._generate_string(schema)
        elif schema_type == "integer":
            return self._generate_integer(schema)
        elif schema_type == "number":
            return self._generate_number(schema)
        elif schema_type == "boolean":
            return self._generate_boolean()
        elif "enum" in schema:
            return self._generate_enum(schema)
        else:
            # Try to infer type from format or pattern
            return self._generate_by_format(schema)
    
    def _generate_object(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate object from schema."""
        result = {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for prop_name, prop_schema in properties.items():
            # Always generate required fields, sometimes generate optional ones
            if prop_name in required or random.random() < 0.7:
                result[prop_name] = self.generate_from_schema(prop_schema)
        
        return result
    
    def _generate_array(self, schema: Dict[str, Any]) -> List[Any]:
        """Generate array from schema."""
        items_schema = schema.get("items", {})
        min_items = schema.get("minItems", 1)
        max_items = schema.get("maxItems", 5)
        
        length = random.randint(min_items, max_items)
        return [self.generate_from_schema(items_schema) for _ in range(length)]
    
    def _generate_string(self, schema: Dict[str, Any]) -> str:
        """Generate string from schema."""
        format_type = schema.get("format")
        pattern = schema.get("pattern")
        min_length = schema.get("minLength", 1)
        max_length = schema.get("maxLength", 50)
        
        # Handle specific formats
        if format_type == "email":
            return self.fake.email()
        elif format_type == "uri":
            return self.fake.url()
        elif format_type == "date":
            return self.fake.date().isoformat()
        elif format_type == "date-time":
            return self.fake.date_time().isoformat()
        elif format_type == "uuid":
            return str(self.fake.uuid4())
        elif format_type == "password":
            return self.fake.password(length=random.randint(8, 16))
        elif format_type == "byte":
            return self.fake.binary(length=random.randint(10, 100)).decode('latin1')
        elif format_type == "binary":
            return self.fake.binary(length=random.randint(10, 100)).decode('latin1')
        
        # Handle pattern if provided
        if pattern:
            return self._generate_by_pattern(pattern, min_length, max_length)
        
        # Default string generation
        length = random.randint(min_length, min(max_length, 100))
        return self.fake.text(max_nb_chars=length).replace('\n', ' ')[:length]
    
    def _generate_integer(self, schema: Dict[str, Any]) -> int:
        """Generate integer from schema."""
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", 1000)
        return random.randint(minimum, maximum)
    
    def _generate_number(self, schema: Dict[str, Any]) -> float:
        """Generate number from schema."""
        minimum = schema.get("minimum", 0.0)
        maximum = schema.get("maximum", 1000.0)
        return round(random.uniform(minimum, maximum), 2)
    
    def _generate_boolean(self) -> bool:
        """Generate boolean value."""
        return random.choice([True, False])
    
    def _generate_enum(self, schema: Dict[str, Any]) -> Any:
        """Generate value from enum."""
        enum_values = schema.get("enum", [])
        return random.choice(enum_values) if enum_values else None
    
    def _generate_by_format(self, schema: Dict[str, Any]) -> Any:
        """Generate data by inferring from format or other hints."""
        format_type = schema.get("format")
        
        if format_type:
            return self._generate_string(schema)
        
        # If no type specified, try to guess from other properties
        if "enum" in schema:
            return self._generate_enum(schema)
        elif "properties" in schema:
            return self._generate_object(schema)
        elif "items" in schema:
            return self._generate_array(schema)
        else:
            return self.fake.word()
    
    def _generate_by_pattern(self, pattern: str, min_length: int, max_length: int) -> str:
        """Generate string matching a regex pattern (simplified)."""
        # This is a simplified pattern matcher for common cases
        # For complex patterns, we'll generate a reasonable default
        
        if pattern == r"^\d+$":
            length = random.randint(min_length, min(max_length, 10))
            return ''.join(random.choices(string.digits, k=length))
        elif pattern == r"^[a-zA-Z]+$":
            length = random.randint(min_length, min(max_length, 20))
            return ''.join(random.choices(string.ascii_letters, k=length))
        elif pattern == r"^[a-zA-Z0-9]+$":
            length = random.randint(min_length, min(max_length, 20))
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        else:
            # For complex patterns, generate a reasonable string
            length = random.randint(min_length, min(max_length, 20))
            return self.fake.pystr(min_chars=length, max_chars=length)
    
    def generate_path_param(self, param_name: str, param_schema: Optional[Dict[str, Any]] = None) -> str:
        """Generate path parameter value."""
        if param_schema:
            value = self.generate_from_schema(param_schema)
            return str(value) if value is not None else "1"
        
        # Generate based on parameter name hints
        name_lower = param_name.lower()
        
        if "id" in name_lower:
            return str(random.randint(1, 1000))
        elif "uuid" in name_lower:
            return str(self.fake.uuid4())
        elif "name" in name_lower:
            return self.fake.word()
        elif "code" in name_lower:
            return self.fake.pystr(min_chars=3, max_chars=10)
        else:
            return str(random.randint(1, 100))
    
    def generate_query_param(self, param_name: str, param_schema: Optional[Dict[str, Any]] = None) -> str:
        """Generate query parameter value."""
        if param_schema:
            value = self.generate_from_schema(param_schema)
            return str(value) if value is not None else ""
        
        # Generate based on parameter name hints
        name_lower = param_name.lower()
        
        if "limit" in name_lower or "size" in name_lower:
            return str(random.randint(10, 100))
        elif "offset" in name_lower or "page" in name_lower:
            return str(random.randint(0, 10))
        elif "sort" in name_lower:
            return random.choice(["asc", "desc"])
        elif "filter" in name_lower or "search" in name_lower:
            return self.fake.word()
        else:
            return self.fake.word()
    
    def generate_header_value(self, header_name: str, header_schema: Optional[Dict[str, Any]] = None) -> str:
        """Generate header value."""
        if header_schema:
            value = self.generate_from_schema(header_schema)
            return str(value) if value is not None else ""
        
        name_lower = header_name.lower()
        
        if "authorization" in name_lower:
            return f"Bearer {self.fake.uuid4()}"
        elif "content-type" in name_lower:
            return "application/json"
        elif "user-agent" in name_lower:
            return self.fake.user_agent()
        elif "accept" in name_lower:
            return "application/json"
        else:
            return self.fake.word()