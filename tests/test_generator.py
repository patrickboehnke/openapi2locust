"""Tests for the Locust generator module."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

from openapi2locust.generator import (
    LocustGenerator, 
    LocustGeneratorError, 
    InvalidFilenameError,
    TemplateRenderError
)


class TestLocustGenerator:
    """Test cases for LocustGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create a simple valid OpenAPI spec
        self.valid_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "summary": "Get all users",
                        "responses": {"200": {"description": "Success"}}
                    },
                    "post": {
                        "summary": "Create user",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }
        
        # Create temporary spec file
        self.spec_file = self.temp_path / "test_spec.yaml"
        with open(self.spec_file, 'w') as f:
            yaml.dump(self.valid_spec, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        assert generator.spec_path == str(self.spec_file)
        assert generator.output_dir == self.temp_path.resolve()
        assert generator.parser is not None
        assert generator.data_faker is not None
    
    def test_generator_initialization_creates_output_dir(self):
        """Test generator creates output directory if it doesn't exist."""
        new_dir = self.temp_path / "new_output"
        generator = LocustGenerator(str(self.spec_file), str(new_dir))
        assert new_dir.exists()
        assert generator.output_dir == new_dir.resolve()
    
    def test_generator_initialization_invalid_output_dir(self):
        """Test generator handles invalid output directory."""
        # Create a file where we want a directory
        invalid_path = self.temp_path / "invalid_dir"
        invalid_path.write_text("file content")
        
        with pytest.raises(LocustGeneratorError, match="Cannot create output directory"):
            LocustGenerator(str(self.spec_file), str(invalid_path))
    
    def test_generate_basic(self):
        """Test basic generation without custom filename."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        output_file = generator.generate()
        
        assert output_file is not None
        output_path = Path(output_file)
        assert output_path.exists()
        assert output_path.name == "locustfile_test_spec.py"
        
        # Check file content
        content = output_path.read_text()
        assert "class TestAPIUser(HttpUser):" in content
        assert "def getUsers(self):" in content
        assert "def post_users(self):" in content
    
    def test_generate_with_custom_filename(self):
        """Test generation with custom filename."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        output_file = generator.generate("custom_test.py")
        
        assert output_file is not None
        output_path = Path(output_file)
        assert output_path.exists()
        assert output_path.name == "custom_test.py"
    
    def test_validate_filename_valid(self):
        """Test filename validation with valid filenames."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        valid_names = [
            "test.py",
            "my_test_file.py",
            "test-file.py",
            "test123.py"
        ]
        
        for name in valid_names:
            result = generator._validate_filename(name)
            assert result == name
    
    def test_validate_filename_invalid(self):
        """Test filename validation with invalid filenames."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        invalid_names = [
            "",
            "../test.py",
            "test/../file.py",
            "test/file.py",
            ".hidden.py",
            "test<file>.py",
            "test|file.py"
        ]
        
        for name in invalid_names:
            with pytest.raises(InvalidFilenameError):
                generator._validate_filename(name)
    
    def test_validate_filename_adds_py_extension(self):
        """Test filename validation adds .py extension if missing."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        result = generator._validate_filename("test")
        assert result == "test.py"
    
    def test_is_safe_path_valid(self):
        """Test path safety validation with valid paths."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        safe_path = self.temp_path / "test.py"
        assert generator._is_safe_path(safe_path)
    
    def test_is_safe_path_invalid(self):
        """Test path safety validation with invalid paths."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # Path outside output directory
        unsafe_path = self.temp_path.parent / "test.py"
        assert not generator._is_safe_path(unsafe_path)
    
    def test_sanitize_string(self):
        """Test string sanitization."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # Normal string
        result = generator._sanitize_string("hello world")
        assert result == "hello world"
        
        # String with control characters
        result = generator._sanitize_string("hello\x00\x1f world")
        assert result == "hello world"
        
        # Long string (should be truncated)
        long_string = "a" * 300
        result = generator._sanitize_string(long_string)
        assert len(result) == 200
        
        # Non-string input
        result = generator._sanitize_string(123)
        assert result == "123"
    
    def test_sanitize_url(self):
        """Test URL sanitization."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # Valid HTTP URL
        result = generator._sanitize_url("http://example.com")
        assert result == "http://example.com"
        
        # Valid HTTPS URL
        result = generator._sanitize_url("https://api.example.com")
        assert result == "https://api.example.com"
        
        # Invalid protocol
        result = generator._sanitize_url("ftp://example.com")
        assert result == ""
        
        # Non-string input
        result = generator._sanitize_url(123)
        assert result == ""
        
        # URL with HTML entities
        result = generator._sanitize_url("https://example.com?q=<script>")
        assert "&lt;script&gt;" in result
    
    def test_generate_class_name(self):
        """Test class name generation."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # Normal title
        result = generator._generate_class_name("My API")
        assert result == "MyAPIUser"
        
        # Title with special characters
        result = generator._generate_class_name("My-API v2.0!")
        assert result == "MyAPIV20User"
        
        # Empty title
        result = generator._generate_class_name("")
        assert result == "APIUser"
        
        # Title starting with number
        result = generator._generate_class_name("2.0 API")
        assert result == "API20APIUser"
        
        # Title already ending with User
        result = generator._generate_class_name("API User")
        assert result == "APIUser"
    
    def test_generate_task_name(self):
        """Test task name generation."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # With operation ID
        endpoint = {
            "operation_id": "getUserById",
            "method": "GET",
            "path": "/users/{id}"
        }
        result = generator._generate_task_name(endpoint)
        assert result == "getUserById"
        
        # Without operation ID
        endpoint = {
            "method": "POST",
            "path": "/users/profile"
        }
        result = generator._generate_task_name(endpoint)
        assert result == "post_users_profile"
        
        # Path with parameters
        endpoint = {
            "method": "GET",
            "path": "/users/{id}/posts/{postId}"
        }
        result = generator._generate_task_name(endpoint)
        assert result == "get_users_posts"
        
        # Root path
        endpoint = {
            "method": "GET",
            "path": "/"
        }
        result = generator._generate_task_name(endpoint)
        assert result == "get_endpoint"
    
    def test_calculate_task_weight(self):
        """Test task weight calculation."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        assert generator._calculate_task_weight("GET") == 10
        assert generator._calculate_task_weight("POST") == 3
        assert generator._calculate_task_weight("PUT") == 2
        assert generator._calculate_task_weight("PATCH") == 2
        assert generator._calculate_task_weight("DELETE") == 1
        assert generator._calculate_task_weight("HEAD") == 1
        assert generator._calculate_task_weight("OPTIONS") == 1
        assert generator._calculate_task_weight("UNKNOWN") == 5
    
    def test_get_expected_status_codes(self):
        """Test expected status codes extraction."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # With success codes
        responses = {
            "200": {"description": "OK"},
            "201": {"description": "Created"},
            "400": {"description": "Bad Request"},
            "500": {"description": "Server Error"}
        }
        result = generator._get_expected_status_codes(responses)
        assert 200 in result
        assert 201 in result
        assert 400 not in result
        assert 500 not in result
        
        # No success codes
        responses = {
            "400": {"description": "Bad Request"},
            "500": {"description": "Server Error"}
        }
        result = generator._get_expected_status_codes(responses)
        assert result == [200]  # Default fallback
        
        # With string status codes
        responses = {
            "200": {"description": "OK"},
            "default": {"description": "Error"}
        }
        result = generator._get_expected_status_codes(responses)
        assert 200 in result
    
    @patch('openapi2locust.generator.LocustGenerator._build_template_context')
    def test_generate_template_render_error(self, mock_context):
        """Test generation handles template rendering errors."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # Mock parser methods directly on the instance
        generator.parser.parse = Mock(return_value=self.valid_spec)
        generator.parser.security_schemes = {}
        generator.parser.get_endpoints = Mock(return_value=[])
        
        # Mock context to cause template error
        mock_context.return_value = {"invalid": object()}  # Non-serializable object
        
        with pytest.raises(LocustGeneratorError, match="Generation failed"):
            generator.generate()
    
    def test_process_endpoint_error_handling(self):
        """Test endpoint processing error handling."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        
        # Valid endpoint
        endpoint = {
            "method": "GET",
            "path": "/users",
            "responses": {"200": {"description": "OK"}}
        }
        result = generator._process_endpoint(endpoint)
        assert result is not None
        assert result["method"] == "GET"
        
        # Invalid endpoint (missing required fields)
        invalid_endpoint = {}
        result = generator._process_endpoint(invalid_endpoint)
        assert result is None
    
    def test_generate_test_data_vars(self):
        """Test test data variables generation."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        result = generator._generate_test_data_vars()
        
        assert "data_faker" in result
        assert "random_ids" in result
        assert "test_strings" in result
        assert result["data_faker"] == "DataFaker()"
    
    def test_build_template_context_sanitization(self):
        """Test template context building with data sanitization."""
        generator = LocustGenerator(str(self.spec_file), str(self.temp_path))
        generator.parser.parse()
        generator.auth_handler = Mock()
        generator.auth_handler.get_auth_setup_code.return_value = ("", [])
        generator.auth_handler.get_auth_comments.return_value = []
        
        spec = {
            "info": {
                "title": "Test<script>alert('xss')</script>API",
                "description": "Test API with <malicious> content"
            }
        }
        endpoints = []
        
        context = generator._build_template_context(spec, endpoints)
        
        # Check that HTML is escaped
        assert "&lt;script&gt;" in context["class_name"] or "script" not in context["class_name"]
        assert "&lt;malicious&gt;" in context["class_description"]