"""OpenAPI specification parser module."""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename


class OpenAPIParser:
    """Parser for OpenAPI specifications."""
    
    def __init__(self, spec_path: Union[str, Path]) -> None:
        self.spec_path = Path(spec_path)
        self.spec: Dict[str, Any] = {}
        self.servers: List[Dict[str, Any]] = []
        self.paths: Dict[str, Any] = {}
        self.components: Dict[str, Any] = {}
        self.security_schemes: Dict[str, Any] = {}
    
    def parse(self) -> Dict[str, Any]:
        """Parse the OpenAPI specification file."""
        try:
            spec_dict, _ = read_from_filename(str(self.spec_path))
            validate_spec(spec_dict)
            self.spec = spec_dict
            
            self._extract_servers()
            self._extract_paths()
            self._extract_components()
            self._extract_security_schemes()
            
            return self.spec
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI spec: {e}")
    
    def _extract_servers(self) -> None:
        """Extract server information from the spec."""
        self.servers = self.spec.get("servers", [])
        if not self.servers:
            self.servers = [{"url": "http://localhost"}]
    
    def _extract_paths(self) -> None:
        """Extract path operations from the spec."""
        self.paths = self.spec.get("paths", {})
    
    def _extract_components(self) -> None:
        """Extract components (schemas, etc.) from the spec."""
        self.components = self.spec.get("components", {})
    
    def _extract_security_schemes(self) -> None:
        """Extract security schemes from components."""
        components = self.spec.get("components", {})
        self.security_schemes = components.get("securitySchemes", {})
    
    def get_base_url(self) -> str:
        """Get the base URL from the first server."""
        if self.servers:
            return self.servers[0]["url"]
        return "http://localhost"
    
    def get_endpoints(self) -> List[Dict[str, Any]]:
        """Extract all endpoints with their details."""
        endpoints = []
        
        for path, path_item in self.paths.items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "operation_id": operation.get("operationId", f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"),
                        "summary": operation.get("summary", ""),
                        "parameters": operation.get("parameters", []),
                        "request_body": operation.get("requestBody"),
                        "responses": operation.get("responses", {}),
                        "security": operation.get("security", self.spec.get("security", [])),
                        "tags": operation.get("tags", [])
                    }
                    endpoints.append(endpoint)
        
        return endpoints
    
    def get_path_parameters(self, path: str) -> List[str]:
        """Extract path parameters from a path string."""
        import re
        return re.findall(r'\{([^}]+)\}', path)
    
    def get_schema_by_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """Resolve a $ref to get the actual schema."""
        if not ref.startswith("#/"):
            return None
        
        parts = ref[2:].split("/")
        current = self.spec
        
        for part in parts:
            current = current.get(part, {})
            if not current:
                return None
        
        return current
    
    def get_request_schema(self, request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract schema from request body."""
        if not request_body:
            return None
        
        content = request_body.get("content", {})
        
        # Try JSON first, then form data
        for content_type in ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]:
            if content_type in content:
                media_type = content[content_type]
                schema = media_type.get("schema")
                
                if schema and "$ref" in schema:
                    return self.get_schema_by_ref(schema["$ref"])
                return schema
        
        return None
    
    def get_response_schema(self, responses: Dict[str, Any], status_code: str = "200") -> Optional[Dict[str, Any]]:
        """Extract schema from response."""
        response = responses.get(status_code) or responses.get("default")
        if not response:
            return None
        
        content = response.get("content", {})
        if "application/json" in content:
            media_type = content["application/json"]
            schema = media_type.get("schema")
            
            if schema and "$ref" in schema:
                return self.get_schema_by_ref(schema["$ref"])
            return schema
        
        return None
    
    def get_security_requirements(self) -> List[Dict[str, Any]]:
        """Get security requirements for the API."""
        security = self.spec.get("security", [])
        return security