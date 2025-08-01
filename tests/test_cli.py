"""Tests for the CLI module."""

import pytest
import tempfile
import yaml
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import Mock, patch

from openapi2locust.cli import main, cli, info, endpoints, _is_valid_filename


class TestCLI:
    """Test cases for CLI functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create a simple valid OpenAPI spec
        self.valid_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API", 
                "version": "1.0.0",
                "description": "A test API for CLI testing"
            },
            "servers": [
                {"url": "https://api.example.com", "description": "Production server"}
            ],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "summary": "Get all users",
                        "tags": ["users"],
                        "responses": {"200": {"description": "Success"}}
                    },
                    "post": {
                        "summary": "Create user",
                        "tags": ["users"],
                        "responses": {"201": {"description": "Created"}}
                    }
                },
                "/users/{id}": {
                    "get": {
                        "summary": "Get user by ID",
                        "tags": ["users"],
                        "parameters": [{
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "apiKey": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
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
    
    def test_main_basic_generation(self):
        """Test basic generation via main command."""
        result = self.runner.invoke(main, [str(self.spec_file)])
        
        assert result.exit_code == 0
        assert "Generating Locust script from:" in result.output
        assert "Locust script generated:" in result.output
        assert "Next steps:" in result.output
        
        # Check output file was created
        expected_file = Path("locustfile_test_spec.py")
        assert expected_file.exists()
        expected_file.unlink()  # Clean up
    
    def test_main_with_output_directory(self):
        """Test generation with custom output directory."""
        output_dir = self.temp_path / "output"
        
        result = self.runner.invoke(main, [
            str(self.spec_file),
            '-o', str(output_dir)
        ])
        
        assert result.exit_code == 0
        assert output_dir.exists()
        
        # Check output file was created in the specified directory
        expected_file = output_dir / "locustfile_test_spec.py"
        assert expected_file.exists()
    
    def test_main_with_custom_filename(self):
        """Test generation with custom filename."""
        result = self.runner.invoke(main, [
            str(self.spec_file),
            '-f', 'my_test.py'
        ])
        
        assert result.exit_code == 0
        
        # Check output file was created with custom name
        expected_file = Path("my_test.py")
        assert expected_file.exists()
        expected_file.unlink()  # Clean up
    
    def test_main_with_output_and_filename(self):
        """Test generation with both output directory and filename."""
        output_dir = self.temp_path / "output"
        
        result = self.runner.invoke(main, [
            str(self.spec_file),
            '-o', str(output_dir),
            '-f', 'custom_test.py'
        ])
        
        assert result.exit_code == 0
        
        # Check output file was created with custom name in custom directory
        expected_file = output_dir / "custom_test.py"
        assert expected_file.exists()
    
    def test_main_validate_only(self):
        """Test validation-only mode."""
        result = self.runner.invoke(main, [
            str(self.spec_file),
            '--validate-only'
        ])
        
        assert result.exit_code == 0
        assert "Validating OpenAPI specification:" in result.output
        assert "OpenAPI specification is valid!" in result.output
        
        # No output file should be created
        expected_file = Path("locustfile_test_spec.py")
        assert not expected_file.exists()
    
    def test_main_verbose(self):
        """Test verbose mode."""
        with patch('openapi2locust.cli.logging.basicConfig') as mock_logging:
            result = self.runner.invoke(main, [
                str(self.spec_file),
                '--verbose'
            ])
            
            # Should configure logging with DEBUG level
            mock_logging.assert_called_once()
            call_args = mock_logging.call_args
            assert call_args[1]['level'] == 20  # INFO level in verbose mode
    
    def test_main_nonexistent_file(self):
        """Test with non-existent spec file."""
        result = self.runner.invoke(main, ['nonexistent.yaml'])
        
        assert result.exit_code != 0
        assert "does not exist" in result.output
    
    def test_main_invalid_filename(self):
        """Test with invalid filename."""
        result = self.runner.invoke(main, [
            str(self.spec_file),
            '-f', '../invalid.py'
        ])
        
        assert result.exit_code == 1
        assert "Invalid filename" in result.output
    
    def test_main_invalid_spec(self):
        """Test with invalid OpenAPI spec."""
        # Create invalid spec
        invalid_spec = {"invalid": "spec"}
        invalid_file = self.temp_path / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            yaml.dump(invalid_spec, f)
        
        result = self.runner.invoke(main, [str(invalid_file)])
        
        assert result.exit_code == 1
        assert "Generation error:" in result.output or "Error:" in result.output
    
    def test_main_permission_error(self):
        """Test with permission error during file creation."""
        with patch('openapi2locust.generator.LocustGenerator.generate', 
                  side_effect=PermissionError("Permission denied")):
            result = self.runner.invoke(main, [str(self.spec_file)])
            
            assert result.exit_code == 1
            assert "Permission denied" in result.output
    
    def test_main_file_not_found_error(self):
        """Test with file not found error."""
        with patch('openapi2locust.generator.LocustGenerator.generate', 
                  side_effect=FileNotFoundError("File not found")):
            result = self.runner.invoke(main, [str(self.spec_file)])
            
            assert result.exit_code == 1
            assert "File not found" in result.output
    
    def test_info_command(self):
        """Test info command."""
        result = self.runner.invoke(cli, ['info', str(self.spec_file)])
        
        assert result.exit_code == 0
        assert "OpenAPI Specification Info:" in result.output
        assert "Title: Test API" in result.output
        assert "Version: 1.0.0" in result.output
        assert "Description: A test API for CLI testing" in result.output
        assert "Servers:" in result.output
        assert "https://api.example.com" in result.output
        assert "Production server" in result.output
        assert "Endpoints: 3" in result.output
        assert "GET: 2" in result.output
        assert "POST: 1" in result.output
        assert "Security Schemes:" in result.output
        assert "apiKey: apiKey" in result.output
    
    def test_info_command_minimal_spec(self):
        """Test info command with minimal spec."""
        minimal_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Minimal API", "version": "1.0.0"},
            "paths": {}
        }
        
        minimal_file = self.temp_path / "minimal.yaml"
        with open(minimal_file, 'w') as f:
            yaml.dump(minimal_spec, f)
        
        result = self.runner.invoke(cli, ['info', str(minimal_file)])
        
        assert result.exit_code == 0
        assert "Title: Minimal API" in result.output
        assert "Description: N/A" in result.output
        assert "Endpoints: 0" in result.output
    
    def test_info_command_invalid_spec(self):
        """Test info command with invalid spec."""
        invalid_file = self.temp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content")
        
        result = self.runner.invoke(cli, ['info', str(invalid_file)])
        
        assert result.exit_code == 1
        assert "Error:" in result.output
    
    def test_endpoints_command(self):
        """Test endpoints command."""
        result = self.runner.invoke(cli, ['endpoints', str(self.spec_file)])
        
        assert result.exit_code == 0
        assert "Endpoints (3):" in result.output
        assert "GET      /users" in result.output
        assert "Get all users" in result.output
        assert "POST     /users" in result.output
        assert "Create user" in result.output
        assert "GET      /users/{id}" in result.output
        assert "Get user by ID" in result.output
    
    def test_endpoints_command_empty_spec(self):
        """Test endpoints command with spec having no endpoints."""
        empty_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Empty API", "version": "1.0.0"},
            "paths": {}
        }
        
        empty_file = self.temp_path / "empty.yaml"
        with open(empty_file, 'w') as f:
            yaml.dump(empty_spec, f)
        
        result = self.runner.invoke(cli, ['endpoints', str(empty_file)])
        
        assert result.exit_code == 0
        assert "Endpoints (0):" in result.output
    
    def test_endpoints_command_invalid_spec(self):
        """Test endpoints command with invalid spec."""
        invalid_file = self.temp_path / "invalid.yaml"
        invalid_file.write_text("invalid yaml content")
        
        result = self.runner.invoke(cli, ['endpoints', str(invalid_file)])
        
        assert result.exit_code == 1
        assert "Error:" in result.output
    
    def test_is_valid_filename_valid(self):
        """Test filename validation with valid filenames."""
        valid_names = [
            "test.py",
            "my_test_file.py",
            "test-file.py",
            "test123.py",
            "test.txt",
            "a" * 100  # Reasonable length
        ]
        
        for name in valid_names:
            assert _is_valid_filename(name), f"Should be valid: {name}"
    
    def test_is_valid_filename_invalid(self):
        """Test filename validation with invalid filenames."""
        invalid_names = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "../test.py",  # Path traversal
            "test/file.py",  # Contains slash
            "test\\file.py",  # Contains backslash
            "a" * 300,  # Too long
            "test..py",  # Contains ..
        ]
        
        for name in invalid_names:
            assert not _is_valid_filename(name), f"Should be invalid: {name}"
    
    def test_main_create_output_directory_error(self):
        """Test main command handles output directory creation errors."""
        # Try to create directory where a file exists
        existing_file = self.temp_path / "existing_file"
        existing_file.write_text("content")
        
        result = self.runner.invoke(main, [
            str(self.spec_file),
            '-o', str(existing_file)
        ])
        
        assert result.exit_code == 1
        assert "Cannot create output directory" in result.output
    
    def test_main_unexpected_error(self):
        """Test main command handles unexpected errors."""
        with patch('openapi2locust.generator.LocustGenerator', 
                  side_effect=RuntimeError("Unexpected error")):
            result = self.runner.invoke(main, [str(self.spec_file)])
            
            assert result.exit_code == 1
            assert "Unexpected error" in result.output
    
    def test_main_generator_error(self):
        """Test main command handles generator-specific errors."""
        from openapi2locust.generator import LocustGeneratorError
        
        with patch('openapi2locust.generator.LocustGenerator.generate', 
                  side_effect=LocustGeneratorError("Generator error")):
            result = self.runner.invoke(main, [str(self.spec_file)])
            
            assert result.exit_code == 1
            assert "Generation error:" in result.output
    
    def test_main_invalid_filename_error(self):
        """Test main command handles invalid filename errors."""
        from openapi2locust.generator import InvalidFilenameError
        
        with patch('openapi2locust.generator.LocustGenerator.generate', 
                  side_effect=InvalidFilenameError("Invalid filename")):
            result = self.runner.invoke(main, [str(self.spec_file)])
            
            assert result.exit_code == 1
            assert "Invalid filename:" in result.output
    
    def test_cli_group(self):
        """Test CLI group command."""
        result = self.runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "OpenAPI to Locust converter tools" in result.output
        assert "info" in result.output
        assert "endpoints" in result.output
    
    def test_main_help(self):
        """Test main command help."""
        result = self.runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "Generate Locust test scripts from OpenAPI specifications" in result.output
        assert "SPEC_FILE" in result.output
        assert "--output" in result.output
        assert "--filename" in result.output
        assert "--validate-only" in result.output
        assert "--verbose" in result.output
    
    def test_main_version(self):
        """Test main command version."""
        result = self.runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        # Should show version number
        assert len(result.output.strip()) > 0