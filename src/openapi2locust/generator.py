"""Locust script generator from OpenAPI specifications."""

import os
import re
import html
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union
from jinja2 import Environment, FileSystemLoader, Template

from .parser import OpenAPIParser
from .data_faker import DataFaker
from .auth_handler import AuthHandler
from .config import ConfigurationManager


class LocustGeneratorError(Exception):
    """Base exception for LocustGenerator."""
    pass


class InvalidFilenameError(LocustGeneratorError):
    """Raised when an invalid filename is provided."""
    pass


class TemplateRenderError(LocustGeneratorError):
    """Raised when template rendering fails."""
    pass


class LocustGenerator:
    """Generate Locust test scripts from OpenAPI specifications."""
    
    # Compiled regex patterns for better performance
    _FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+\.py$')
    _CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1f\x7f-\x9f]')
    _SPECIAL_CHARS_PATTERN = re.compile(r'[^a-zA-Z0-9\s]')
    _MULTIPLE_UNDERSCORES_PATTERN = re.compile(r'_+')
    _HTTP_URL_PATTERN = re.compile(r'^https?://')
    
    def __init__(self, spec_path: str, output_dir: str = ".", config: Optional[ConfigurationManager] = None) -> None:
        self.spec_path = spec_path
        self.config = config or ConfigurationManager()
        
        # Use config for output directory if not explicitly provided
        if output_dir == ".":
            output_dir = self.config.get_output_dir()
        
        self.output_dir = Path(output_dir).resolve()  # Resolve to absolute path
        self.parser = OpenAPIParser(spec_path)
        
        # Use config for data faker locale
        faker_locale = self.config.get_data_faker_locale()
        self.data_faker = DataFaker(faker_locale)
        
        self.auth_handler: Optional[AuthHandler] = None
        self.logger = logging.getLogger(__name__)
        
        # Validate output directory
        if not self.output_dir.exists():
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise LocustGeneratorError(f"Cannot create output directory: {e}")
        elif self.output_dir.is_file():
            raise LocustGeneratorError(f"Cannot create output directory: {self.output_dir} is a file")
        
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        
    def generate(self, output_filename: Optional[str] = None) -> str:
        """Generate Locust script from OpenAPI spec."""
        try:
            # Parse the OpenAPI specification
            spec = self.parser.parse()
            
            # Setup authentication handler
            self.auth_handler = AuthHandler(self.parser.security_schemes)
            
            # Get endpoints
            endpoints = self.parser.get_endpoints()
            
            # Generate template context
            context = self._build_template_context(spec, endpoints)
            
            # Render template
            template = self.env.get_template("locustfile.py.j2")
            generated_code = template.render(**context)
            
            # Write to file
            if not output_filename:
                spec_name = Path(self.spec_path).stem
                output_filename = f"locustfile_{spec_name}.py"
            
            # Validate and sanitize output filename
            validated_filename = self._validate_filename(output_filename)
            output_path = self.output_dir / validated_filename
            
            # Ensure output path is within output directory (prevent path traversal)
            if not self._is_safe_path(output_path):
                raise InvalidFilenameError(f"Invalid output path: {output_path}")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(generated_code)
            
            self.logger.info(f"Generated Locust script: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to generate Locust script: {e}")
            if isinstance(e, (LocustGeneratorError, OSError, IOError)):
                raise
            raise LocustGeneratorError(f"Generation failed: {e}") from e
    
    def _build_template_context(self, spec: Dict[str, Any], endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build the template context with all necessary data."""
        spec_info = spec.get("info", {})
        
        # Generate class name from spec title
        class_name = self._generate_class_name(spec_info.get("title", "API"))
        
        # Process endpoints
        processed_endpoints = []
        for endpoint in endpoints:
            processed_endpoint = self._process_endpoint(endpoint)
            if processed_endpoint:
                processed_endpoints.append(processed_endpoint)
        
        # Get authentication setup
        security_requirements = self.parser.get_security_requirements()
        auth_setup_code, additional_imports = self.auth_handler.get_auth_setup_code(security_requirements)
        auth_comments = self.auth_handler.get_auth_comments(security_requirements)
        
        # Get wait times from config
        min_wait, max_wait = self.config.get_wait_time()
        
        # Build context with sanitized data
        context = {
            "class_name": self._sanitize_string(class_name),
            "class_description": html.escape(spec_info.get("description", f"Load test for {spec_info.get('title', 'API')}")),
            "base_url": self._sanitize_url(self.parser.get_base_url()),
            "min_wait": min_wait,
            "max_wait": max_wait,
            "endpoints": processed_endpoints,
            "auth_setup_code": auth_setup_code,
            "auth_comments": auth_comments,
            "additional_imports": additional_imports,
            "test_data_vars": self._generate_test_data_vars(),
            "filename": f"locustfile_{Path(self.spec_path).stem}.py",
            "include_security_headers": self.config.should_include_security_headers(),
            "security_headers": self.config.get_security_headers(),
            "include_test_data_helpers": self.config.should_include_test_data_helpers()
        }
        
        return context
    
    def _process_endpoint(self, endpoint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single endpoint into template format."""
        try:
            # Generate task name
            task_name = self._generate_task_name(endpoint)
            
            # Process parameters
            path_params = self._process_path_parameters(endpoint)
            query_params = self._process_query_parameters(endpoint)
            headers = self._process_headers(endpoint)
            
            # Process request body
            request_body = self._process_request_body(endpoint)
            
            # Process authentication
            auth_params = self.auth_handler.get_request_auth_params(endpoint.get("security", [])) if self.auth_handler else {}
            
            # Generate response validation
            response_validation = self._generate_response_validation(endpoint)
            
            # Determine expected status codes
            expected_status_codes = self._get_expected_status_codes(endpoint.get("responses", {}))
            
            # Calculate task weight based on method
            weight = self._calculate_task_weight(endpoint["method"])
            
            return {
                "task_name": task_name,
                "name": f"{endpoint['method']} {endpoint['path']}",
                "description": html.escape(endpoint.get("summary", f"{endpoint['method']} {endpoint['path']}")),
                "method": endpoint["method"],
                "path": endpoint["path"],
                "path_params": path_params,
                "query_params": query_params,
                "headers": headers,
                "auth_params": auth_params,
                "request_body": request_body,
                "response_validation": response_validation,
                "expected_status_codes": expected_status_codes,
                "weight": weight
            }
        except (KeyError, ValueError, TypeError) as e:
            self.logger.warning(f"Failed to process endpoint {endpoint.get('path', 'unknown')}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error processing endpoint {endpoint.get('path', 'unknown')}: {e}")
            raise LocustGeneratorError(f"Endpoint processing failed: {e}") from e
    
    def _generate_class_name(self, title: str) -> str:
        """Generate a valid Python class name from API title."""
        # HTML escape the input first to handle malicious content
        safe_title = html.escape(title)
        
        # Check if HTML escaping occurred (indicates malicious input)
        if '&lt;' in safe_title or '&gt;' in safe_title or '&amp;' in safe_title:
            # Remove HTML entirely for malicious input to prevent script injection
            clean_title = re.sub(r'&[a-zA-Z0-9#]+;', '', safe_title)
        else:
            clean_title = safe_title
            
        # Remove special characters and convert to PascalCase
        clean_title = self._SPECIAL_CHARS_PATTERN.sub('', clean_title)
        words = clean_title.split()
        
        # Special handling for "API" to keep it uppercase
        pascal_words = []
        for word in words:
            if word.lower() == 'api':
                pascal_words.append('API')
            else:
                pascal_words.append(word.capitalize())
        
        class_name = ''.join(pascal_words)
        
        if not class_name:
            class_name = "APIUser"
        elif not class_name[0].isalpha():
            class_name = "API" + class_name
        
        return class_name + "User" if not class_name.endswith("User") else class_name
    
    def _generate_task_name(self, endpoint: Dict[str, Any]) -> str:
        """Generate a valid Python method name from endpoint."""
        operation_id = endpoint.get("operation_id", "")
        if operation_id and operation_id.replace("_", "").isalnum():
            return operation_id
        
        # Generate from method and path
        method = endpoint["method"].lower()
        path = endpoint["path"]
        
        # Extract meaningful parts from path
        path_parts = [part for part in path.split("/") if part and not part.startswith("{")]
        if not path_parts:
            path_parts = ["endpoint"]
        
        # Create method name
        task_name = method + "_" + "_".join(path_parts)
        
        # Clean up the name
        task_name = re.sub(r'[^a-zA-Z0-9_]', '_', task_name)
        task_name = self._MULTIPLE_UNDERSCORES_PATTERN.sub('_', task_name).strip('_')
        
        # Ensure it starts with a letter
        if not task_name[0].isalpha():
            task_name = "task_" + task_name
        
        return task_name
    
    def _process_path_parameters(self, endpoint: Dict[str, Any]) -> Dict[str, str]:
        """Process path parameters for an endpoint."""
        path_params = {}
        path = endpoint["path"]
        parameters = endpoint.get("parameters", [])
        
        # Find path parameters from the path string
        param_names = self.parser.get_path_parameters(path)
        
        for param_name in param_names:
            # Find parameter schema
            param_schema = None
            for param in parameters:
                if param.get("name") == param_name and param.get("in") == "path":
                    param_schema = param.get("schema")
                    break
            
            # Generate parameter value
            path_params[param_name] = f'self.data_faker.generate_path_param("{param_name}", {param_schema})'
        
        return path_params
    
    def _process_query_parameters(self, endpoint: Dict[str, Any]) -> Dict[str, str]:
        """Process query parameters for an endpoint."""
        query_params = {}
        parameters = endpoint.get("parameters", [])
        
        for param in parameters:
            if param.get("in") == "query":
                param_name = param.get("name")
                param_schema = param.get("schema")
                required = param.get("required", False)
                
                # Only include required parameters or randomly include optional ones
                if required:
                    query_params[param_name] = f'self.data_faker.generate_query_param("{param_name}", {param_schema})'
        
        return query_params
    
    def _process_headers(self, endpoint: Dict[str, Any]) -> Dict[str, str]:
        """Process header parameters for an endpoint."""
        headers = {"Content-Type": '"application/json"'}
        parameters = endpoint.get("parameters", [])
        
        for param in parameters:
            if param.get("in") == "header":
                header_name = param.get("name")
                param_schema = param.get("schema")
                required = param.get("required", False)
                
                if required and header_name.lower() not in ["authorization", "content-type"]:
                    headers[header_name] = f'self.data_faker.generate_header_value("{header_name}", {param_schema})'
        
        return headers
    
    def _process_request_body(self, endpoint: Dict[str, Any]) -> Optional[Any]:
        """Process request body for an endpoint."""
        request_body = endpoint.get("request_body")
        if not request_body:
            return None
        
        schema = self.parser.get_request_schema(request_body)
        if schema:
            return self.data_faker.generate_from_schema(schema)
        
        return None
    
    def _generate_response_validation(self, endpoint: Dict[str, Any]) -> str:
        """Generate response validation code."""
        responses = endpoint.get("responses", {})
        validation_code = []
        
        # Get schema for successful response (200, 201, etc.)
        for status_code in ["200", "201", "202"]:
            schema = self.parser.get_response_schema(responses, status_code)
            if schema:
                validation_code.append(f"# Validate response structure")
                validation_code.append(f"# Expected schema: {schema}")
                break
        
        return "\n".join(validation_code) if validation_code else ""
    
    def _get_expected_status_codes(self, responses: Dict[str, Any]) -> List[int]:
        """Get list of expected status codes from responses."""
        status_codes = []
        for status_code in responses.keys():
            if status_code.isdigit():
                code = int(status_code)
                if 200 <= code < 400:  # Success and redirect codes
                    status_codes.append(code)
        
        return status_codes if status_codes else [200]
    
    def _calculate_task_weight(self, method: str) -> int:
        """Calculate task weight based on HTTP method."""
        return self.config.get_task_weight(method)
    
    def _generate_test_data_vars(self) -> Dict[str, Any]:
        """Generate common test data variables."""
        return {
            "data_faker": "DataFaker()",
            "random_ids": "[random.randint(1, 1000) for _ in range(10)]",
            "test_strings": '["test", "sample", "demo", "example"]'
        }
    
    def _validate_filename(self, filename: str) -> str:
        """Validate and sanitize filename to prevent path traversal."""
        if not filename:
            raise InvalidFilenameError("Filename cannot be empty")
        
        # Check for dangerous patterns before cleaning
        if '..' in filename or '/' in filename or '\\' in filename:
            raise InvalidFilenameError(f"Invalid filename pattern: {filename}")
        
        # Remove any path separators and parent directory references
        clean_filename = Path(filename).name
        
        # Check for dangerous patterns after cleaning
        if clean_filename.startswith('.'):
            raise InvalidFilenameError(f"Invalid filename pattern: {filename}")
        
        # Check for invalid characters that could cause issues
        invalid_chars = '<>"|?*'
        if any(char in clean_filename for char in invalid_chars):
            raise InvalidFilenameError(f"Invalid filename characters: {clean_filename}")
        
        # Ensure it's a Python file
        if not clean_filename.endswith('.py'):
            clean_filename += '.py'
        
        # Validate filename characters (allow alphanumeric, underscore, hyphen, dot)
        if not self._FILENAME_PATTERN.match(clean_filename):
            raise InvalidFilenameError(f"Invalid filename characters: {clean_filename}")
        
        return clean_filename
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is within the output directory (prevent path traversal)."""
        try:
            path_resolved = path.resolve()
            output_resolved = self.output_dir.resolve()
            return path_resolved.parent == output_resolved
        except (OSError, RuntimeError):
            return False
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string input for template rendering."""
        if not isinstance(value, str):
            return str(value)
        # Remove control characters and limit length
        sanitized = self._CONTROL_CHARS_PATTERN.sub('', value)
        return sanitized[:200]  # Limit length
    
    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL input."""
        if not isinstance(url, str):
            return ""
        # Basic URL validation - allow only http/https
        if not self._HTTP_URL_PATTERN.match(url):
            return ""
        return html.escape(url)[:500]  # Limit length