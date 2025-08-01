"""Tests for the authentication handler module."""

import pytest
from unittest.mock import patch

from openapi2locust.auth_handler import (
    AuthHandler, 
    AuthHandlerError, 
    InvalidSecuritySchemeError,
    AuthType
)


class TestAuthHandler:
    """Test cases for AuthHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.basic_schemes = {
            "api_key": {
                "type": "apiKey",
                "name": "X-API-Key",
                "in": "header"
            },
            "basic_auth": {
                "type": "http",
                "scheme": "basic"
            },
            "bearer_auth": {
                "type": "http",
                "scheme": "bearer"
            },
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "implicit": {
                        "authorizationUrl": "https://example.com/oauth/authorize",
                        "scopes": {"read": "Read access"}
                    }
                }
            }
        }
    
    def test_auth_handler_initialization(self):
        """Test auth handler initialization."""
        handler = AuthHandler(self.basic_schemes)
        assert handler.security_schemes == self.basic_schemes
    
    def test_auth_handler_initialization_none(self):
        """Test auth handler initialization with None schemes."""
        handler = AuthHandler(None)
        assert handler.security_schemes == {}
    
    def test_auth_handler_initialization_empty(self):
        """Test auth handler initialization with empty schemes."""
        handler = AuthHandler({})
        assert handler.security_schemes == {}
    
    def test_validate_security_schemes_valid(self):
        """Test validation of valid security schemes."""
        handler = AuthHandler()
        result = handler._validate_security_schemes(self.basic_schemes)
        assert len(result) == len(self.basic_schemes)
        assert "api_key" in result
        assert "basic_auth" in result
    
    def test_validate_security_schemes_invalid_type(self):
        """Test validation rejects non-dict security schemes."""
        handler = AuthHandler()
        with pytest.raises(InvalidSecuritySchemeError, match="must be a dictionary"):
            handler._validate_security_schemes("invalid")
    
    def test_validate_security_schemes_invalid_scheme_name(self):
        """Test validation handles invalid scheme names."""
        handler = AuthHandler()
        invalid_schemes = {
            "": {"type": "apiKey"},  # Empty name
            123: {"type": "apiKey"},  # Non-string name  
            "valid_scheme": {"type": "apiKey"}
        }
        result = handler._validate_security_schemes(invalid_schemes)
        assert len(result) == 1  # Only valid_scheme should remain
        assert "valid_scheme" in result
    
    def test_validate_security_schemes_missing_type(self):
        """Test validation handles schemes without type."""
        handler = AuthHandler()
        invalid_schemes = {
            "no_type": {"name": "X-API-Key"},  # Missing type
            "valid_scheme": {"type": "apiKey", "name": "X-API-Key"}
        }
        result = handler._validate_security_schemes(invalid_schemes)
        assert len(result) == 1  # Only valid_scheme should remain
        assert "valid_scheme" in result
    
    def test_is_valid_scheme_name(self):
        """Test scheme name validation."""
        handler = AuthHandler()
        
        # Valid names
        assert handler._is_valid_scheme_name("api_key")
        assert handler._is_valid_scheme_name("basicAuth")
        assert handler._is_valid_scheme_name("oauth2_bearer")
        assert handler._is_valid_scheme_name("a" * 50)  # At max length
        
        # Invalid names
        assert not handler._is_valid_scheme_name("")
        assert not handler._is_valid_scheme_name("123invalid")  # Starts with number
        assert not handler._is_valid_scheme_name("api-key")  # Hyphen not allowed
        assert not handler._is_valid_scheme_name("api key")  # Space not allowed
        assert not handler._is_valid_scheme_name("a" * 51)  # Too long
        assert not handler._is_valid_scheme_name(123)  # Not string
    
    def test_sanitize_parameter_name(self):
        """Test parameter name sanitization."""
        handler = AuthHandler()
        
        # Valid name
        assert handler._sanitize_parameter_name("X-API-Key") == "X-API-Key"
        assert handler._sanitize_parameter_name("Authorization") == "Authorization"
        
        # Name with control characters
        assert handler._sanitize_parameter_name("API\x00Key") == "APIKey"
        
        # Empty or invalid input
        assert handler._sanitize_parameter_name("") == ""
        assert handler._sanitize_parameter_name("   ") == ""
        assert handler._sanitize_parameter_name(None) == ""
        
        # Long name (should be truncated)
        long_name = "X-" + "A" * 200
        result = handler._sanitize_parameter_name(long_name)
        assert len(result) == 100
    
    def test_sanitize_variable_name(self):
        """Test variable name sanitization."""
        handler = AuthHandler()
        
        # Valid name
        assert handler._sanitize_variable_name("api_key") == "api_key"
        assert handler._sanitize_variable_name("basicAuth") == "basicAuth"
        
        # Name with invalid characters
        assert handler._sanitize_variable_name("api-key") == "api_key"
        assert handler._sanitize_variable_name("api key") == "api_key"
        
        # Name starting with number
        assert handler._sanitize_variable_name("123key").startswith("auth_")
        
        # Empty or invalid input
        assert handler._sanitize_variable_name("") == "auth"
        assert handler._sanitize_variable_name("   ") == "auth"
        assert handler._sanitize_variable_name(None) == "auth"
    
    def test_get_auth_setup_code_api_key_header(self):
        """Test auth setup code generation for API key in header."""
        schemes = {
            "api_key": {
                "type": "apiKey",
                "name": "X-API-Key",
                "in": "header"
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"api_key": []}]
        code, imports = handler.get_auth_setup_code(security_requirements)
        
        assert 'self.client.headers["X-API-Key"]' in code
        assert 'API_KEY_API_KEY' in code
        assert len(imports) == 0
    
    def test_get_auth_setup_code_api_key_query(self):
        """Test auth setup code generation for API key in query."""
        schemes = {
            "api_key": {
                "type": "apiKey",
                "name": "api_key",
                "in": "query"
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"api_key": []}]
        code, imports = handler.get_auth_setup_code(security_requirements)
        
        assert 'self.api_key_api_key' in code
        assert 'API_KEY_API_KEY' in code
        assert len(imports) == 0
    
    def test_get_auth_setup_code_api_key_cookie(self):
        """Test auth setup code generation for API key in cookie."""
        schemes = {
            "api_key": {
                "type": "apiKey",
                "name": "session",
                "in": "cookie"
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"api_key": []}]
        code, imports = handler.get_auth_setup_code(security_requirements)
        
        assert 'self.client.cookies["session"]' in code
        assert 'API_KEY_API_KEY' in code
        assert len(imports) == 0
    
    def test_get_auth_setup_code_basic_auth(self):
        """Test auth setup code generation for basic auth."""
        schemes = {
            "basic": {
                "type": "http",
                "scheme": "basic"
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"basic": []}]
        code, imports = handler.get_auth_setup_code(security_requirements)
        
        assert 'import base64' in code
        assert 'BASIC_USERNAME' in code
        assert 'BASIC_PASSWORD' in code
        assert 'Authorization' in code
        assert 'Basic' in code
        assert 'base64' in imports
    
    def test_get_auth_setup_code_bearer_auth(self):
        """Test auth setup code generation for bearer auth."""
        schemes = {
            "bearer": {
                "type": "http",
                "scheme": "bearer"
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"bearer": []}]
        code, imports = handler.get_auth_setup_code(security_requirements)
        
        assert 'Bearer' in code
        assert 'BEARER_TOKEN' in code
        assert 'Authorization' in code
        assert len(imports) == 0
    
    def test_get_auth_setup_code_oauth2(self):
        """Test auth setup code generation for OAuth2."""
        schemes = {
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "implicit": {
                        "authorizationUrl": "https://example.com/oauth",
                        "scopes": {"read": "Read access"}
                    }
                }
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"oauth2": ["read"]}]
        code, imports = handler.get_auth_setup_code(security_requirements)
        
        assert 'OAuth2 authentication' in code
        assert 'Bearer' in code
        assert 'OAUTH2_ACCESS_TOKEN' in code
        assert len(imports) == 0
    
    def test_get_auth_setup_code_openid_connect(self):
        """Test auth setup code generation for OpenID Connect."""
        schemes = {
            "openid": {
                "type": "openIdConnect",
                "openIdConnectUrl": "https://example.com/.well-known/openid"
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"openid": []}]
        code, imports = handler.get_auth_setup_code(security_requirements)
        
        assert 'OpenID Connect authentication' in code
        assert 'Bearer' in code
        assert 'OPENID_ID_TOKEN' in code
        assert len(imports) == 0
    
    def test_get_auth_setup_code_empty_requirements(self):
        """Test auth setup code generation with empty requirements."""
        handler = AuthHandler(self.basic_schemes)
        
        code, imports = handler.get_auth_setup_code([])
        
        assert code == ""
        assert imports == []
    
    def test_get_auth_setup_code_invalid_requirements_type(self):
        """Test auth setup code generation with invalid requirements type."""
        handler = AuthHandler(self.basic_schemes)
        
        with pytest.raises(ValueError, match="must be a list"):
            handler.get_auth_setup_code("invalid")
    
    def test_get_auth_setup_code_invalid_scheme_name(self):
        """Test auth setup code handles invalid scheme names."""
        handler = AuthHandler(self.basic_schemes)
        
        # Security requirement with invalid scheme name
        security_requirements = [{"invalid-scheme": [], "api_key": []}]
        
        with patch.object(handler, 'logger') as mock_logger:
            code, imports = handler.get_auth_setup_code(security_requirements)
            mock_logger.warning.assert_called()
            
        # Should still process valid scheme
        assert 'X-API-Key' in code
    
    def test_get_auth_comments(self):
        """Test auth comments generation."""
        handler = AuthHandler(self.basic_schemes)
        
        security_requirements = [{"api_key": [], "basic_auth": []}]
        comments = handler.get_auth_comments(security_requirements)
        
        assert "Authentication setup:" in comments
        assert "Set the following environment variables:" in comments
        assert "API_KEY_API_KEY" in " ".join(comments)
        assert "BASIC_AUTH_USERNAME" in " ".join(comments)
        assert "BASIC_AUTH_PASSWORD" in " ".join(comments)
    
    def test_get_auth_comments_empty_requirements(self):
        """Test auth comments generation with empty requirements."""
        handler = AuthHandler(self.basic_schemes)
        
        comments = handler.get_auth_comments([])
        
        assert comments == ["# No authentication required"]
    
    def test_get_request_auth_params(self):
        """Test request auth parameters generation."""
        schemes = {
            "api_key": {
                "type": "apiKey",
                "name": "api_key",
                "in": "query"
            },
            "header_key": {
                "type": "apiKey",
                "name": "X-API-Key",
                "in": "header"
            }
        }
        handler = AuthHandler(schemes)
        
        security_requirements = [{"api_key": [], "header_key": []}]
        params = handler.get_request_auth_params(security_requirements)
        
        # Only query parameters should be included
        assert "api_key" in params
        assert "X-API-Key" not in params
        assert params["api_key"] == "self.api_key_api_key"
    
    def test_get_request_auth_params_invalid_type(self):
        """Test request auth params with invalid requirements type."""
        handler = AuthHandler(self.basic_schemes)
        
        with pytest.raises(ValueError, match="must be a list"):
            handler.get_request_auth_params("invalid")
    
    def test_get_request_auth_params_error_handling(self):
        """Test request auth params error handling."""
        handler = AuthHandler(self.basic_schemes)
        
        # Invalid requirement structure
        invalid_requirements = [123]  # Not a dict
        
        with patch.object(handler, 'logger') as mock_logger:
            params = handler.get_request_auth_params(invalid_requirements)
            assert params == {}  # Should return empty dict on error
    
    def test_auth_setup_code_error_handling(self):
        """Test auth setup code generation error handling."""
        handler = AuthHandler(self.basic_schemes)
        
        # Create a scenario that would cause an exception
        with patch.object(handler, '_generate_auth_code', side_effect=Exception("Test error")):
            with pytest.raises(AuthHandlerError, match="Auth setup generation failed"):
                handler.get_auth_setup_code([{"api_key": []}])
    
    def test_generate_auth_code_unknown_type(self):
        """Test auth code generation for unknown auth type."""
        schemes = {
            "unknown": {
                "type": "unknown_type"
            }
        }
        handler = AuthHandler(schemes)
        
        code, imports = handler._generate_auth_code("unknown", schemes["unknown"], [])
        
        assert code == ""
        assert imports == []
    
    def test_get_scheme_comments_comprehensive(self):
        """Test scheme comments for all auth types."""
        handler = AuthHandler()
        
        # API Key
        api_key_scheme = {"type": "apiKey"}
        comments = handler._get_scheme_comments("api_key", api_key_scheme)
        assert any("API_KEY_API_KEY" in comment for comment in comments)
        
        # Basic HTTP
        basic_scheme = {"type": "http", "scheme": "basic"}
        comments = handler._get_scheme_comments("basic", basic_scheme)
        assert any("BASIC_USERNAME" in comment for comment in comments)
        assert any("BASIC_PASSWORD" in comment for comment in comments)
        
        # Bearer HTTP
        bearer_scheme = {"type": "http", "scheme": "bearer"}
        comments = handler._get_scheme_comments("bearer", bearer_scheme)
        assert any("BEARER_TOKEN" in comment for comment in comments)
        
        # OAuth2
        oauth2_scheme = {"type": "oauth2"}
        comments = handler._get_scheme_comments("oauth2", oauth2_scheme)
        assert any("OAUTH2_ACCESS_TOKEN" in comment for comment in comments)
        
        # OpenID Connect
        openid_scheme = {"type": "openIdConnect"}
        comments = handler._get_scheme_comments("openid", openid_scheme)
        assert any("OPENID_ID_TOKEN" in comment for comment in comments)